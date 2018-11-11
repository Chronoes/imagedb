"""
"""
from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin

__author__ = 'Chronoes'


class Parser:
    hostname = None

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

    def get_image(self,link):
        resp = self.session.get(
            link,
            headers={'Referer': self.url})
        return resp.content

    def _get_image_parent(self, soup):
        raise NotImplementedError('Gets location of image and tags in HTML')

    def _get_link_parent(self, soup):
        raise NotImplementedError('Gets link to original (unsampled) image')


class GelbooruParser(Parser):
    hostname = 'gelbooru.com'

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        a_tags = soup.find_all('a')
        for element in a_tags:
            if element.string == 'Original image':
                return element
        return ''


class KonachanParser(Parser):
    hostname = 'konachan.com'

    def _get_image_parent(self, soup):
        return soup.find(id='image')

    def _get_link_parent(self, soup):
        return soup.find(id='highres')


class YandereParser(KonachanParser):
    hostname = 'yande.re'


class ParserManager:
    def __init__(self):
        self.session = Session()

    def determine_parser(self, url):
        if url.find(GelbooruParser.hostname) != -1:
            return GelbooruParser(self.session, url)
        elif url.find(KonachanParser.hostname) != -1:
            return KonachanParser(self.session, url)
        elif url.find(YandereParser.hostname) != -1:
            return YandereParser(self.session, url)
        else:
            raise NotImplementedError('Parser for (' + url + ') does not exist yet')
