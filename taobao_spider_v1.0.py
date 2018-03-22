# -*- coding: utf-8 -*-
import os
from _md5 import md5
import re
import requests
import sys
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
import pymongo

# MongoDB的url
MONGO_URL = 'localhost'
# MongoDB的库名
MONGO_DB = 'taobao'
# MongoDB的表名
MONGO_TABLE = 'product'

browser = webdriver.Chrome()
wait = WebDriverWait(browser, 10)
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


def search(keywork):
    """
    检索
    """
    try:
        browser.get('http://www.taobao.com')
        search_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#J_TSearchForm > div.search-button > button"))
        )
        search_input.send_keys(keywork)
        submit.click()
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )
        get_product()
        return total.text
    except TimeoutException:
        return search()


def next_page(page_number):
    """
    翻页
    :param page_number: 页码
    :return:
    """
    try:
        page_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
        )
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit"))
        )
        page_input.clear()
        page_input.send_keys(page_number)
        submit.click()
        wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number))
        )
        get_product()
    except TimeoutException:
        next_page(page_number)


def get_product():
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item'))
    )
    html = browser.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'image': 'http:'+item.find('.pic .img').attr('data-src'),
            'price': item.find('.price').text()[2:],
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text(),
        }
        save_to_mongo(product)
        download_image(product['image'])


def save_to_mongo(data):
    try:
        if db[MONGO_TABLE].insert(data):
            print('save success', data)
    except Exception:
        print('save fail', data)


def download_image(url):
    print('Downloading', url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except ConnectionError:
        return None


def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    print(file_path)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()


def main():
    keyword = sys.argv[1]
    if len(keyword) <= 0:
        return None
    else:
        # 关键词总页数
        total = search(keyword)
        total = int(re.compile('(\d+)').search(total).group(1))
        for i in range(2, total+1):
            next_page(i)
    browser.quit()


if __name__ == '__main__':
    main()

