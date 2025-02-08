import os
import re
from dataclasses import dataclass
from pprint import pprint
from typing import Any, Self

import requests
from yarl import URL
from lxml import html, etree

from element import ElementNotFoundError
from page import Page
from selector import By

categories = ['devops']


def write_content(file_name: str, content: Any):
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    with open(f'{logs_dir}/{file_name}.html', 'w', encoding='utf-8') as f:
        f.write(etree.tostring(content, pretty_print=True, encoding='unicode'))


def to_int(price: str | None) -> int | None:
    return int(re.sub(r'[^\d]', '', price)) if price else None


@dataclass
class Product:
    category: str
    subcategory: str
    title: str | None = None
    description: str | None = None
    low_price: int | None = None
    medium_price: int | None = None
    high_price: int | None = None

    def collect_from_page(self, page: Page) -> Self:
        try:
            self.title = page.find(By().class_name('rt-Text rt-r-size-5 rt-r-weight-bold')).first().text
            self.description = page.find(
                By().class_name('rt-Flex rt-r-display-none xs:rt-r-display-flex rt-r-fd-row rt-r-gap-1').tag('p'),
                raise_exception=False
            ).first().text
            self.low_price = to_int(page.find(By().class_name('v-fw-600 v-fs-12'), raise_exception=False).first().text)
            self.high_price = to_int(
                page.find(By().class_name('_rangeSliderLastNumber'), raise_exception=False).first().text
            )
            self.medium_price = to_int(
                page.find(By().class_name('v-fw-700 v-fs-24'), raise_exception=False).first().text
            )
        except ElementNotFoundError as e:
            write_content('debug', page.source)
            raise e
        return self


def fetch_product(from_: URL, category_name: str, subcategory_name: str) -> Product:
    product_page = Page.get(root=from_)
    product_dto = Product(category=category_name.capitalize(), subcategory=subcategory_name)
    return product_dto.collect_from_page(page=product_page)


def get_product_url_by_category(category_name: str):
    category_page = Page.get(root='/categories/' + category_name)
    subcategories = category_page.find(by=By().class_name('rt-Box rt-r-pb-1').tag('a')).all()
    for category_num, subcategory in enumerate(subcategories, start=1):
        subcategory_name = subcategory.text
        subcategory_link = subcategory.link
        write_content('debug', content=subcategory.html_element)
        page_number = int(subcategory_link.query['page'])
        print(f'{category_num=} | {subcategory_name}\n' + '=' * 100)
        while True:
            updated_link = subcategory_link.with_query(dict(subcategory_link.query) | {'page': page_number})
            page_number += 1

            product_list_page = Page.get(root=updated_link)
            if not (
                products := product_list_page.find(
                    By().class_name('rt-Grid rt-r-gtc-1 sm:rt-r-gtc-2 rt-r-ai-start rt-r-gap-5').tag('a'),
                    raise_exception=False
                ).all()
            ):
                break
            for product in products:
                product_dto = fetch_product(
                    from_=product.link, category_name=category_name, subcategory_name=subcategory_name
                )
                pprint(product_dto)
        break
    print(f'Finish with {category_name}')


if __name__ == '__main__':
    for category in categories:
        get_product_url_by_category(category)
