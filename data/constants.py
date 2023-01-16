MAX_COUNT = 100
MAX_POSTS_COUNT = 1

START_PARSER_INTERVAL = 120  # in seconds
START_DB_CLEAN_INTERVAL = 12  # in hours

PARSER_SLEEP_INTERVAL_SECONDS = 60 * 5


PARSER_LINKS = {
    'bazos': {
        'link': 'https://mobil.bazos.cz/',
        'currency': 'CZK',
        'match_pattern': r"(https://){0,1}(.+\.bazos\.cz/{0,1}.*)",
        'match_group': 2,
        'search': 'www.bazos.cz/search.php?hledat={search_word}&rubriky=www&hlokalita=&humkreis=1000&cenaod=&cenado=&Submit=Hledat&kitx=ano',
    },
    'sakaryateknoloji': {
        'link': 'https://www.sahibinden.com/en/computers',
        'currency': 'TL',
        'match_pattern': r"(https://){0,1}(.+\.bazos\.cz/{0,1}.*)",
        'match_group': 2,
        'search': 'www.bazos.cz/search.php?hledat={search_word}&rubriky=www&hlokalita=&humkreis=1000&cenaod=&cenado=&Submit=Hledat&kitx=ano',
    },

}
