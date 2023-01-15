import asyncio
import concurrent.futures
import json

import cloudscraper


# обертки для запуска функции, блокирующей io
async def run_blocking_io(func, *args):
    # получаем loop
    loop = asyncio.get_running_loop()
    # выполняем функцию func с аргументами *args с помощью объекта ThreadPoolExecutor в полученном loop`е
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
        # возвращаем результат выполнения функции
        return result


def write_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(data)


def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = f.read()
    return data


def write_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_dict_string(string):
    start_index = None
    end_index = None
    start_count = 0
    end_count = None
    for i in range(len(string)):
        val = string[i]
        if val == '{':
            if start_index is None:
                start_index = i
            start_count += 1
        if val == '}':
            if end_count is None:
                end_count = 0
            end_index = i
            end_count += 1
        if start_count == end_count:
            return string[start_index: end_index + 1]


def cloudscraper_get(url, proxy):
    scraper = cloudscraper.create_scraper()
    proxies = {"http": proxy, "https": proxy}
    proxies = None
    print(url)
    req = scraper.get(url, proxies=proxies)
    return req.text


async def async_cloudscraper_get(url, proxy):
    return await run_blocking_io(cloudscraper_get, url, proxy)
