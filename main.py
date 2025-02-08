import os
import re
import queue
import threading

from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
from dataclasses import dataclass
from pprint import pprint
from time import sleep
from typing import Any, Self
from yarl import URL
from lxml import etree

from element import ElementNotFoundError
from page import Page
from selector import By

CATEGORIES = ['devops']

THREADS_QTY = 3


def write_content(file_name: str, content: Any):
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    with open(f'{logs_dir}/{file_name}.html', 'w', encoding='utf-8') as f:
        f.write(etree.tostring(content, pretty_print=True, encoding='unicode'))


@dataclass
class Product:
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
        return int(re.sub(r'[^\d]', '', price))

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


ProductTask = namedtuple('ProductTask', ['from_', 'category_name', 'subcategory_name'])


class FlowControl:
    to_read = queue.Queue()
    to_write = queue.Queue()

    def __init__(self, threads_qty: int) -> None:
        self.threads_qty = threads_qty


    @classmethod
    def collect_category_products(cls, category_name: str):
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
                    cls.to_read.put(
                        ProductTask(
                            from_=product.link, category_name=category_name, subcategory_name=subcategory_name
                        )
                    )
                print('TO READ', cls.to_read.qsize())

    @classmethod
    def fetch_product(cls, task: ProductTask) -> None:
        product_page = Page.get(root=task.from_)
        product_dto = Product(category=task.category_name.capitalize(), subcategory=task.subcategory_name)
        product_dto.collect_from_page(page=product_page)
        cls.to_write.put(product_dto)
        print('TO WRITE', cls.to_write.qsize())

    def start_worker(self):
        while not self.to_read.empty():
            task = self.to_read.get(timeout=2)
            self.fetch_product(task=task)
            self.to_read.task_done()

    def start(self):
        self.threads = []
        for _ in range(self.threads_qty):
            thread = threading.Thread(target=self.start_worker)
            thread.start()
            self.threads.append(thread)


def main(categories: list) -> None:
    print('Starting...')
    try:
        flow_control = FlowControl(threads_qty=THREADS_QTY)
        for category in categories:
            flow_control.collect_category_products(category_name=category)
        flow_control.start()
    finally:
        print('THE END')


if __name__ == '__main__':
    main(categories=CATEGORIES)
