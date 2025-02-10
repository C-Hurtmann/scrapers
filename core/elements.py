from typing import Any
from abc import ABC, abstractmethod
from playwright.sync_api import Locator


class Element(ABC):
    def __init__(self, locator: Locator | None) -> None:
        self.locator = locator

    @property
    def value(self) -> Any:
        return None if self.locator is None else self.get()

    @abstractmethod
    def get(self) -> Any:
        pass


class Link(Element):

    def get(self) -> str:
        return self.locator.get_attribute('href')


class Text(Element):

    def get(self) -> str:
        return self.locator.text_content()


class Image(Element):

    def get(self) -> str:
        return self.locator.get_attribute('src')
