from aiogram.dispatcher.fsm.state import StatesGroup, State


class Mailing(StatesGroup):
    post = State()
    sure = State()


class NewBlackWord(StatesGroup):
    main = State()


class ParserStates(StatesGroup):
    url = State()
    seller_posts = State()
    reg_date = State()
    seller_reviews = State()
    parsing = State()


class Bazos(StatesGroup):
    token = State()
    proxy = State()
    url = State()
    count = State()
    price = State()
    post_date = State()
    skip_tops = State()
    seller_posts = State()
    post_views = State()
    save = State()
    preset = State()
    cancel = State()
    preset_count = State()
    preset_proxy = State()
    preset_token = State()


class BazosTextG(StatesGroup):
    text = State()
    name = State()
