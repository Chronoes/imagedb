"""
"""
import re

from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

from config import load_config

__author__ = 'Chronoes'

class ImageDownloaderException(Exception): pass

class ImageDownloader:
    def __init__(self, session, url):
        self.session = session
        self.url = url.strip()

    @staticmethod
    def supports(url):
        return False

    def canonical_url(self):
        """
        Returns canonical URL for the downloader
        """
        raise NotImplementedError('Returns canonical URL')

    def get_image_info(self):
        """
        Must return dictionary containing 'tags' and 'link' keys
        """
        raise NotImplementedError('Gets image metadata')

    def get_image(self, link):
        resp = self.session.get(
            link,
            headers={'Referer': self.url})
        return resp.content

    def __str__(self):
        return self.__class__.__name__


def parse_gelbooru_id(url):
    parsed_url = urlparse(url)
    qry = parse_qs(parsed_url.query)
    return qry['id'].pop()


def gelbooru_canonical_url(url):
    img_id = parse_gelbooru_id(url)
    return 'https://gelbooru.com/index.php?page=post&s=view&id=' + img_id


class GelbooruAPIParser(ImageDownloader):
    base_url = 'https://gelbooru.com/index.php'
    def __init__(self, session, url, api_key, user_id):
        super().__init__(session, url)
        self.api_key = api_key
        self.user_id = user_id

    @staticmethod
    def supports(url):
        return 'gelbooru.com' in url

    def canonical_url(self):
        return gelbooru_canonical_url(self.url)

    def upvote_image(self, img_id):
        params={'page': 'post', 's': 'vote', 'id': img_id, 'type': 'up'}
        self.session.get(self.base_url, params=params)

    def get_image_info(self):
        params = {'page': 'dapi', 's': 'post', 'q': 'index', 'json': 1, 'api_key': self.api_key, 'user_id': self.user_id}
        img_id = parse_gelbooru_id(self.url)
        params['id'] = img_id
        resp = self.session.get(self.base_url, params=params)
        if len(resp.content) == 0:
            raise ImageDownloaderException('{}: Could not parse {}'.format(str(self), self.url))
        resp_json = resp.json()
        if not resp_json or 'post' not in resp_json:
            raise ImageDownloaderException('{}: Could not parse {}'.format(str(self), self.url))
        item = resp_json['post'].pop()

        self.upvote_image(img_id)

        return {
            'tags': item['tags'].split(),
            'link': item['file_url']
        }


class HTMLParser(ImageDownloader):
    def get_image_info(self):
        resp = self.session.get(self.url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        image_parent = self._get_image_parent(soup)
        link_parent = self._get_link_parent(soup)
        if image_parent and link_parent:
            return {
                'tags': image_parent['alt'].split(),
                'link': urljoin(self.url, link_parent['href']) if link_parent['href'].startswith('//') else link_parent['href']
            }
        raise ImageDownloaderException('{}: Could not parse {}'.format(str(self), self.url))

    def _get_image_parent(self, soup):
        raise NotImplementedError('Gets location of image and tags in HTML')

    def _get_link_parent(self, soup):
        raise NotImplementedError('Gets link to original (unsampled) image')


class GelbooruParser(HTMLParser):
    @staticmethod
    def supports(url):
        return 'gelbooru.com' in url

    def canonical_url(self):
        return gelbooru_canonical_url(self.url)

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        a_tags = soup.find_all('a')
        for element in a_tags:
            if element.string == 'Original image':
                return element
        return ''

    def upvote_image(self, img_id):
        params={'page': 'post', 's': 'vote', 'id': img_id, 'type': 'up'}
        self.session.get('https://gelbooru.com/index.php', params=params)

    def get_image_info(self):
        result = super().get_image_info()
        if result:
            img_id = parse_gelbooru_id(self.url)
            self.upvote_image(img_id)
        return result

class KonachanParser(HTMLParser):
    host = 'konachan.com'

    @staticmethod
    def supports(url):
        return KonachanParser.host in url

    def canonical_url(self):
        match = re.search(r'post\/show\/([0-9]+)', self.url)
        if not match:
            raise ImageDownloaderException('Cannot parse ID from ' + self.url)
        return 'https://{}/post/show/{}'.format(self.host, match.group(1))

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        return soup.find(id='highres')


class YandereParser(KonachanParser):
    host = 'yande.re'

    @staticmethod
    def supports(url):
        return YandereParser.host in url

class ImageInfo:
    def __init__(self, link: str, original_link: str, tags: list[str], group=None, downloader: ImageDownloader=None, data=None, parent=None, filename=None) -> None:
        self.link = link
        self.original_link = original_link
        self.tags = tags
        self.group = group
        self.data = data
        self.downloader = downloader
        self.parent = parent
        self.filename = filename

    @classmethod
    def from_downloader(cls, downloader: ImageDownloader, group=None, skip_data=False, parent=None):
        img_info = downloader.get_image_info()
        return cls(img_info['link'], downloader.canonical_url(), img_info['tags'], group=group, downloader=downloader,
            data=None if skip_data else downloader.get_image(img_info['link']),
            parent=parent)

class DownloaderManager:
    def __init__(self):
        self.config = load_config()
        self.session = Session()
        self.config_verified = {'gelbooru': self._verify_gelbooru_api_config()}

    def _verify_gelbooru_api_config(self) -> bool:
        if 'credentials' not in self.config:
            return False
        cred = self.config['credentials']
        if 'gelbooru' not in cred:
            return False
        g = cred['gelbooru']
        if g.get('api_key', None) and g.get('user_id', None):
            return g
        return False

    def determine_downloader(self, url: str) -> ImageDownloader:
        if GelbooruAPIParser.supports(url) and self.config_verified['gelbooru']:
            credentials = self.config_verified['gelbooru']
            return GelbooruAPIParser(self.session, url, credentials['api_key'], credentials['user_id'])
        elif GelbooruParser.supports(url):
            return GelbooruParser(self.session, url)
        elif KonachanParser.supports(url):
            return KonachanParser(self.session, url)
        elif YandereParser.supports(url):
            return YandereParser(self.session, url)

        raise NotImplementedError('Parser for (' + url + ') does not exist yet')
