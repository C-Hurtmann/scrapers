import os

from playwright.sync_api import sync_playwright, Playwright, Page


links = []


class Session:
    BASE_URL = 'https://books.toscrape.com'

    def __init__(self, playwright: Playwright) -> None:
        self._browser = playwright.chromium.launch(headless=True)
        self.current_page = self._browser.new_page()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._browser.close()

    def go_to(self, root: str):
        url = self.BASE_URL + '/' + root
        print('Perform req', url)
        resp = self.current_page.goto(url=url)
        self.current_page.wait_for_load_state("load")
        if not 200 <= resp.status < 400:
            raise Exception('Invalid response', resp.status)
        return self.current_page


def collect_book_links_on_page(page: Page):
    links_on_page = page.locator('//*[@class="image_container"]//a').all()
    for index, link_element in enumerate(links_on_page, start=1):
        link = link_element.get_attribute('href')
        links.append(link)


def fetch_data(page: Page):
    image_link = page.url.replace('index.html', '') + page.locator('//img').first.get_attribute('src')
    print(image_link)


def main():
    with sync_playwright() as p:
        with Session(playwright=p) as session:
            page = session.go_to(root='')
            page_qty = int(page.locator('//*[@class="current"]').first.text_content().strip().split(' ')[-1])
            print(page_qty)
            page_number = 1
            while True:
                try:
                    page = session.go_to(root=f'catalogue/page-{page_number}.html')
                except Exception:
                    break
                else:
                    page_number += 1
                    collect_book_links_on_page(page=page)

            for link in links:
                page = session.go_to(root='catalogue/' + link)
                with open('logs/book.html', 'w') as f:
                    f.write(page.content())
                fetch_data(page=page)
                break


if __name__ == '__main__':
    main()