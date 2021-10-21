import concurrent.futures as confut
import threading
import queue
import peewee
import time

from pathlib import Path

import database.database as db
import utilities as util
from downloaders import ImageDownloader, DownloaderManager

from config import load_config

config = load_config()


def get_image(downloader: ImageDownloader, redownload=False, custom_name=None, skip_data=False, parent=None):
    img_info = downloader.get_image_info()
    if not img_info:
        return '{}: Could not parse {}'.format(downloader, downloader.url)
    if custom_name:
        filename = custom_name + util.parse_extension(img_info['link'])
    else:
        filename = util.parse_filename(img_info['link'])
    if not redownload and db.Image.select().where(db.Image.filename == filename).exists():
        return '{}: Image ({}) already exists'.format(downloader, downloader.url)

    img_info['data'] = None if skip_data else downloader.get_image(img_info['link'])
    img_info['original_link'] = downloader.canonical_url()
    img_info['filename'] = filename
    img_info['_downloader'] = str(downloader)
    img_info['parent'] = parent
    return img_info


def queue_consumer(queue: queue.Queue, url_count: int, results_callback):
    i = 0
    result_count = 0

    while True:
        util.progress_bar(i, url_count, suffix=f'-- {result_count}/{url_count} images downloaded.')
        finished = queue.get()
        if type(finished) == dict:
            results_callback(finished)
            result_count += 1
        elif type(finished) == str:
            results_callback(finished, error=True)
        else:
            queue.task_done()
            break

        queue.task_done()
        i += 1
        time.sleep(0.3)


def get_image_bulk(urls: list, results_callback, **kwargs):
    url_count = sum(1 for url in urls if url.startswith('http'))

    image_queue = queue.Queue(0)
    consumer = threading.Thread(target=queue_consumer, args=(image_queue, url_count, results_callback))
    consumer.start()

    manager = DownloaderManager()

    def download_image(url, parent=None):
        downloader = manager.determine_downloader(url)
        return get_image(downloader, parent=parent, **kwargs)


    with confut.ThreadPoolExecutor(max_workers=4) as executor:
        # A lock to prevent multiple series downloaders running at once
        # without it there's a potential for deadlock if series downloader threads equal max_workers
        series_download_lock = threading.Lock()
        def download_image_series(series_urls):
            series_futures = []

            series_futures.append(executor.submit(download_image, series_urls[0]))
            for i in range(1, len(series_urls)):
                series_futures.append(executor.submit(download_image, series_urls[i], parent=series_urls[i - 1]))

            # Results have to be in the same order, so we have to process them sequentially
            results = [f.result() for f in series_futures]
            series_download_lock.release()
            return results

        downloaded_urls = set()
        futures = []
        series_of_urls = []
        add_to_series = False
        for url in urls:
            url = url.strip()
            if url in downloaded_urls:
                continue
            if url == 'series':
                # start of a series of URLs, process separately
                add_to_series = True
            elif url == 'end series':
                # ends the series of URLs and processes them
                if len(series_of_urls) >= 1:
                    series_download_lock.acquire()
                    # Submit a copy of the list
                    futures.append(executor.submit(download_image_series, series_of_urls[:]))
                    series_of_urls.clear()
                add_to_series = False
            elif add_to_series:
                series_of_urls.append(url)
                downloaded_urls.add(url)
            else:
                futures.append(executor.submit(download_image, url))
                downloaded_urls.add(url)

        for future in confut.as_completed(futures):
            image = future.result()
            if type(image) == list:
                for im in image:
                    image_queue.put(im)
            else:
                image_queue.put(image)

    image_queue.join()
    image_queue.put(None)
    consumer.join()


def save_file(img_info: dict, group: db.ImageGroup):
    filename = img_info['filename']
    dest_path = Path(config['groups'][group.name]) / filename
    with dest_path.open('wb') as f:
        f.write(img_info['data'])


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


def save(img_info: dict, group: db.ImageGroup, retries=3):
    if not img_info:
        return
    elif retries <= 0:
        print('{}: No more retries for {}.'.format(img_info['_downloader'], img_info['original_link']))
        return

    try:
        parent = None
        if img_info['parent']:
            parent = db.Image.get(db.Image.original_link == img_info['parent'])
        img = db.Image.create(
            group=group,
            filename=img_info['filename'],
            original_link=img_info['original_link'],
            parent=parent
        )
    except (peewee.IntegrityError, peewee.sqlite3.IntegrityError):
        print('{}: This {} is duplicated'.format(img_info['_downloader'], img_info['filename']))
        return
    except peewee.OperationalError:
        print('Disk error, retrying...')
        return save(img_info, group, retries - 1)

    process_tags(img, img_info['tags'])
    save_file(img_info, group)

    print('{}: Image {} saved.'.format(img_info['_downloader'], img_info['original_link']))


def fetch_image_urls(group: db.ImageGroup, all_images: bool):
    query = db.Image.select(db.Image.original_link, db.Image.filename).where(db.Image.group == group).join(db.ImageGroup)
    if all_images:
        return [img.original_link for img in query]
    files = set(file.name for file in Path(config['groups'][group.name]).iterdir())
    return [img.original_link for img in query if img.filename not in files]
