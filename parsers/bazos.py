import random
from urllib.parse import urlparse

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
from parsers.exceptions import CancelError
from parsers.utils import write_file, read_file

codes = {
    'cz': '+420',
    'at': '+43',
    'pl': '+48',
    'sk': '+421'
}


class Post(BaseModel):
    views: int
    created: datetime
    title: str
    description: str
    price: Optional[int]
    town: str
    link: HttpUrl
    seller_name: str
    photo_url: HttpUrl
    phone: Optional[str]
    seller_posts: Optional[int]
    seller_url: str


async def fetch_post(url, proxy, tokens: list = None) -> Post:
    page_id = url.split("/")[-2].split("-")[0]

    logger.debug("fetching post: {}", url)
    if not tokens:
        tokens = ['LN2UNBJV38']
    random.shuffle(tokens)
    # cookies = dict(
    #     # testcookie='ano',
    #     bkod='LN2UNBJV38',
    #     # bid='57696254'
    # )
    async with aiohttp.ClientSession() as session:
        async with session.get(
                url,
                headers={"user-agent": user_agent},
                proxy=proxy,
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
        views = None
        price = None
        seller_posts = None
        for tr in trs:
            tds = tr.find_all('td')
            names = ['Jméno', 'Meno', 'Imię', 'Name']
            if any([name in tds[0].getText(strip=True) for name in names]):
                # if 'Jméno' in tds[0].getText(strip=True):
                seller_a = tds[-1].find('a')
                seller_name = seller_a.getText(strip=True)
                seller_url = seller_a.get('href')
            towns = ['Lokalita', 'Lokalita', 'Lokalizacja', 'Lokalität']
            if any([town in tds[0].getText(strip=True) for town in towns]):
                # if 'Lokalita' in tds[0].getText(strip=True):
                town = tds[-1].getText(strip=True, separator=', ')
            views_names = ['Vidělo', 'Gesehen', 'Widziało', 'Videlo']
            if any([views_name in tds[0].getText(strip=True) for views_name in views_names]):
                # if 'Vidělo' in tds[0].getText(strip=True):
                views = int(tds[-1].getText(strip=True).split(' ')[0])
            price_names = ['Cena', 'Preis']
            if any([price_name in tds[0].getText(strip=True) for price_name in price_names]):
                # if 'Cena' in tds[0].getText(strip=True):
                try:
                    price = int(tds[-1].getText(strip=True).replace('Kč', '').replace('€', '').replace('zł', '')
                                .replace(' ', ''))
                except:
                    price = None
        photo_url = soup.find('meta', {'property': 'og:image'}).get('content')
        '//div[@class="inzeratydetnadpis"]//span[@class="velikost10"]'
        created_text = soup.find('div', {'class': 'inzeratydetnadpis'}).find('span', {'class': 'velikost10'}).getText()
        created = parse(created_text.replace(' ', ''), fuzzy_with_tokens=True, dayfirst=True)[0]

        # phone_url = 'https://zvirata.bazos.cz/detailtel.php?idi=159742718&idphone=3438270'

        try:
            country = url.split('bazos.')[-1].split('/')[0]
            url_parts = urlparse(url)

            phone_link = soup.find('span', {'class': 'teldetail'}).get('onclick').split("('")[-1].split("')")[0]

            phone_url = f'{url_parts.scheme}://{url_parts.netloc}{phone_link}'
            logger.debug(phone_url)
            for token in tokens:
                async with session.get(
                        phone_url,
                        headers={"user-agent": user_agent},
                        proxy=proxy,
                        cookies={'bkod': token}
                ) as phone_resp:
                    phone_html = await phone_resp.text()
                    phone_soup = BeautifulSoup(phone_html, "lxml")
                    try:
                        # 'max tel' - значение номера при лимите
                        phone = phone_soup.find('a', {'class': 'teldetail'}).getText(strip=True)
                        if 'max' in phone or 'tel' in phone:
                            logger.warning(phone)
                            phone = None
                        else:
                            phone = codes[country] + phone
                            break
                    except AttributeError:
                        phone = None
        except Exception as ex:
            phone = None
        print(phone)

        async with session.get(
                seller_url,
                headers={"user-agent": user_agent},
                proxy=proxy,
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

    return Post(
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


async def bazos_parse(url, proxy, skip_tops: bool, token: list = None, page_sleep: int = 1):
    start_url = url
    page_id = 1
    print(f'{proxy=}')
    domain = f'https://{urllib_parse.urlsplit(url).netloc}'
    try_count = 3
    while try_count > 0:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        url,
                        headers={"user-agent": user_agent},
                        proxy=proxy
                ) as resp:
                    html = await resp.text()
                    print(f"{resp.url=}")
                    # print("html", resp)
                    # write_file('parsers/source/bazos_cz.html', html)
                soup = BeautifulSoup(html, "lxml")

                posts = soup.find_all('div', {'class': 'inzeraty inzeratyflex'})
                if not posts:
                    logger.error("search_results empty!")
                    await sleep(5)
                    break
                pages = []
                for post in posts:
                    link = post.find('a').get('href')
                    if 'https' not in link:
                        link = domain + link
                    date_text = post.find('span', {'class': 'velikost10'}).getText()
                    if 'TOP' in date_text:
                        is_top = True
                    else:
                        is_top = False
                    context = dict(
                        url=link,
                        is_top=is_top
                    )
                    pages.append(context)
                get_posts = len(pages)
                for page in pages:
                    if page['is_top'] and skip_tops:
                        continue
                    try:
                        post = await fetch_post(page['url'], proxy, token)
                        yield post, get_posts, start_url

                        get_posts = None
                    except CancelError as ex:
                        logger.debug("CancelError - {}", ex)
                        await sleep(5)
                    except Exception as ex:
                        logger.exception(ex)
                # next_names = ['Ďalšia', 'Další', 'Następna', 'Nächste']
                # next_page = soup.find('a', text=lambda x: any([next_name in x for next_name in next_names]) if x else None)
                next_page = soup.find('a', text=re.compile('Ďalšia|Další|Następna|Nächste'))
                if next_page:
                    next_page_url = next_page.get('href')
                    if next_page_url[0] != '/':
                        next_page_url = '/' + next_page_url
                    url = domain + next_page_url
                else:
                    break
        except GeneratorExit:
            break
        except Exception as exception:
            try_count -= 1
            logger.exception(exception)

        await sleep(page_sleep)


async def main():
    url1 = 'https://mobil.bazos.cz/'
    url2 = 'https://mobil.bazos.cz/motorola/220/'
    url3 = 'https://www.bazos.cz/search.php?hledat=apple&rubriky=www'
    url4 = 'https://zvierata.bazos.sk/'
    url5 = 'https://www.bazos.pl/search.php?hledat=iphone&rubriky=www&hlokalita=&humkreis=1000&cenaod=&cenado=&Submit=Szukaj&kitx=ano'
    url6 = 'https://tiere.bazos.at/'
    proxy = f'http://nophantom_mail_ru:16963efa00@192.144.9.158:30001'
    async for post, get_posts, start_url in bazos_parse(url6, proxy):
        print(post, get_posts)


async def main1():
    url1 = 'https://zvirata.bazos.cz/inzerat/160669489/africke-cichlidy-jezera-malawi-brno-venkov.php'
    url2 = 'https://auto.bazos.cz/inzerat/161396975/skoda-superb-20-tdi-140kw-dsg-sportline-led-navi-kamera.php'
    proxy = f'http://nophantom_mail_ru:16963efa00@192.144.11.207:30001'
    res = await fetch_post(url2, proxy)
    print(res)


if __name__ == "__main__":
    asyncio.run(main1())
