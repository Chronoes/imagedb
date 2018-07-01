"""
"""
from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin

__author__ = 'Chronoes'


class Parser:
    hostname = None

    def __init__(self, url=None):
        self.session = Session()
        self.url = url.strip() if url else None

    @staticmethod
    def determine_parser(url):
        if url.find(gelbooru.hostname) != -1:
            gelbooru.set_url(url)
            return gelbooru
        elif url.find(konachan.hostname) != -1:
            konachan.set_url(url)
            return konachan
        elif url.find(yandere.hostname) != -1:
            yandere.set_url(url)
            return yandere
        else:
            raise NotImplementedError('Parser for (' + url + ') does not exist yet')

    def set_url(self, url):
        self.url = url.strip()

    def get_image_info(self):
        resp = self.session.get(self.url)
        self._set_html_parser(resp.text)
        image_parent = self._get_image_parent()
        link_parent = self._get_link_parent()
        if image_parent and link_parent:
            return {
                'tags': image_parent['alt'].split(),
                'link': urljoin(self.url, link_parent['href']) if link_parent['href'].startswith('//') else link_parent['href']
            }
        return

    def get_image(self, link):
        resp = self.session.get(
            link,
            headers={'Referer': self.url})
        return resp.content

    def _set_html_parser(self, content):
        self.soup = BeautifulSoup(content, 'html.parser')

    def _get_image_parent(self):
        raise NotImplementedError('Gets location of image and tags in HTML')

    def _get_link_parent(self):
        raise NotImplementedError('Gets link to original (unsampled) image')


class GelbooruParser(Parser):
    hostname = 'gelbooru.com'

    def _get_image_parent(self):
        return self.soup.find(id='image')

    def _get_link_parent(self):
        a_tags = self.soup.find_all('a')
        for element in a_tags:
            if element.string == 'Original image':
                return element
        return ''


class KonachanParser(Parser):
    hostname = 'konachan.com'

    def _get_image_parent(self):
        return self.soup.find(id='image')

    def _get_link_parent(self):
        return self.soup.find(id='highres')


class YandereParser(KonachanParser):
    hostname = 'yande.re'


gelbooru = GelbooruParser()
konachan = KonachanParser()
yandere = YandereParser()
