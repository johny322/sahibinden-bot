from random import choice

from loguru import logger


# def get_proxy():
#     urls = [
#         'http://sQsBgPgR:4Bb6dNL3@88.151.13.211:64644'
#     ]
#
#     proxy_url = choice(urls)
#     # logger.debug("proxy - {}", proxy_url)
#     return proxy_url


def get_proxy():
    # try:
    #     with open(proxies_path, 'r', encoding='utf-8') as f:
    #         proxies = f.readlines()
    # except FileNotFoundError:
    #     with open(proxies_path, 'w', encoding='utf-8') as f:
    #         pass
    #     return
    # if not proxies:
    #     return
    proxies = [
        'sQsBgPgR:4Bb6dNL3@88.151.13.211:64644'
    ]
    proxy = choice(proxies)
    if proxy:
        proxy = proxy.strip()
        first_part, second_part = proxy.split('@')
        proxy_host, proxy_port = second_part.split(':')
        proxy_username, proxy_password = first_part.split(':')
        return proxy_host, proxy_port, proxy_username, proxy_password
    return
