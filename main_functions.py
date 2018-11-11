import threading
import queue
import peewee

from pathlib import Path

import database.database as db
import utilities as util
from html_parsers import Parser
from database.db_queries import *


def get_image(url: str, redownload=False, custom_name=None):
    if not url:
        return
    url = url.strip()
    try:
        parser = Parser.determine_parser(url)
    except NotImplementedError as e:
        return str(e)
    img_info = parser.get_image_info()
    if not img_info:
        return 'Could not parse {}'.format(url)
    if custom_name:
        filename = custom_name + util.parse_extension(img_info['link'])
    else:
        filename = util.parse_filename(img_info['link'])
    if not redownload and db.Image.select().where(db.Image.filename == filename).exists():
        return 'Image ({}) already exists'.format(url)
    img_info['data'] = parser.get_image(img_info['link'])
    img_info['original_link'] = url
    img_info['filename'] = filename
    return img_info


def get_image_queue(queue: queue.Queue, *args, **kwargs):
    queue.put(get_image(*args, **kwargs))


def queue_consumer(queue: queue.Queue, url_count: int, results, failed):
    util.progress_bar(0, url_count, suffix='-- 0/{} images downloaded.'.format(url_count))
    i = 1
    result_count = 0

    while True:
        finished = queue.get()
        if type(finished) == dict:
            results.append(finished)
            result_count += 1
        elif type(finished) == str:
            failed.append(finished)
        else:
            queue.task_done()
            break

        util.progress_bar(i, url_count, suffix='-- {}/{} images downloaded.'.format(result_count, url_count))
        queue.task_done()
        i += 1


def get_image_bulk(urls: list, **kwargs):
    results = []
    failed = []
    url_count = len(urls)

    url_queue = queue.Queue()
    consumer = threading.Thread(target=queue_consumer, args=(url_queue, url_count, results, failed))
    consumer.start()

    threads = []
    for url in set(urls):
        t = threading.Thread(target=get_image_queue, args=(url_queue, url), kwargs=kwargs)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    url_queue.join()
    url_queue.put(None)
    consumer.join()

    print()
    if len(failed) > 0:
        print('Failed:\n' + '\n'.join(failed))
        print('------')
    return results


def save_file(img_info: dict, group: db.ImageGroup):
    filename = img_info['filename']
    dest_path = Path(group.path) / filename
    with dest_path.open('wb') as f:
        f.write(img_info['data'])


def save(img_info: dict, group: db.ImageGroup, retries=3):
    if not img_info:
        return
    elif retries <= 0:
        print('No more retries for {}.'.format(img_info['original_link']))
        return

    try:
        img = db.Image.create(
            group=group,
            filename=img_info['filename'],
            original_link=img_info['original_link'])
    except (peewee.IntegrityError, peewee.sqlite3.IntegrityError):
        print('This {} is duplicated'.format(img_info['filename']))
        return
    except peewee.OperationalError:
        print('Disk error, retrying...')
        return save(img_info, group, retries - 1)

    tags_query = db.Tag.select().where(db.Tag.tag << img_info['tags'])
    old_tags = set(tag.tag for tag in tags_query)
    new_tags = set(img_info['tags']) - old_tags

    if len(new_tags) > 0:
        db.Tag.insert_many({'tag': tag} for tag in new_tags).execute()

    def insert_tags(retries=5):
        if retries <= 0:
            return
        try:
            db.ImageTag.insert_many(
                {'image': img, 'tag': tag} for tag in tags_query) \
                .execute()
        except peewee.OperationalError:
            return insert_tags(retries - 1)
    insert_tags()

    save_file(img_info, group)

    print('Image {} saved.'.format(img_info['original_link']))


def fetch_image_urls(group: db.ImageGroup, all_images: bool):
    query = db.Image.select(db.Image.original_link, db.Image.filename).where(db.Image.group == group).join(db.ImageGroup)
    if all_images:
        return [img.original_link for img in query]
    files = set(file.name for file in Path(group.path).iterdir())
    return [img.original_link for img in query if img.filename not in files]
