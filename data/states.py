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
