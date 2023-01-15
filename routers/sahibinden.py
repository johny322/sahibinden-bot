import json
from json.decoder import JSONDecodeError

from aiogram import Router, types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.fsm.context import FSMContext
from dateutil.parser import parse
from loguru import logger

from config import bot, cookies_path
from data import texts
from data.constants import PARSER_LINKS
from data.keyboards import menu_markup, delete_markup, get_seller_date_markup, cancel_markup, no_count_markup
from data.states import ParserStates
from models import User, Parser, get_datetime_now, Post, Alert

# from parsers import set_first_banned
from routers.filters.admin import MainAdminFilter

router = Router()


@router.callback_query(lambda cb: cb.data.split(":")[-1] == "start")
async def start_parser_handler(query: types.CallbackQuery, state: FSMContext):
    parser_name = query.data.split(":")[0]
    await state.update_data(parser_name=parser_name)
    await query.message.edit_text(
        text=texts.parse_url.format(
            parser_link=PARSER_LINKS[parser_name]['link']
        ),
        reply_markup=delete_markup,
        disable_web_page_preview=True
    )
    await state.set_state(ParserStates.url)


@router.message(ParserStates.url)
async def get_url_handler(message: types.Message, state: FSMContext):
    url = message.text
    await state.update_data(url=url)
    await message.answer(
        text=texts.parse_seller_posts,
        reply_markup=no_count_markup
    )
    await state.set_state(ParserStates.seller_posts)


@router.message(ParserStates.seller_posts)
async def get_seller_posts_handler(message: types.Message, state: FSMContext):
    if not message.text.isdigit() and message.text != "no":
        await message.answer(text=texts.parse_seller_posts_invalid)
        return

    await message.answer(
        text=texts.parse_creator_date,
        reply_markup=get_seller_date_markup()
    )
    if message.text == "no":
        max_posts = None
    else:
        max_posts = int(message.text)
    await state.update_data(max_posts=max_posts)
    await state.set_state(ParserStates.reg_date)


@router.message(ParserStates.reg_date)
async def get_reg_date_handler(message: types.Message, state: FSMContext):
    if message.text == "no":
        await message.answer(
            text=texts.parse_seller_reviews,
            reply_markup=no_count_markup()
        )
        await state.update_data(reg_date=None)
        await state.set_state(ParserStates.seller_reviews)
        return

    try:
        reg_date = parse(message.text)
    except ValueError:
        logger.debug("ValueError reg_date")
        await message.answer(
            text=texts.parse_date_invalid,
            reply_markup=cancel_markup
        )
        return

    if reg_date.year > 2000 and reg_date < get_datetime_now():
        await message.answer(
            text=texts.parse_seller_reviews,
            reply_markup=no_count_markup()
        )
        await state.update_data(reg_date=message.text)
        await state.set_state(ParserStates.seller_reviews)
    else:
        await message.answer(
            text=texts.parse_date_invalid,
            reply_markup=get_seller_date_markup()
        )


@router.message(ParserStates.seller_reviews)
async def get_seller_reviews_handler(message: types.Message, state: FSMContext):
    if not message.text.isdigit() and message.text != "no":
        await message.answer(text=texts.parse_seller_reviews_invalid)
        return
    if message.text.isdigit():
        if int(message.text) > 5:
            await message.answer(text=texts.parse_seller_posts_invalid)
            return
    if message.text == "no":
        max_reviews = None
    else:
        max_reviews = int(message.text)

    data = await state.get_data()
    reg_date = data['reg_date']
    max_posts = data['max_posts']
    url = data['url']
    user = User.get(
        user_id=message.from_user.id
    )
    pars_filter = dict(
        url=url,
        max_reviews=max_reviews,
        reg_date=reg_date,
        max_posts=max_posts
    )

    Parser.create(
        owner=user,
        pars_filter=pars_filter,
        url=url
    )
    await message.answer(
        text=texts.start_parsing_text,
        reply_markup=cancel_markup
    )
    await state.update_data(user=user)
    await state.set_state(ParserStates.parsing)


@router.message(Text(text_contains='отмена', text_ignore_case=True), state=ParserStates.parsing)
async def cancel_parsing_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = data['user']
    Parser.delete().where(Parser.owner == user).execute()
    Post.delete().where(Parser.owner == user).execute()
    await state.clear()
    await message.answer(
        text=texts.parse_interrupted,
        reply_markup=menu_markup
    )


@router.message(MainAdminFilter(), content_types=types.ContentType.DOCUMENT, state=ParserStates.parsing)
async def get_cookies_handler(message: types.Message, state: FSMContext):
    destination = r"./file.txt"
    await bot.download(
        message.document,
        destination=destination
    )
    with open(destination) as f:
        text = f.read()
    cookies = text.strip()
    try:
        cookies = json.loads(cookies)
    except JSONDecodeError:
        await message.answer('Неверный формат куки')
        return
    if (not isinstance(cookies, dict)) and (not isinstance(cookies, list)):
        print(type(cookies))
        await message.answer('Неверный формат куки')
        return
    with open(cookies_path, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=4)
    await Alert.delete().execute()
    await message.answer('Куки сохранены')
