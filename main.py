import os
from pprint import pprint
from typing import Any

import requests
from yarl import URL
from lxml import html, etree


BASE_URL = 'https://www.vendr.com'

categories = ['devops']


def write_content(file_name: str, content: Any):
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)
    with open(f'{logs_dir}/{file_name}.html', 'w', encoding='utf-8') as f:
        f.write(etree.tostring(content, pretty_print=True, encoding='unicode'))


def get_page_content(root: str | URL) -> html.HtmlElement:
    root = str(root)
    print('Perform req', BASE_URL + root)
    res = requests.get(BASE_URL + root)
    return html.fromstring(res.content)


def get_product_url_by_category(category_name: str):
    category_page = get_page_content(root='/categories/' + category_name)
    subcategories = category_page.xpath('//div[@class="rt-Box rt-r-pb-1"]//a')  # TODO create selector class
    write_content(file_name='category_page', content=category_page)
    for category_num, subcategory in enumerate(subcategories, start=1):
        subcategory_name = subcategory.text.lower().replace(' ', '_')
        subcategory_link = URL(subcategory.get('href'))
        page_number = int(subcategory_link.query['page'])
        print(f'{category_num=} | {subcategory_name}\n' + '=' * 100)
        while True:
            updated_link = subcategory_link.with_query(dict(subcategory_link.query) | {'page': page_number})
            page_number += 1

            product_list_page = get_page_content(root=updated_link)
            if not (
                products := product_list_page.xpath(
                    '//div[@class="rt-Grid rt-r-gtc-1 sm:rt-r-gtc-2 rt-r-ai-start rt-r-gap-5"]//a'
                )
            ):
                break
            for product in products:
                product_link = URL(product.get('href'))
                print(product_link)
                product_page = get_page_content(root=product_link)
                write_content(file_name='product_page', content=product_page)
                title = product_page.xpath('//span[@class="rt-Text rt-r-size-5 rt-r-weight-bold"]')[0].text
                description = product_page.xpath(
                    '//div[@class="rt-Flex rt-r-display-none xs:rt-r-display-flex rt-r-fd-row rt-r-gap-1"]//p'
                )[0].text
                low_price = product_page.xpath('//*[@class="v-fw-600 v-fs-12"]')[0].text
                high_price = product_page.xpath(
                    '//*[@class="_rangeSliderLastNumber_118fo_38 v-fw-600 v-fs-12"]'
                )[0].text  # TODO create get text logic
                medium_price = product_page.xpath('//*[@class="v-fw-700 v-fs-24"]')[0].text
                pprint(
                    {
                        'title': title,
                        'category': ...,
                        'subcategory': ...,
                        'description': description,
                        'low_price': low_price,
                        'medium_price': medium_price,
                        'high_price': high_price
                    }
                )
            break
        break


if __name__ == '__main__':
    for category in categories:
        get_product_url_by_category(category)
