from playwright.sync_api import Playwright

from page import Page


class Session:
    BASE_URL = 'https://books.toscrape.com'

    def __init__(self, playwright: Playwright) -> None:
        self._browser = playwright.chromium.launch(headless=True)
        self.current_page = self._browser.new_page()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._browser.close()

    def go_to(self, root: str) -> Page:
        url = self.BASE_URL + '/' + root
        print('Perform req', url)
        resp = self.current_page.goto(url=url)
        self.current_page.wait_for_load_state("load")
        if not 200 <= resp.status < 400:
            raise Exception('Invalid response', resp.status)
        return Page(inner_page=self.current_page)

