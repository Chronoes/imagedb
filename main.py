"""
"""
import pathlib
import sys
import argparse

from pathlib import Path
from main_functions import *

__author__ = 'Chronoes'


# TODO: GUI for querying tags and inserting new images
# TODO: Integrate with widescreenimages.py and imagesaver (Go)


def init_parser():
    parser = argparse.ArgumentParser(
        description='''
        Retrieve image from URL and save tags to local DB.
        Currently supported Gelbooru, Konachan and Yande.re.''')
    parser.add_argument('-o', '--out',
        help='Custom filename for destination. Only works for single URL source')
    parser.add_argument('-s', '--series',
        action='store_true',
        help='Read source file of URLs as an image series. Multiple series must be separated by newline.')
    parser.add_argument('--redownload',
        action='store_true',
        help='Redownload images that do not exist in filesystem. Use --force to download all.')
    parser.add_argument('-f', '--force',
        action='store_true',
        help='Apply some force.')
    parser.add_argument('source', nargs='?', default='-',
        help='Source must be a valid URL or file of URLs')
    parser.add_argument('group',
        help='Group to be used for image')
    return parser


def main():
    parser = init_parser()
    args = parser.parse_args()
    # TODO: Fix this shit
    args.series = False

    img_group = find_group(args.group)

    if args.redownload:
        urls = fetch_image_urls(img_group, args.force)
        results = get_image_bulk(urls, redownload=True)
        for img_info in results:
            save_file(img_info, img_group)
            print('Image {} redownloaded.'.format(img_info['original_link']))
    elif args.source.startswith('http'):
        if 'out' in args:
            img_info = get_image(
                args.source,
                custom_name=args.out)
        else:
            img_info = get_image(args.source)
        if type(img_info) == str:
            print(img_info)
        else:
            save(img_info, img_group)
    else:
        file = sys.stdin if args.source == '-' else open(args.source, 'r')
        with file as f:
            urls = f.readlines()
        # if args.series:
        #     results = get_image_series(urls)
        # else:
        results = get_image_bulk(urls, redownload=args.redownload)
        for img_info in results:
            save(img_info, img_group)


if __name__ == '__main__':
    main()
