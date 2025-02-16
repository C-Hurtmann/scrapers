from dataclasses import dataclass
from typing import Self


@dataclass
class Selector:
    tag: str | None = None
    class_name: str | None = None

    def __str__(self):
        selector_string = f'//{self.tag or '*'}'
        if self.class_name:
            selector_string += f'[contains(@class, "{self.class_name}")]'
        return selector_string


class By:

    def __init__(self) -> None:
        self.selector_chain: list[Selector] = []

    def __str__(self) -> str:
        return ''.join(map(str, self.selector_chain))

    def class_name(self, name: str, contains: bool = False) -> Self:
        self.selector_chain.append(Selector(class_name=name))
        return self

    def tag(self, name: str) -> Self:
        self.selector_chain.append(Selector(tag=name))
        return self
