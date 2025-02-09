import re
import time
import multiprocessing as mp
from dataclasses import dataclass
from typing import Callable, Self

from playwright.sync_api import sync_playwright, Playwright
from word2number import w2n

from page import Page
from session import Session

mp.set_start_method('fork')


class Process(mp.Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__is_crashed = False

    def run(self) -> None:
        try:
            super().run()
        except Exception as e:
            self.__is_crashed = True
            raise e

    def is_crashed(self) -> bool:
        return self.__is_crashed


@dataclass
class Task:
    scrape_function: Callable
    data: dict


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


def worker(worker_id: int, task_queue: mp.Queue):
    with sync_playwright() as p:
        with Session(playwright=p) as session:
            while not task_queue.empty():
                task = task_queue.get(timeout=2)
                func = task.scrape_function
                kwargs = task.data
                print(f'Worker {worker_id} performing {func.__name__} with {kwargs}')
                kwargs.update({'session': session})
                try:
                    func(**kwargs)
                except Exception as e:
                    print(f'Something went wrong {e}')
                    raise e


class ProcessManager:
    tasks = mp.Queue()
    result = []

    def __init__(self, num_processes: int = 3):
        self.num_processes = num_processes
        self.workers = {}
        self.health_checker = None

    @classmethod
    def add_task(cls, task: Task | None):
        cls.tasks.put(task)

    def start_worker(self, worker_id):
        work_process = Process(target=worker, args=(worker_id, self.tasks))
        work_process.start()
        self.workers[worker_id] = work_process
        print(f'Worker {worker_id} started')

    def check_health(self):
        try:
            while any(work_process.is_alive() for work_process in self.workers.values()):
                for worker_id, work_process in list(self.workers.items()):
                    if work_process.is_crashed():
                        print(f'WARNING: Worker {worker_id} crashed, restarting...')
                        self.start_worker(worker_id)
                print('INFO: Health checked')
                time.sleep(3)
        finally:
            self.shutdown()

    def start(self) -> Self:
        print('Starting...')
        with sync_playwright() as p:
            with Session(playwright=p) as session:
                page = session.go_to(root='')
                page_qty = int(page.find('//*[@class="current"]').text.strip().split(' ')[-1])
        for page_number in range(1, page_qty + 1):
            self.add_task(Task(scrape_function=collect_book_links_on_page, data={'page_number': page_number}))
        for i in range(1, self.num_processes + 1):
            self.start_worker(i)
        self.check_health()
        return self

    def shutdown(self):
        print('Gathering data and shutting down...')
        for work_process in self.workers.values():
            work_process.join()
        print('Books collected', len(self.result))
        print('All workers shut down.')


if __name__ == '__main__':
    ProcessManager().start()