from parsers import bazos_parse
from parsers.bazos import fetch_post

PARSERS_FUNCTIONS = {
    'bazos': {
        'main': bazos_parse,
        'fetch_post': fetch_post
    }
}
