from lxml import html
from yarl import URL


class ElementNotFoundError(Exception):
    pass


class Element:
    def __init__(self, html_element: html.HtmlElement | None = None, is_empty: bool = False) -> None:
        self.html_element = html_element
        self.is_empty = is_empty

    @property
    def text(self) -> str | None:
        return self.html_element.text if not self.is_empty else None

    @property
    def link(self) -> URL | None:
        return URL(self.html_element.get('href')) if not self.is_empty else None
