from parsers import bazos_parse, new_bazos_parse
from parsers.bazos import fetch_post

PARSERS_FUNCTIONS = {
    'bazos': {
        'main': new_bazos_parse,
        'fetch_post': fetch_post
    }
}
