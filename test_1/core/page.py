from typing import Self

import requests
from lxml import html
from yarl import URL

from .element import ElementNotFoundError, Element
from .selector import By


BASE_URL = 'https://www.vendr.com'


class InvalidServerResponse(Exception):
    pass


class Page:

    def __init__(self, source: requests.Response) -> None:
        self.source: html.HtmlElement = html.fromstring(source.content)
        self.found_elements: list[html.HtmlElement] = []
        self.raise_exception = None

    @staticmethod
    def get(root: str | URL) -> 'Page':
        url = BASE_URL + str(root)
        print('Perform request on', url)
        res = requests.get(url=url)
        if res.ok:
            return Page(source=res)
        raise InvalidServerResponse(f'Invalid server response - {res.status_code} {url}')

    def find(self, by: By, raise_exception: bool = True) -> Self:
        self.raise_exception = raise_exception
        elements = self.source.xpath(str(by))
        if not elements and raise_exception:
            raise ElementNotFoundError
        self.found_elements = elements
        return self

    def all(self) -> list[Element]:
        return [Element(html_element=el) for el in self.found_elements]

    def first(self) -> Element:
        if not self.found_elements:
            return Element(html_element=None, is_empty=True)
        return Element(html_element=self.found_elements[0])
