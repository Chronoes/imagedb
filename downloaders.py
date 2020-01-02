"""
"""
from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

from config import load_config

__author__ = 'Chronoes'

class ImageDownloader:
    def __init__(self, session, url):
        self.session = session
        self.url = url.strip()

    @staticmethod
    def supports(url):
        return False

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


class GelbooruAPIParser(ImageDownloader):
    def __init__(self, session, url, api_key, user_id):
        super().__init__(session, url)
        self.api_key = api_key
        self.user_id = user_id

    @staticmethod
    def supports(url):
        return url.find('gelbooru.com') != -1

    def parse_id(self):
        parsed_url = urlparse(self.url)
        qry = parse_qs(parsed_url.query)
        return qry['id']

    def get_image_info(self):
        params = {'page': 'dapi', 's': 'post', 'q': 'index', 'json': 1, 'api_key': self.api_key, 'user_id': self.user_id}
        img_id = self.parse_id()
        params['id'] = img_id
        resp = self.session.get('https://gelbooru.com/index.php', params=params)
        if len(resp.content) == 0:
            return

        resp_json = resp.json().pop()
        return {
            'tags': resp_json['tags'].split(),
            'link': resp_json['file_url']
        }


class HTMLParser(ImageDownloader):
    def __init__(self, session, url):
        self.session = session
        self.url = url.strip()

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
        return

    def _get_image_parent(self, soup):
        raise NotImplementedError('Gets location of image and tags in HTML')

    def _get_link_parent(self, soup):
        raise NotImplementedError('Gets link to original (unsampled) image')


class GelbooruParser(HTMLParser):
    @staticmethod
    def supports(url):
        return url.find('gelbooru.com') != -1

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        a_tags = soup.find_all('a')
        for element in a_tags:
            if element.string == 'Original image':
                return element
        return ''


class KonachanParser(HTMLParser):
    @staticmethod
    def supports(url):
        return url.find('konachan.com') != -1

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        return soup.find(id='highres')


class YandereParser(KonachanParser):
    @staticmethod
    def supports(url):
        return url.find('yande.re') != -1


class DownloaderManager:
    def __init__(self):
        self.config = load_config()
        self.session = Session()

    def determine_downloader(self, url):
        if GelbooruAPIParser.supports(url):
            credentials = self.config['credentials']['gelbooru']
            return GelbooruAPIParser(self.session, url, credentials['api_key'], credentials['user_id'])
        # elif GelbooruParser.supports(url):
        #     return GelbooruParser(self.session, url)
        elif KonachanParser.supports(url):
            return KonachanParser(self.session, url)
        elif YandereParser.supports(url):
            return YandereParser(self.session, url)
        else:
            raise NotImplementedError('Parser for (' + url + ') does not exist yet')
