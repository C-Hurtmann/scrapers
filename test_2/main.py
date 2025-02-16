import re
import time
import multiprocessing as mp
import pandas as pd
from collections import namedtuple
from typing import Self

from playwright.sync_api import sync_playwright
from word2number import w2n

from test_2.core import Session

mp.set_start_method('fork')


class ProcessCrashedError(Exception):
    pass


Task = namedtuple('Task', 'scrape_function, data')


def collect_book_links_on_page(session: Session, page_number: int) -> None:
    page = session.go_to(root=f'catalogue/page-{page_number}.html')
    for link in page.find('//*[@class="image_container"]//a', all=True).link:
        ProcessManager.add_task(Task(scrape_function=fetch_data, data={'link': 'catalogue/' + link}))


def fetch_data(session: Session, link: str) -> None:
    page = session.go_to(root=link)
    image_link = page.url.replace('index.html', '') + page.find('//img').image
    title = page.find('//h1').text
    category = page.find('//ul[@class="breadcrumb"]/li[position() = last() - 1]').text.strip()
    price_raw = page.find('//*[@class="price_color"]').text
    price = int(float(re.search(r'\d+\.\d+', price_raw).group()) * 100)
    available = int(
        re.sub(r'\D', '', page.find('//*[@class="instock availability"]').text)
    )
    rating = w2n.word_to_num(
        page.find(
            '//*[contains(@class, "star-rating")]'
        ).raw.get_attribute('class').replace('star-rating ', '')
    )
    description = page.find('//div[@id="product_description"]/following-sibling::p', required=False).text

    product_information = {}
    for row in page.find('//table[@class="table table-striped"]/tbody/tr', all=True).raw:
        product_information[row.locator('//th').text_content()] = row.locator('//td').text_content()

    ProcessManager.result.append(
        {
            'image_link': image_link,
            'title': title,
            'category': category,
            'price': price,
            'available': available,
            'rating': rating,
            'description': description,
            'product_information': product_information

        }
    )


def worker(worker_id: int, task_queue: mp.Queue) -> None:
    with sync_playwright() as p:
        with Session(playwright=p) as session:
            while not task_queue.empty():
                task = task_queue.get(timeout=2)
                func = task.scrape_function
                kwargs = task.data.copy()
                print(f'Worker {worker_id} performing {func.__name__} with {kwargs}')
                kwargs.update({'session': session})
                try:
                    func(**kwargs)
                except Exception as e:
                    print(f'Something went wrong {e}')
                    task_queue.put(task, timeout=2)
                    time.sleep(2)
                    raise ProcessCrashedError


class ProcessManager:
    manager = mp.Manager()
    tasks = manager.Queue()
    result = manager.list()

    def __init__(self, num_processes: int = 3) -> None:
        self.num_processes = num_processes
        self.workers = {}
        self.health_checker = None

    @classmethod
    def add_task(cls, task: Task) -> None:
        cls.tasks.put(task)

    def get_result(self) -> list[dict]:
        return list(self.result)

    def start_worker(self, worker_id: int) -> None:
        work_process = mp.Process(target=worker, args=(worker_id, self.tasks))
        work_process.start()
        self.workers[worker_id] = work_process
        print(f'Worker {worker_id} started')

    def check_health(self) -> None:
        print('Starting health checker')
        number_of_crashes = 0
        try:
            while not self.tasks.empty():
                for worker_id, work_process in list(self.workers.items()):
                    if not work_process.is_alive():
                        print(f'WARNING: Worker {worker_id} crashed, restarting...')
                        number_of_crashes += 1
                        self.start_worker(worker_id)
                    else:
                        print('INFO: Health checked')
                        time.sleep(3)
        finally:
            print(f'Finishing scrapping with {number_of_crashes} crashes')
            self.shutdown()

    def start(self) -> Self:
        print('Starting...')
        with sync_playwright() as p:
            with Session(playwright=p) as session:
                page = session.go_to(root='')
                page_qty = int(page.find('//*[@class="current"]', no_bombs=True).text.strip().split(' ')[-1])
        for page_number in range(1, page_qty + 1):
            self.add_task(Task(scrape_function=collect_book_links_on_page, data={'page_number': page_number}))
        for i in range(1, self.num_processes + 1):
            self.start_worker(i)
        self.check_health()
        return self

    def shutdown(self) -> None:
        print('Gathering data and shutting down...')
        for work_process in self.workers.values():
            work_process.join()
        print('All workers shut down')


if __name__ == '__main__':
    result = ProcessManager().start().get_result()
    df = pd.DataFrame(list(result))
    print(df)
