import traceback
from pprint import pprint

from loguru import logger
from asyncio import sleep
from typing import Optional
from datetime import datetime
from urllib import parse as urllib_parse
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl

import re
import aiohttp
import asyncio

from config import user_agent
from dateutil.parser import parse

from parsers.all import get_proxy
from parsers.exceptions import CancelError
from parsers.utils import write_file, read_file


def get_page_offset(page_number):
    # if page_number == 1:
    #     return 0
    return page_number * 20 - 20


def get_start_url(url, page_number):
    params = None
    page_offset = get_page_offset(page_number)
    if 'search' in url:
        params = {
            'crz': page_offset
        }
    else:
        pattern = '/\d{0,}/{0,1}$'
        url = re.sub(pattern, f'/{page_offset}/', url)
    return url, params


class Post(BaseModel):
    views: int
    created: datetime
    title: str
    description: str
    price: Optional[int]
    town: str
    link: HttpUrl
    seller_name: str
    photo_url: Optional[HttpUrl]
    phone: Optional[str]
    seller_posts: Optional[int]
    seller_url: str


async def fetch_post(context: dict) -> Post:
    url = context['url']
    views = context['views']
    page_id = url.split("/")[-2].split("-")[0]

    logger.debug("fetching post: {}", url)
    proxy = get_proxy()
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url,
                headers={"user-agent": user_agent},
                proxy=proxy
        ) as resp:
            html = await resp.text()
            # write_file('source/bazos_cz.html', html)
        # html = read_file('source/bazos_cz.html')

        soup = BeautifulSoup(html, "lxml")
        title = soup.find('h1').getText(strip=True)
        description = soup.find('div', {'class': 'popisdetail'}).getText(strip=True)
        table = soup.find('td', {'class': 'listadvlevo'})
        trs = table.find_all('tr')
        seller_name = None
        town = None
        # views = None
        price = None
        seller_posts = None
        for tr in trs:
            tds = tr.find_all('td')
            if 'Jméno' in tds[0].getText(strip=True):
                seller_a = tds[-1].find('a')
                seller_name = seller_a.getText(strip=True)
                seller_url = seller_a.get('href')
            if 'Lokalita' in tds[0].getText(strip=True):
                town = tds[-1].getText(strip=True, separator=', ')
            # if 'Vidělo' in tds[0].getText(strip=True):
            #     views = int(tds[-1].getText(strip=True).split(' ')[0])
            if 'Cena' in tds[0].getText(strip=True):
                price_text = tds[-1].getText(strip=True)
                try:
                    price = int(price_text.replace('Kč', '').replace(' ', ''))
                except ValueError:
                    price = None
        try:
            photo_url = soup.find('meta', {'property': 'og:image'}).get('content')
        except AttributeError:
            photo_url = None
        '//div[@class="inzeratydetnadpis"]//span[@class="velikost10"]'
        created_text = soup.find('div', {'class': 'inzeratydetnadpis'}).find('span', {'class': 'velikost10'}).getText()
        created = parse(created_text.replace(' ', ''), fuzzy_with_tokens=True, dayfirst=True)[0]
        async with session.get(
                seller_url,
                headers={"user-agent": user_agent},
                proxy=proxy
        ) as resp:
            seller_html = await resp.text()
        seller_soup = BeautifulSoup(seller_html, "lxml")
        try:
            seller_posts_text = seller_soup.find('div', {'class': 'inzeratynadpis'}).getText()
            match = re.search(r'\d{1,}', seller_posts_text)
            if match:
                seller_posts = int(match.group(0))
        except:
            seller_posts = None

        phone = None
    post = Post(
        link=url,
        views=views,
        created=created,
        title=title,
        description=description,
        price=price,
        town=town,
        photo_url=photo_url,
        seller_name=seller_name,
        phone=phone,
        seller_posts=seller_posts,
        seller_url=seller_url
    )
    return post


async def bazos_parse(url, page_sleep: int = 2):
    domain = f'https://{urllib_parse.urlsplit(url).netloc}'
    proxy = get_proxy()
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    url,
                    headers={"user-agent": user_agent},
                    proxy=proxy
            ) as resp:
                html = await resp.text()
                # print("html", resp)
            soup = BeautifulSoup(html, "lxml")

            posts = soup.find_all('div', {'class': 'inzeraty inzeratyflex'})
            if not posts:
                logger.error("search_results empty!")
                await sleep(5)
                break
            pages = []
            for post in posts:
                link = post.find('a').get('href')
                if 'https' in link:
                    pages.append(link)
                else:
                    pages.append(domain + link)
            yield pages
            for page in pages:
                try:
                    post = await fetch_post(page)
                    yield post

                except CancelError as ex:
                    logger.debug("CancelError - {}", ex)
                    await sleep(5)
                except Exception as ex:
                    logger.exception(ex)

            next_page = soup.find('a', text=re.compile('Další'))
            if next_page:
                url = domain + next_page.get('href')
            else:
                break

        await sleep(page_sleep)


async def new_bazos_parse(url, start_page_number: int = 1, page_number: int = 2):
    domain = f'https://{urllib_parse.urlsplit(url).netloc}'
    try_count = 3
    url, params = get_start_url(url, start_page_number)
    while try_count > 0:
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug('Category url: {}', url)
                async with session.get(
                        url,
                        headers={"user-agent": user_agent},
                        params=params,
                        proxy=get_proxy()
                ) as resp:
                    html = await resp.text()
                    # print("html", resp)
                soup = BeautifulSoup(html, "lxml")
                posts = soup.find_all('div', {'class': 'inzeraty inzeratyflex'})
                if not posts:
                    logger.error("search_results empty!")
                    await sleep(5)
                    break
                try:
                    current_page_number = int(soup.find('span', {'class': 'cisla'}).getText(strip=True))
                except AttributeError:
                    page_title = soup.find('title').getText(strip=True)
                    pattern = 'strana (\d{1,})'
                    search = re.search(pattern, page_title)
                    if search:
                        current_page_number = int(search.group(1))
                    else:
                        current_page_number = 1
                pages = []
                for post in posts:
                    link = post.find('a').get('href')
                    if 'https' not in link:
                        link = domain + link
                    views = int(post.find('div', {'class': 'inzeratyview'}).getText().replace('x', '').strip())
                    date_text = post.find('span', {'class': 'velikost10'}).getText()
                    if 'TOP' in date_text:
                        is_top = True
                    else:
                        is_top = False
                    context = dict(
                        url=link,
                        views=views,
                        is_top=is_top
                    )
                    pages.append(context)
                # print(pages)
                yield pages, current_page_number

                next_page = soup.find('a', text=re.compile('Další'))
                if next_page:
                    next_page = next_page.get('href')
                    if next_page[0] != '/':
                        next_page = '/' + next_page
                    url = domain + next_page
                    # print(url)
                else:
                    break
        except GeneratorExit:
            break
        except Exception as exception:
            try_count -= 1
            logger.exception(exception)
        # await sleep(page_sleep)


async def main():
    url1 = 'https://mobil.bazos.cz/'
    url2 = 'https://mobil.bazos.cz/motorola/220/'
    url3 = 'https://www.bazos.cz/search.php?hledat=apple&rubriky=www'
    proxy = f'http://raita4205_gmail_com:6122bf63f4@192.144.8.125:30001'
    # async for post, get_posts in bazos_parse(url3):
    #     print(post, get_posts)
    # async for res in bazos_parse(url3):
    #     if isinstance(res, list):
    #         print(res)
    #         await asyncio.sleep(3)
    async for res in new_bazos_parse(url1):
        print(res)


async def main1():
    url1 = 'https://mobil.bazos.cz/inzerat/158421390/ulefone-armor-11-t-5g.php'
    url2 = 'https://www.secondamano.it/altro/informatica-computer-e-videogames/lombardia/milano/7761167-postazione-completa-pc-tower-con-doppio-sistema-operativo-p1'
    url3 = 'https://www.secondamano.it/altro/telefonia/emilia-romagna/modena/8336986-iphone-8-–-64-gb-p1'
    url4 = 'https://mobil.bazos.cz/inzerat/158942492/apple-iphone-x-64-gb-stribrny-12-mesicu-zaruka-jako-novy.php'
    res = await fetch_post(url4)
    print(res)


if __name__ == "__main__":
    asyncio.run(main1())
