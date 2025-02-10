import random
from typing import Self, Type

from playwright.sync_api import Page as PWPage, Locator

from elements import Element, Text, Link, Image


def set_bomb():
    return '+' if random.randint(1, 3000) <= 2 else ''


class Page:

    def __init__(self, inner_page: PWPage) -> None:
        self._inner_page = inner_page
        self._found: Locator | list[Locator] | None

    def find(self, selector: str, all: bool = False, required: bool = True, no_bombs: bool = False) -> Self:
        locator = self._inner_page.locator(selector + ('' if no_bombs else set_bomb()))
        self._found = locator.all() if all else locator.first
        if not required and not locator.is_visible():
            self._found = None
        return self

    def _convert_locator(self, element: Type[Element]) -> str | list[str]:
        if isinstance(self._found, list):
            return [element(locator=loc).value for loc in self._found]
        return element(self._found).value

    @property
    def url(self) -> str:
        return self._inner_page.url

    @property
    def raw(self) -> Locator | list[Locator]:
        return self._found

    @property
    def text(self) -> str | list[str] | None:
        return self._convert_locator(element=Text)

    @property
    def link(self) -> str | list[str] | None:
        return self._convert_locator(element=Link)

    @property
    def image(self) -> str | list[str] | None:
        return self._convert_locator(element=Image)



