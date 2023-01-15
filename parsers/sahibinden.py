import json
import platform
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from dateutil.parser import parse
from loguru import logger
from pydantic import BaseModel, HttpUrl
from pyvirtualdisplay import Display
from selenium.common import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import scheduler
from data.constants import PARSER_SLEEP_INTERVAL_SECONDS, START_DB_CLEAN_INTERVAL
from models import Parser, Post, ParserFirstBanned, Alert, User, ParserBanned, get_datetime_now
from parsers.all import get_proxy
from parsers.extra import create_proxy_plugin


@dataclass
class AlertMessage:
    cookies_error = 'cookies_error'
    need_cookies = 'need_cookies'
    other_error = 'other_error'


class NoProxyError(Exception):
    pass


class PostData(BaseModel):
    post_id: str
    created: datetime
    title: str
    description: str
    price: Optional[int]
    town: str
    link: HttpUrl
    seller_name: str
    seller_id: str
    photo_url: Optional[HttpUrl]
    seller_posts: Optional[int]
    seller_rating: Optional[float]
    seller_reviews: Optional[int]
    seller_reg: datetime
    business_account: bool


plugin_save_path = 'proxy.zip'
cookies_path = 'cookies.json'


class SahibindenParser:
    def __init__(self):
        self._create_driver()
        self.login_url = 'https://secure.sahibinden.com/login'

    def _create_driver(self):
        proxy = get_proxy()
        if proxy:
            proxy_host, proxy_port, proxy_username, proxy_password = proxy
        else:
            raise NoProxyError
        if platform.system() == 'Linux':
            self.disp = Display(visible=0, size=(1920, 1080))
            self.disp.start()
        proxy_plugin = create_proxy_plugin(proxy_host, proxy_port, proxy_username, proxy_password, plugin_save_path)
        # options = webdriver.ChromeOptions()
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument('--start-maximized')
        # # options.binary_location = "/usr/bin/google-chrome"
        # options.add_extension(proxy_plugin)
        # options.add_experimental_option("excludeSwitches",
        #                                 ["ignore-certificate-errors",
        #                                  "safebrowsing-disable-download-protection",
        #                                  "safebrowsing-disable-auto-update",
        #                                  "disable-client-side-phishing-detection",
        #                                  "enable-automation",
        #                                  "enable-logging"])
        # options.add_experimental_option('useAutomationExtension', False)
        # options.add_argument("--disable-blink-features=AutomationControlled")
        #
        # options.add_argument("--mute-audio")
        # options.add_argument("disable-infobars")
        # options.add_argument("disable-translate")
        # options.add_argument("disable-notifications")
        # options.add_argument("disable-popup-blocking")
        # self.driver = uc.Chrome(options=options)
        try_count = 3
        while try_count > 0:
            try:
                self.driver = uc.Chrome(version_main=108)
                break
            except ConnectionResetError:
                try_count -= 1
                time.sleep(1)

    def quit_driver_method(self):
        self.driver.quit()
        if hasattr(self, 'disp'):
            self.disp.stop()

    def login(self):
        self.driver.get(self.login_url)

        with open(cookies_path, 'r') as f:
            cookies = json.load(f)

        for cookie in cookies:
            if 'sameSite' in cookie:
                del cookie['sameSite']
            self.driver.add_cookie(cookie)

        self.driver.refresh()
        try:
            WebDriverWait(self.driver, 5, 0.2).until(
                EC.url_changes(self.login_url)
            )
            return True
        except TimeoutException:
            return False

    def _get_seller_posts(self, seller_posts_url):
        self.driver.get(seller_posts_url)
        source = self.driver.page_source
        soup = BeautifulSoup(source, 'lxml')
        try:
            seller_posts = soup.find('div', {'class': 'classified-count'}).find('strong').getText()
        except AttributeError:
            seller_posts = soup.find('div', {'class': 'result-text'}).find('span').getText().split()[0]
        seller_posts = int(seller_posts)
        return seller_posts

    def _get_seller_reviews(self, seller_reviews_url):
        self.driver.get(seller_reviews_url)
        source = self.driver.page_source
        soup = BeautifulSoup(source, 'lxml')
        seller_reviews_count = int(soup.find('div', {'class': 'rate-count'}).find('span').getText())
        return seller_reviews_count

    def fetch_post(self, post_url, context: dict) -> PostData:
        logger.debug("fetching post: {}", post_url)
        created = context['created']
        title = context['title']
        post_id = context['post_id']
        price = context['price']
        town = context['town']

        self.driver.get(post_url)
        source = self.driver.page_source
        soup = BeautifulSoup(source, 'lxml')
        seller_links = soup.find('ul', {'class': 'userLinks'}).find_all('li')
        seller_posts_url = seller_links[0].find('a', {'id': 'ownersClassifieds'}).get('href')
        description = soup.find('div', {'id': 'classifiedDescription'}).getText(strip=True, separator=' ')
        business_account = False
        seller_name = soup.find('div', {'class': 'paris-name'}).find('span').getText(strip=True)
        photo_url = soup.find('img', {'class': 'stdImg'}).get('src')
        try:
            seller_reg = soup.find('p', {'class': 'userRegistrationDate'}).find('span').getText(strip=True)
        except AttributeError:
            business_account = True
            seller_reg = soup.find('div', {'id': 'badge'}).find('strong').getText(strip=True)
        seller_reg = parse(seller_reg)
        try:
            seller_rating = float(soup.find('span', {'class': 'feedback-average'}).getText(strip=True))
            seller_reviews_url = seller_links[1].find('a').get('href')
            if not seller_reviews_url.startswith('http'):
                seller_reviews_url = 'https://www.sahibinden.com' + seller_reviews_url
            seller_reviews_count = self._get_seller_reviews(seller_reviews_url)
        except AttributeError:
            seller_rating = None
            seller_reviews_count = None

        if not seller_posts_url.startswith('http'):
            seller_posts_url = 'https://www.sahibinden.com' + seller_posts_url
        seller_id = seller_posts_url.split('userId=')[-1]
        seller_posts = self._get_seller_posts(seller_posts_url)
        post = PostData(
            link=post_url,
            created=created,
            business_account=business_account,
            title=title,
            post_id=post_id,
            price=price,
            seller_reg=seller_reg,
            seller_reviews=seller_reviews_count,
            seller_posts=seller_posts,
            seller_rating=seller_rating,
            description=description,
            town=town,
            seller_name=seller_name,
            seller_id=seller_id,
            photo_url=photo_url,
        )
        return post

    def _processing_error(self, error_text=None) -> str:
        if error_text:
            self._append_error_alert(error_text)
            logger.warning(f'detected error: {error_text}')
            return error_text
        current_url = self.driver.current_url
        if 'login' in current_url:
            error_text = AlertMessage.need_cookies
            self._append_error_alert(error_text)
            return error_text
        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        try:
            title = soup.find('title').getText()
        except AttributeError:
            title = ''
        if 'login' in title:
            error_text = AlertMessage.need_cookies
            self._append_error_alert(error_text)
            return error_text
        error_text = AlertMessage.other_error
        logger.warning(f'detected error: {error_text}')
        self._append_error_alert(error_text)
        return error_text

    def _append_error_alert(self, error_text):
        alerts = Alert.select()
        if not alerts:
            Alert.create(
                message=error_text
            )

    def _check_pars_filter(self, post: PostData, pars_filter: dict, owner: User) -> bool:
        seller_id = post.seller_id
        banned = ParserBanned.get_or_none(
            owner=owner,
            seller=seller_id
        )
        if banned:
            return False
        check = True
        reg_date = pars_filter['reg_date']
        max_posts = pars_filter['max_posts']
        max_reviews = pars_filter['max_reviews']
        if reg_date:
            if reg_date > post.seller_reg:
                check = False
        if max_posts is not None:
            if post.seller_posts > max_posts:
                check = False
        if max_posts is not None:
            if post.seller_posts > max_posts:
                check = False
        if max_reviews is not None:
            if post.seller_reviews > max_reviews:
                check = False
        if check:
            ParserBanned.create(
                owner=owner,
                seller=seller_id
            )
        return check

    def _add_post(self, post: PostData, url: str):
        parsers = Parser.select().where(Parser.url == url)
        # owners = [parsers.owner for parsers in parsers]
        for parser in parsers:
            owner = parser.owner
            pars_filter: dict = parser.pars_filter
            if self._check_pars_filter(post, pars_filter, owner):
                owner = parser.owner
                Post.create(
                    owner=owner,
                    post_json=json.loads(post.json())
                )
        # insert_data = [
        #     dict(
        #         owner=owner,
        #         post_json=json.loads(post.json())
        #     )
        #     for owner in owners
        # ]
        # Post.insert_many(insert_data).execute()
        # for owner in owners:
        #     Post.create(
        #         owner=owner,
        #         post_json=json.loads(post.json())
        #     )
        pass

    def _skip_post(self, search_url, post_id: str) -> bool:
        already_pars_link = ParserFirstBanned.get_or_none(
            search_url=search_url,
            post=post_id
        )
        if already_pars_link:
            return True
        ParserFirstBanned.create(
            search_url=search_url,
            post=post_id
        )
        return False

    def parser(self, context: dict):
        url = context['url']
        first_pars = context.get('first_pars', False)
        logger.debug("get search url: {}", url)
        self.driver.get(url)
        while True:
            time.sleep(0.1)
            source = self.driver.page_source
            soup = BeautifulSoup(source, 'lxml')
            posts = soup.find('tbody', {'class': 'searchResultsRowClass'}).find_all('tr',
                                                                                    {'class': 'searchResultsItem'})
            print(f'{len(posts)=}')
            logger.debug(f'{len(posts)=}')
            if first_pars:
                posts = posts[::-1][:-4]
            for post in posts[:3]:
                try:
                    post_id = post.get('data-id')
                    if self._skip_post(url, post_id):
                        continue
                    try:
                        post_url = 'https://www.sahibinden.com' + post.find('a').get('href')
                    except AttributeError:
                        continue
                    title = post.find('a').get('title')
                    town = post.find('td', {'class': 'searchResultsLocationValue'}).getText(strip=True,
                                                                                            separator=' ').strip()
                    price = post.find('div', {'class': 'classified-price-container'}).getText(strip=True).split(' ')[0]
                    price = float(price.replace(',', '').strip())
                    created = post.find('td', {'class': 'searchResultsDateValue'}).getText(strip=True)
                    created = parse(created)
                    context = dict(
                        created=created,
                        post_id=post_id,
                        price=price,
                        title=title,
                        town=town
                    )
                    post = self.fetch_post(post_url, context)
                    # print(post)
                    self._add_post(post, url)
                except Exception as e:
                    traceback.print_exc()
            if first_pars:
                break
            last_page = soup.find('ul', {'class': 'pageNaviButtons'}).find_all('a')[-1]
            # next_page = None
            if last_page.get('class')[0] == 'prevNextBut':
                next_page = 'https://www.sahibinden.com' + last_page.get('href')
                self.driver.get(next_page)
            else:
                break

    # @sync_to_async
    def start_parser(self):
        Alert.delete().execute()
        already_log = False
        while True:
            # uniq_urls = [
            #     # 'https://www.sahibinden.com/satilik?sorting=date_desc',
            #     'https://www.sahibinden.com/en/computers?sorting=date_desc'
            # ]
            parsers = Parser.select().group_by(Parser.url)
            uniq_urls = [parser.url for parser in parsers]
            # print(uniq_urls)
            logger.info(f'{uniq_urls=}')

            alert = Alert.select().first()
            if alert:
                if alert.message == AlertMessage.need_cookies:
                    already_log = False
                # print('alert')
                logger.warning(f'alert: {alert.message}')
                self.driver.get('chrome://new-tab-page/')
                logger.debug(f'sleep {PARSER_SLEEP_INTERVAL_SECONDS} s')
                time.sleep(PARSER_SLEEP_INTERVAL_SECONDS)
                continue
            if not already_log:
                login_result = self.login()
            else:
                login_result = True
            if not login_result:
                print('bad login')
                logger.warning(f'bad login')
                self._processing_error(AlertMessage.need_cookies)
                self.driver.get('chrome://new-tab-page/')
                logger.debug(f'sleep {PARSER_SLEEP_INTERVAL_SECONDS} s')
                time.sleep(PARSER_SLEEP_INTERVAL_SECONDS)
                continue
            else:
                already_log = True
                print('good login')
                logger.info(f'good login')
                time.sleep(1)
                for url in uniq_urls:
                    # self.driver.get(url)
                    context = dict(
                        url=url
                    )
                    try:
                        self.parser(context)
                    except Exception as ex:
                        logger.exception(ex)
                        # error_text = self._processing_error()

                    # time.sleep(1000)
                    Parser.update(first_run=False).where(Parser.url == url).execute()
            self.driver.get('chrome://new-tab-page/')
            logger.debug(f'sleep {PARSER_SLEEP_INTERVAL_SECONDS} s')
            time.sleep(PARSER_SLEEP_INTERVAL_SECONDS)


def sahibinden_parser():
    sahibinden = SahibindenParser()
    sahibinden.start_parser()


def clear_last_posts():
    now = get_datetime_now() - timedelta(days=1)
    count = ParserFirstBanned.delete().where(ParserFirstBanned.created < now).execute()
    logger.debug('cleaned {} last posts', count)


def append_scheduler_job():
    scheduler.add_job(sahibinden_parser, 'date', run_date=datetime.now())
    scheduler.add_job(clear_last_posts, 'interval', hours=START_DB_CLEAN_INTERVAL)
    scheduler.add_job(clear_last_posts, 'interval', hours=START_DB_CLEAN_INTERVAL)

    logger.debug('added jobs')


if __name__ == '__main__':
    login = 'for.money.make.seo@gmail.com'
    password = 'Ivann235'
    s = SahibindenParser()
    s.start_parser()
    # asyncio.run(s.start_parser())
