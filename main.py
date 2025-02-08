import queue
import threading
import pandas as pd

from collections import namedtuple

from model import Base, ProductDTO, Product
from page import Page
from selector import By
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


ProductTask = namedtuple('ProductTask', ['from_', 'category_name', 'subcategory_name'])
engine = create_engine("sqlite:///products.db")


class TaskQueue(queue.Queue):

    def __init__(self, threads_qty):
        super().__init__()
        self.threads_qty = threads_qty
        self.start_workers()

    def add_task(self, task, *args, **kwargs):
        args = args or ()
        kwargs = kwargs or {}
        self.put((task, args, kwargs))

    def start_workers(self):
        for i in range(self.threads_qty):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()

    def worker(self):
        while True:
            item, args, kwargs = self.get()
            item(*args, **kwargs)
            self.task_done()

    def wait_for_all_tasks(self):
        self.join()


class FlowControl:

    def __init__(self, threads_qty: int) -> None:
        Base.metadata.create_all(engine)
        self.to_read = TaskQueue(threads_qty=threads_qty)
        self.to_write = TaskQueue(threads_qty=1)
        self.session = sessionmaker(bind=engine)()
        self.product_qty_to_check = 0

        self.check_db_connection()
        self.session.query(Product).delete()
        self.session.commit()

    def collect_category_products(self, category_name: str):
        category_page = Page.get(root='/categories/' + category_name)
        subcategories = category_page.find(by=By().class_name('rt-Box rt-r-pb-1').tag('a')).all()
        for category_num, subcategory in enumerate(subcategories, start=1):
            subcategory_name = subcategory.text
            subcategory_link = subcategory.link
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
                    self.product_qty_to_check += 1
                    self.to_read.add_task(
                        self.fetch_product,
                        ProductTask(
                            from_=product.link, category_name=category_name, subcategory_name=subcategory_name
                        )
                    )
                print('TO READ', self.to_read.qsize())

    def fetch_product(self, task: ProductTask) -> None:
        product_page = Page.get(root=task.from_)
        product_dto = ProductDTO(category=task.category_name.capitalize(), subcategory=task.subcategory_name)
        product_dto.collect_from_page(page=product_page)
        self.to_write.add_task(self.save_product, product_dto)

    def save_product(self, product_dto: ProductDTO) -> None:
        print('Perform save', product_dto.title)
        product = Product(
            category=product_dto.category,
            subcategory=product_dto.subcategory,
            title=product_dto.title,
            description=product_dto.description,
            low_price=product_dto.low_price,
            medium_price=product_dto.medium_price,
            high_price=product_dto.high_price,
        )
        self.session.add(product)
        self.session.commit()

    def check_db_connection(self) -> None:
        try:
            self.session.execute(text("SELECT 1"))
        except Exception as e:
            raise f"❌ Database connection failed: {e}"


def main(threads_qty: int, categories: list) -> None:
    print('Starting...')
    try:
        flow_control = FlowControl(threads_qty=threads_qty)
        for category in categories:
            flow_control.collect_category_products(category_name=category)
        flow_control.to_read.wait_for_all_tasks()
        flow_control.to_write.wait_for_all_tasks()
        products = flow_control.session.query(Product).all()
        print(pd.DataFrame([product.to_dict() for product in products]))
        print('PRODUCT QTY TO CHECK', flow_control.product_qty_to_check)
    finally:
        print('THE END')


if __name__ == '__main__':
    categories_ = ['devops', 'it-infrastructure', 'data-analytics-and-management']
    main(threads_qty=5, categories=categories_)
