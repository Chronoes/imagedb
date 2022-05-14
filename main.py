"""
"""
import sys
import argparse
import peewee

import database.db_queries as queries

from main_functions import fetch_image_urls, get_image, get_image_bulk, process_tags, save, save_file
from database.database import connect_db
from downloaders import DownloaderManager

__author__ = 'Chronoes'



def init_parser():
    parser = argparse.ArgumentParser(
        description='''
        Retrieve image from URL and save tags to local DB.
        Currently supported Gelbooru, Konachan and Yande.re.''')
    parser.add_argument('-o', '--out',
        help='Custom filename for destination. Only works for single URL source')
    # parser.add_argument('-s', '--series',
    #     action='store_true',
    #     help='Read source file of URLs as an image series. Multiple series must be separated by newline.')
    parser.add_argument('--redownload',
        help='Redownload options: =images that do not exist in filesystem (--force for all). =metadata to redownload metadata.',
        choices=('images', 'metadata'))
    parser.add_argument('-f', '--force',
        action='store_true',
        help='Apply some force.')
    parser.add_argument('-g', '--group',
        help='Group to be used for image')
    parser.add_argument('source', nargs='?', default='-',
        help='Source must be a valid URL or file of URLs')
    return parser


def main():
    parser = init_parser()
    args = parser.parse_args()
    connect_db()

    try:
        img_group = queries.find_group(args.group) if args.group else None
    except peewee.DoesNotExist as e:
        raise Exception(f'No such image group {args.group}') from e

    if args.redownload == 'images':
        urls = fetch_image_urls(img_group, args.force)
        def redownload_images_cb(result, error=False):
            if error:
                print(result)
            else:
                save_file(result)
                print(f'Image {result["original_link"]} redownloaded.')

        get_image_bulk(urls, redownload_images_cb, redownload=True)
    elif args.redownload == 'metadata':
        urls = fetch_image_urls(img_group, True)
        def redownload_metadata_cb(result, error=False):
            if error:
                print(result)
            else:
                img = queries.find_by_filename(result['filename'])
                process_tags(img, result['tags'])
                print(f'Image {result["filename"]} ({result["original_link"]}) metadata redownloaded.')

        get_image_bulk(urls, redownload_metadata_cb, redownload=True, skip_data=True)
    elif args.source.startswith('http'):
        if img_group is None:
            raise Exception('--group option must be specified for HTTP link as source')
        manager = DownloaderManager()
        downloader = manager.determine_downloader(args.source)
        if 'out' in args:
            img_info = get_image(downloader, custom_name=args.out)
        else:
            img_info = get_image(downloader)
        if type(img_info) == str:
            print(img_info)
        else:
            img_info['group'] = img_group.name
            save(img_info)
    else:
        file = sys.stdin if args.source == '-' else open(args.source, 'r')
        with file as f:
            urls = []
            for line in f:
                line = line.strip()
                if line == 'series' or line == 'end series':
                    urls.append((None, line))
                else:
                    parts = line.split(' ', maxsplit=1)
                    if len(parts) == 1:
                        if img_group is None:
                            raise Exception('Lines in file must have format if --group is not set: <group> <url>')
                        else:
                            urls.append((img_group.name, parts[0]))
                    else:
                        urls.append(tuple(parts))


        def save_image_cb(result, error=False):
            if error:
                print(result)
            else:
                save(result)

        get_image_bulk(urls, save_image_cb, redownload=bool(args.redownload))


if __name__ == '__main__':
    main()
