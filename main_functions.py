import concurrent.futures as confut
import threading
import queue
import peewee
import progressbar

from pathlib import Path

import database.database as db
import utilities as util
from database.db_queries import find_group, get_groups
from downloaders import ImageDownloader, DownloaderManager, ImageDownloaderException, ImageInfo

from config import load_config

config = load_config()


def get_image(downloader: ImageDownloader, group: str, redownload=False, custom_name=None, skip_data=False, parent=None):
    try:
        img_info = ImageInfo.from_downloader(downloader, group=group, skip_data=skip_data, parent=parent)
    except ImageDownloaderException as e:
        return (str(e), downloader.canonical_url())
    if custom_name:
        filename = custom_name + util.parse_extension(img_info.link)
    else:
        filename = util.parse_filename(img_info.link)
    if not redownload and db.Image.select().where(db.Image.filename == filename).exists():
        return ('{}: Image ({}) already exists'.format(downloader, downloader.url), downloader.canonical_url())

    img_info.filename = filename
    return img_info


def queue_consumer(queue: queue.Queue, url_count: int, results_callback):
    i = 0
    resolved_urls = set()

    with progressbar.ProgressBar(max_value=url_count, initial_value=0, redirect_stdout=True) as bar:
        bar.update(i)
        while True:
            finished = queue.get()
            if type(finished) == ImageInfo:
                # add back to queue if the image has a parent but it isn't processed yet
                if finished.parent and finished.parent[1] not in resolved_urls:
                    queue.task_done()
                    queue.put(finished)
                    continue
                results_callback(finished)
                resolved_urls.add(finished.original_link)
            elif type(finished) == tuple:
                results_callback(finished[0], error=True)
                resolved_urls.add(finished[1])
            else:
                queue.task_done()
                break

            queue.task_done()
            bar.update(i)
            i += 1


def get_image_bulk(urls: list, results_callback, **kwargs):
    url_count = sum(1 for _, url in urls if url.startswith('http'))

    image_queue = queue.Queue(0)
    consumer = threading.Thread(target=queue_consumer, args=(image_queue, url_count, results_callback))
    consumer.start()

    manager = DownloaderManager()

    def download_image(group, url, parent=None):
        downloader = manager.determine_downloader(url)
        return get_image(downloader, group, parent=parent, **kwargs)

    futures = []
    with confut.ThreadPoolExecutor(max_workers=3) as executor:
        def download_image_series(series_urls):
            # Results have to be in the same order, so we have to process them sequentially
            for i, (g, url) in enumerate(series_urls):
                parent = series_urls[i - 1] if i > 0 else None
                futures.append(executor.submit(download_image, g, url, parent=parent))

        downloaded_urls = set()
        series_of_urls = []
        add_to_series = False
        for group, url in urls:
            url = url.strip()
            if url in downloaded_urls:
                continue
            if url == 'series':
                # start of a series of URLs, process separately
                add_to_series = True
            elif url == 'end series':
                # ends the series of URLs and processes them
                if series_of_urls:
                    download_image_series(series_of_urls)
                    series_of_urls.clear()
                add_to_series = False
            elif add_to_series:
                series_of_urls.append((group, url))
                downloaded_urls.add(url)
            else:
                futures.append(executor.submit(download_image, group, url))
                downloaded_urls.add(url)

    for future in confut.as_completed(futures):
        image = future.result()
        image_queue.put(image)

    image_queue.join()
    image_queue.put(None)
    consumer.join()


def save_file(img_info: ImageInfo):
    dest_path = Path(config['groups'][img_info.group]) / img_info.filename
    with dest_path.open('wb') as f:
        f.write(img_info.data)


def process_tags(img: db.Image, tags: list):

    tags_query = db.Tag.select().where(db.Tag.tag << tags)
    old_tags = set(tag.tag for tag in tags_query)
    new_tags = set(tags) - old_tags

    if len(new_tags) > 0:
        db.Tag.insert_many({'tag': tag} for tag in new_tags).execute()

    def insert_tags(retries=5):
        if retries <= 0:
            return
        with db.db.atomic() as transaction:
            try:
                db.ImageTag.delete().where(db.ImageTag.image == img).execute()
                db.ImageTag.insert_many(
                    {'image': img, 'tag': tag} for tag in tags_query) \
                    .execute()
            except peewee.OperationalError:
                transaction.rollback()
                return insert_tags(retries - 1)
    insert_tags()


def save(img_info: ImageInfo, retries=3):
    if not img_info:
        return
    elif retries <= 0:
        print('{}: No more retries for {}.'.format(img_info.downloader, img_info.original_link))
        return

    try:
        group = find_group(img_info.group)
        parent = None
        if img_info.parent:
            parent = db.Image.get(db.Image.original_link == img_info.parent[1])
        img = db.Image.create(
            group=group,
            filename=img_info.filename,
            original_link=img_info.original_link,
            parent=parent
        )
    except (peewee.IntegrityError, peewee.sqlite3.IntegrityError):
        print('{}: This {} is duplicated'.format(img_info.downloader, img_info.filename))
        return
    except peewee.OperationalError:
        print('Disk error, retrying...')
        return save(img_info, retries - 1)

    process_tags(img, img_info.tags)
    save_file(img_info)

    print('{}: Image {} saved.'.format(img_info.downloader, img_info.original_link))


def fetch_image_urls(group: db.ImageGroup, all_images: bool):
    query = db.Image.select(db.Image.original_link, db.Image.filename).join(db.ImageGroup)
    if group:
        query = query.where(db.Image.group == group)
    if all_images:
        return [(img.group.name, img.original_link) for img in query]

    if group:
        files = set(file.name for file in Path(config['groups'][group.name]).iterdir())
    else:
        files = set()
        for g in get_groups():
            files = files.intersection(file.name for file in Path(config['groups'][g.name]).iterdir())
    return [(img.group.name, img.original_link) for img in query if img.filename not in files]
