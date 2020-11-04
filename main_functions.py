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


def get_image(downloader: ImageDownloader, redownload=False, custom_name=None, skip_data=False):
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
    return img_info


def get_image_queue(queue: queue.Queue, *args, **kwargs):
    queue.put(get_image(*args, **kwargs))


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
    url_count = len(urls)

    url_queue = queue.Queue(3)
    consumer = threading.Thread(target=queue_consumer, args=(url_queue, url_count, results_callback))
    consumer.start()

    threads = []
    manager = DownloaderManager()
    for url in set(urls):
        downloader = manager.determine_downloader(url)
        t = threading.Thread(target=get_image_queue, args=(url_queue, downloader), kwargs=kwargs)
        t.start()
        threads.append(t)
        if len(threads) >= 10:
            for t in threads:
                t.join()
            threads.clear()

    for t in threads:
        t.join()

    url_queue.join()
    url_queue.put(None)
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
        img = db.Image.create(
            group=group,
            filename=img_info['filename'],
            original_link=img_info['original_link'])
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
