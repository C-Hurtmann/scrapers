import os
import re

from dataclasses import dataclass
from typing import Self

from lxml import etree
from sqlalchemy import Integer, Column, String
from sqlalchemy.orm import declarative_base

from .element import ElementNotFoundError
from .page import Page
from .selector import By

Base = declarative_base()


@dataclass
class ProductDTO:
    category: str
    subcategory: str
    title: str | None = None
    description: str | None = None
    low_price: int | None = None
    medium_price: int | None = None
    high_price: int | None = None

    @staticmethod
    def __to_int(price: str | None) -> int | None:
        if not price:
            return None
        return int(re.sub(r'\D', '', price))

    def collect_from_page(self, page: Page) -> Self:
        try:
            self.title = page.find(By().class_name('rt-Text rt-r-size-5 rt-r-weight-bold')).first().text
            self.description = page.find(
                By().class_name('rt-Flex rt-r-display-none xs:rt-r-display-flex rt-r-fd-row rt-r-gap-1').tag('p'),
                raise_exception=False
            ).first().text
            self.low_price = self.__to_int(
                page.find(By().class_name('v-fw-600 v-fs-12'), raise_exception=False).first().text
            )
            self.high_price = self.__to_int(
                page.find(By().class_name('_rangeSliderLastNumber'), raise_exception=False).first().text
            )
            self.medium_price = self.__to_int(
                page.find(By().class_name('v-fw-700 v-fs-24'), raise_exception=False).first().text
            )
        except ElementNotFoundError as e:
            logs_dir = 'logs'
            os.makedirs(logs_dir, exist_ok=True)
            with open(f'{logs_dir}/debug.html', 'w', encoding='utf-8') as f:
                f.write(etree.tostring(page.source, pretty_print=True, encoding='unicode'))
            raise e
        return self


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    low_price = Column(Integer, nullable=True)
    medium_price = Column(Integer, nullable=True)
    high_price = Column(Integer, nullable=True)

    def to_dict(self):
        model_dict = self.__dict__
        model_dict.pop('_sa_instance_state', None)
        return model_dict
