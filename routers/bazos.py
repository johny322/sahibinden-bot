import re
import traceback
import urllib
from asyncio import sleep

from aiogram import Router, types
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile
from aiohttp import ClientConnectorError, ClientHttpProxyError, ClientProxyConnectionError
from asyncstdlib import zip_longest
from loguru import logger

from data.constants import MAX_COUNT
from models import BlackWord, BazosText, User, get_datetime_now, \
    BazosPreset, BazosBanned
from dateutil.parser import parse
from config import config
from data import texts
from data.states import Bazos, BazosTextG
from data.keyboards import (
    get_presets_markup, get_post_date_markup,
    start_parse_markup, cancel_markup, get_back_parsing_markup,
    menu_markup, cancel_parse_markup, save_preset_markup,
    texts_markup, back_texts_markup, count_markup,
    get_price_markup, no_count_markup, bazos_keyboard, parse_skip_tops_markup
)
from log import decode_log_config
from parsers.bazos import bazos_parse
from utils.exel_worker import Excel

countries = {
    'sk': {
        'link': 'https://mobil.bazos.sk/',
        'currency': 'EUR',
    },
    'pl': {
        'link': 'https://telefon.bazos.pl/',
        'currency': 'PLN'
    },
    'at': {
        'link': 'https://handy.bazos.at/',
        'currency': 'EUR'
    },
    'cz': {
        'link': 'https://mobil.bazos.cz/',
        'currency': 'CZK '
    },
}

router = Router()


@router.callback_query(text="bazos_show")
async def show_all_carousells(query: types.CallbackQuery):
    await query.message.edit_text(
        text=texts.choice_parser_country,
        reply_markup=bazos_keyboard
    )


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_start")
async def bazos_start(query: types.CallbackQuery):
    country = query.data.split(":")[1]
    user = User.get(user_id=query.from_user.id)
    await query.message.edit_text(
        text=texts.parse_start_sub,
        reply_markup=start_parse_markup("bazos", country)
    )


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos")
async def bazos(query: types.CallbackQuery, state: FSMContext):
    country = query.data.split(":")[1]
    await state.update_data(country=country)
    user = User.get(user_id=query.from_user.id)
    await query.message.edit_text(
        text=texts.parse_token_bazos,
        reply_markup=get_back_parsing_markup("bazos", country)
    )
    await state.set_state(Bazos.token)


@router.message(Bazos.token)
async def get_bazos_token_handler(message: types.Message, state: FSMContext):
    await state.update_data(token=message.text.split('\n'))
    await message.answer(
        text=texts.parse_proxy,
        reply_markup=cancel_markup
    )
    await state.set_state(Bazos.proxy)
    return


@router.message(Bazos.proxy)
async def bazos_proxy(message: types.Message, state: FSMContext):
    match = re.match(r'.+:.+@[0-9a-zA-Z\.]+:\d+', message.text)
    if (not match) or ('http' in match.group(0)):
        await message.answer(
            text=texts.bad_parse_proxy,
            reply_markup=cancel_markup
        )
        return
    proxy = f'http://{match.group(0)}'
    data = await state.get_data()
    country = data['country']
    await state.update_data(proxy=proxy)

    await message.answer(
        text=texts.parse_many_urls.format(
            parser_link=countries[country]['link']
        ),
        disable_web_page_preview=True,
        reply_markup=cancel_markup
    )
    await state.set_state(Bazos.url)


@router.message(Bazos.url)
async def bazos_url(message: types.Message, state: FSMContext):
    links = message.text.split('\n')
    queries = []
    data = await state.get_data()
    country = data['country']
    for link in links:
        link = link.strip()
        if not link:
            continue
        match = re.match(r"(https://){0,1}(.+\.bazos\." + country + r"/{0,1}.*)", link)
        if match:
            query = match.group(2)
        else:
            query = f'www.bazos.{country}/search.php?hledat={link.replace(" ", "+")}&rubriky=www&hlokalita=&humkreis=1000&cenaod=&cenado=&Submit=Hledat&kitx=ano'
        logger.debug("query - {}", query)
        queries.append(query)

    await message.answer(
        text=texts.parse_count,
        reply_markup=count_markup
    )
    await state.update_data(query=queries)
    await state.set_state(Bazos.count)


@router.message(Bazos.preset_count, lambda msg: not msg.text.isdigit())
@router.message(Bazos.count, lambda msg: not msg.text.isdigit())
async def bazos_count_inv(message: types.Message):
    await message.answer(
        text=texts.parse_count_invalid,
        reply_markup=count_markup
    )


@router.message(Bazos.count)
async def bazos_count(message: types.Message, state: FSMContext):
    count = int(message.text)
    if count > MAX_COUNT:
        await message.answer(
            text=texts.parse_count_too_much.format(
                max_count=MAX_COUNT
            ),
            reply_markup=cancel_markup
        )
        return
    await state.update_data(count=count)
    data = await state.get_data()
    country = data['country']
    currency = countries[country]['currency']
    await message.answer(
        text=texts.parse_price.format(coin=currency),
        reply_markup=get_price_markup()
    )
    await state.set_state(Bazos.price)


@router.message(Bazos.price)
async def bazos_price(message: types.Message, state: FSMContext):
    payload = message.text.split("-")
    try:
        price_s = int(payload[0])
        price_e = int(payload[1])
        await state.update_data(price_s=price_s, price_e=price_e)

        await message.answer(
            text=texts.parse_post_views,
            reply_markup=no_count_markup
        )
        await state.set_state(Bazos.post_views)

    except (IndexError, ValueError):
        await message.answer(
            text=texts.parse_price_invalid,
            reply_markup=get_price_markup()
        )


@router.message(Bazos.post_views)
async def bazos_max_post_views(message: types.Message, state: FSMContext):
    if not message.text.isdigit() and message.text != "no":
        await message.answer(text=texts.parse_post_views_invalid)
        return

    if message.text == "no":
        max_views = None
    else:
        max_views = int(message.text)
    await state.update_data(max_views=max_views)

    await message.answer(
        text=texts.parse_seller_posts,
        reply_markup=no_count_markup
    )
    await state.set_state(Bazos.seller_posts)


@router.message(Bazos.seller_posts)
async def bazos_seller_posts(message: types.Message, state: FSMContext):
    if not message.text.isdigit() and message.text != "no":
        await message.answer(text=texts.parse_seller_posts_invalid)
        return

    if message.text == "no":
        max_posts = None
    else:
        max_posts = int(message.text)
    await state.update_data(max_posts=max_posts)

    await message.answer(
        text=texts.parse_skip_tops,
        reply_markup=parse_skip_tops_markup
    )
    await state.set_state(Bazos.skip_tops)


@router.message(Bazos.skip_tops)
async def bazos_skip_tops(message: types.Message, state: FSMContext):
    if message.text == "no":
        skip_tops = False
    elif message.text == "yes":
        skip_tops = True
    else:
        await message.answer(
            text=texts.parse_skip_tops_invalid
        )
        return
    await state.update_data(skip_tops=skip_tops)

    await message.answer(
        text=texts.parse_post_date,
        reply_markup=get_post_date_markup()
    )
    await state.set_state(Bazos.post_date)


@router.message(Bazos.post_date)
async def bazos_post_date(message: types.Message, state: FSMContext):
    if message.text == "no":
        await state.update_data(post_date=None)
        await message.answer(
            text=texts.parse_save_preset,
            reply_markup=save_preset_markup
        )
        await state.set_state(Bazos.save)
        return
    try:
        post_date = parse(message.text)
    except ValueError:
        await message.answer(
            text=texts.parse_date_invalid,
            reply_markup=cancel_markup
        )
        return

    if post_date.year > 2000 and post_date < get_datetime_now():
        await state.update_data(post_date=message.text)
        await message.answer(
            text=texts.parse_save_preset,
            reply_markup=save_preset_markup
        )
        await state.set_state(Bazos.save)
    else:
        await message.answer(
            text=texts.parse_date_invalid,
            reply_markup=get_post_date_markup()
        )


@router.message(Bazos.save, text="yes")
async def bazos_save_preset(message: types.Message, state: FSMContext):
    await message.answer(
        text=texts.preset_save_name,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Bazos.preset)


@router.message(Bazos.save, text="no")
@router.message(Bazos.preset)
@router.message(Bazos.preset_count)
async def bazos_run_parsing(message: types.Message, state: FSMContext):
    curr_state = await state.get_state()

    # ex = Excel()
    # main_key = 'Ссылка на товар'
    # data = {
    #     main_key: []
    # }
    # ex.set_main_key(main_key)
    # ex.set_data(data)

    user = User.get(user_id=message.from_user.id)
    log = decode_log_config(user.log_config)
    data = await state.get_data()
    country = data['country']
    if curr_state == "Bazos:preset_count":
        prev_preset = data.get('preset')
        if prev_preset:
            preset = prev_preset
        else:
            preset = BazosPreset.get(owner=user, id=data['preset_id'], country=country)
        queries = preset.query.split('\n')
        post_date = preset.post_date
        count = int(message.text)
        if count > MAX_COUNT:
            await message.answer(
                text=texts.parse_count_too_much.format(
                    max_count=MAX_COUNT
                ),
                reply_markup=cancel_markup
            )
            return
        price_s = preset.price_s
        price_e = preset.price_e
        max_posts = preset.max_posts
        max_views = preset.max_views
        skip_tops = preset.skip_tops
        proxy = data["proxy"]
    else:
        queries = data["query"]
        post_date = None
        if data["post_date"]:
            post_date = parse(data["post_date"])
        count = data["count"]
        price_s = data["price_s"]
        price_e = data["price_e"]
        max_posts = data["max_posts"]
        max_views = data["max_views"]
        proxy = data["proxy"]
        skip_tops = data['skip_tops']
    token = data['token']

    if curr_state == "Bazos:preset":
        try:
            BazosPreset.get(owner=user, name=message.text)
            await message.answer(text=texts.preset_alredy_exists)
        except BazosPreset.DoesNotExist:
            BazosPreset.create(
                owner=user,
                country=country,
                name=message.text,
                query='\n'.join(queries),
                post_date=post_date,
                price_s=price_s,
                price_e=price_e,
                max_posts=max_posts,
                max_views=max_views,
                skip_tops=skip_tops,
            )
            await message.answer(text=texts.preset_saved)

    await state.set_state(Bazos.cancel)
    await message.answer(
        text=texts.parse_starts,
        reply_markup=cancel_parse_markup
    )
    posts_counted = 0
    posts_getted = 0

    skip_post_date = 0
    skip_only_phone = 0
    skip_ban_word = 0
    skip_check_wa = 0
    skip_post_price = 0
    skip_max_posts = 0
    skip_max_views = 0
    skip_ban_post = 0
    domain = 'https://'
    urls = [domain + query for query in queries]
    funcs = [bazos_parse(url, proxy, skip_tops, token) for url in urls]
    try:
        async for parser_results in zip_longest(*funcs):
            if not parser_results:
                continue
            for post, get_posts, start_url in parser_results:
                if get_posts:
                    await message.answer(
                        text=texts.parser_many_get_posts.format(
                            count_posts=get_posts,
                            url=start_url
                        ),
                        disable_web_page_preview=True
                    )
                    posts_getted += get_posts
                curr_state = await state.get_state()
                if not "Bazos:cancel" == curr_state:
                    # df = ex.get_df_bytes()
                    # f = BufferedInputFile(df, 'Результат.xlsx')
                    # await message.answer_document(f)
                    await message.answer(
                        text=texts.parse_interrupted,
                        reply_markup=menu_markup
                    )
                    return
                await sleep(0.1)
                # print(post)
                if not post.price:
                    skip_post_price += 1
                    continue
                if post.price > price_e or post.price < price_s:
                    skip_post_price += 1
                    continue
                if post_date:
                    if post_date > post.created.replace(tzinfo=None):
                        skip_post_date += 1
                        continue
                if max_posts is not None:
                    if max_posts < post.seller_posts:
                        skip_max_posts += 1
                        continue
                if max_views is not None:
                    if max_views < post.views:
                        skip_max_views += 1
                        continue

                if log.only_with_phone and not post.phone:
                    skip_only_phone += 1
                    continue
                word_ban = False
                for word in post.title.split():
                    try:
                        BlackWord.get(
                            owner=user,
                            name=word
                        )
                        word_ban = True
                        break
                    except BlackWord.DoesNotExist:
                        pass
                if word_ban:
                    skip_ban_word += 1
                    continue

                text = "📦 Товар"
                if log.title:
                    text += f": <code>{post.title}</code>\n"
                if log.description:
                    text += f"😇 Описание: <i>{post.description}</i>\n"
                currency = countries[country]['currency']
                if log.price:
                    text += f"💰 Цена: <b>{post.price} {currency}</b>\n"
                text += "\n"  # maybe delete
                if post.phone:
                    text += f"📞 Контакт(-ы): <code>{post.phone}</code>\n"
                    text += texts.gowhatsup.format(phone=post.phone) + "\n"
                    text += texts.goviber.format(phone=post.phone)
                    text += texts.gotelegram.format(phone=post.phone) + "\n"
                    # @link
                    # @price
                    # @itemname
                    wa_texts = []
                    for modl in BazosText.select().where(BazosText.owner == user):
                        mtext = modl.text.replace("@link", "{link}"
                                                  ).replace("@price", "{price}"
                                                            ).replace("@itemname", "{itemname}").format(
                            price=post.price,
                            itemname=post.title,
                            link=post.link,
                        )
                        wa_texts.append((
                            f"<a href='https://web.whatsapp.com/send?phone={post.phone}&text={urllib.parse.quote(mtext)}'>{modl.name}</a>",
                            f"<a href='https://api.whatsapp.com/send?phone={post.phone}&text={urllib.parse.quote(mtext)}'>{modl.name}</a>",
                        ))
                    if wa_texts:
                        wa_web_text = " ".join(list(map(lambda t: t[0], wa_texts)))
                        wa_mob_text = " ".join(list(map(lambda t: t[1], wa_texts)))
                        text += f"📱 WhatsApp (Ваш текст): {wa_mob_text}\n" + \
                                f"🖥 WEB WhatsApp (Ваш текст): {wa_web_text}\n\n"
                if log.created:
                    text += f"🗓 Дата создания объявления: <b>{post.created.strftime('%Y-%m-%d')}</b>\n"

                text += f"🔗 Ссылка на товар: <a href='{post.link}'>Нажми</a>\n"

                text += f"🔗 Ссылка на фото: <a href='{post.photo_url}'>Нажми</a>\n"
                if log.seller_name:
                    text += f"👨 Имя продавца: <b>{post.seller_name}</b>\n"
                text += f"🔗 Ссылка на продавца: <a href='{post.seller_url}'>Нажми</a>\n"
                if log.posts_count:
                    text += f"🔢 Объявлений продавца: {post.seller_posts}\n"
                if log.views:
                    text += f"👁 Просмотров: {post.views}\n"

                try:
                    if user.other_banned:
                        BazosBanned.get(seller_url=post.seller_url)
                    else:
                        BazosBanned.get(owner=user, seller_url=post.seller_url)
                    logger.debug("post in black list")
                    skip_ban_post += 1
                    continue
                except BazosBanned.DoesNotExist:
                    BazosBanned.create(owner=user, seller_url=post.seller_url)

                # ex.add_key_value('Товар', post.title)
                # ex.add_key_value('Описание', post.description)
                # ex.add_key_value('Цена', f'{post.price} {currency}')
                # ex.add_key_value('Дата создания объявления', post.created.strftime('%Y-%m-%d'))
                # ex.add_key_value('Ссылка на товар', post.link)
                # ex.add_key_value('Ссылка на фото', post.photo_url)
                # ex.add_key_value('Имя продавца', post.seller_name)
                # ex.add_key_value('Ссылка на продавца', post.seller_url)
                # ex.add_key_value('Обьявлений продавца', post.seller_posts)
                # ex.add_key_value('Просмотров', post.views)
                # if post.phone:
                #     ex.add_key_value('Контакт', post.phone)

                posts_counted += 1
                logger.debug(f'{posts_counted=}')
                text += f"\nℹ️ Осталось спарсить объявлений: <b>{count - posts_counted}/{count}</b>"
                if log.photo:
                    try:
                        await message.answer_photo(
                            photo=post.photo_url,
                            caption=text
                        )
                    except TelegramBadRequest as e:
                        if 'MEDIA_CAPTION_TOO_LONG' in str(e):
                            await message.answer_photo(
                                photo=post.photo_url
                            )
                            await message.answer(text=text, disable_web_page_preview=True)
                        else:
                            logger.error(e)
                else:
                    await message.answer(text=text, disable_web_page_preview=True)
                if posts_counted >= count:
                    break
            if posts_counted >= count:
                break
    except (ClientConnectorError, ClientHttpProxyError, ClientProxyConnectionError):
        await message.answer(
            text=texts.bad_connect_parse_proxy,
            reply_markup=menu_markup
        )
        await state.clear()
        return
    all_skip = skip_post_date + skip_only_phone + skip_ban_word + skip_post_price + skip_ban_post + skip_max_views + \
               skip_max_posts
    anythink_skip = posts_getted - all_skip - count
    await message.answer(
        text=texts.parse_ends + texts.bazos_ends.format(
            price=skip_post_price,
            post_date=skip_post_date,
            max_posts=skip_max_posts,
            max_views=skip_max_views,
            ban_word=skip_ban_word,
            anythink=anythink_skip,
            ban_post=skip_ban_post,
            all_count=posts_getted - count
        ),
        reply_markup=menu_markup
    )

    # df = ex.get_df_bytes()
    # f = BufferedInputFile(df, 'Результат.xlsx')
    # await message.answer_document(f)


@router.message(Bazos.save)
async def bazos_preset_save_invalid(message: types.Message):
    await message.answer(
        text=texts.parse_save_preset,
        reply_markup=save_preset_markup
    )


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_preset")
async def bazos_preset(query: types.CallbackQuery):
    user = User.get(user_id=query.from_user.id)
    country = query.data.split(":")[1]
    pr_query = BazosPreset.select().where(BazosPreset.owner == user, BazosPreset.country == country)
    presets = {}
    for p in pr_query:
        if p.name != f'{user.user_id}_previous_state':
            presets[p.name] = p.id

    if not presets:
        await query.answer(text="У вас нет пресетов", show_alert=True)
        return

    await query.message.edit_text(
        text=texts.presets,
        reply_markup=get_presets_markup("bazos", presets, country)
    )


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_run_preset")
async def bazos_run_preset(query: types.CallbackQuery, state: FSMContext):
    payload = query.data.split(":")
    country = payload[2]
    preset = BazosPreset.get(id=query.data.split(":")[1], country=country)
    await state.update_data(preset_id=preset.id, country=country)

    await state.set_state(Bazos.preset_token)
    await query.message.edit_text(
        text=texts.parse_token_bazos
    )


@router.message(Bazos.preset_token)
async def bazos_preset_token(message: types.Message, state: FSMContext):
    await state.update_data(token=message.text)
    await state.set_state(Bazos.preset_proxy)
    await message.answer(
        text=texts.parse_proxy,
        reply_markup=cancel_markup
    )


@router.message(Bazos.preset_proxy)
async def bazos_preset_count(message: types.Message, state: FSMContext):
    data = await state.get_data()
    country = data['country']
    currency = countries[country]['currency']
    preset_id = data['preset_id']
    preset = BazosPreset.get(id=preset_id, country=country)

    match = re.match(r'.+:.+@[0-9a-zA-Z\.]+:\d+', message.text)
    if (not match) or ('http' in match.group(0)):
        await message.answer(
            text=texts.bad_parse_proxy,
            reply_markup=cancel_markup
        )
        return
    proxy = f'http://{match.group(0)}'
    await state.update_data(proxy=proxy)
    await state.set_state(Bazos.preset_count)
    post_date = "Нет"
    if preset.post_date:
        post_date = preset.post_date.strftime("%d-%m-%Y")
    max_posts = "Нет"
    if preset.max_posts is not None:
        max_posts = preset.max_posts
    max_views = "Нет"
    if preset.max_views is not None:
        max_views = preset.max_views
    skip_tops = 'Да' if preset.skip_tops else 'Нет'
    await message.answer(
        text=texts.preset_settings.format(
            settings=texts.bazos_settings.format(
                name=preset.query,
                post_date=post_date,
                price=f"{preset.price_s}-{preset.price_e}",
                currency=currency,
                max_posts=max_posts,
                max_views=max_views,
                skip_tops=skip_tops
            )
        ),
    )


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_del_presets")
async def bazos_delete_all_presets(query: types.CallbackQuery):
    country = query.data.split(":")[1]
    user = User.get(user_id=query.from_user.id)
    BazosPreset.delete().where(BazosPreset.owner == user, BazosPreset.country == country).execute()
    await bazos_start(query)


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_texts_delete")
async def bazos_delete_all_text(query: types.CallbackQuery):
    country = query.data.split(":")[1]
    user = User.get(user_id=query.from_user.id)
    BazosText.delete().where(BazosText.owner == user, BazosText.country == country).execute()
    await bazos_start(query)


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_texts")
async def bazos_custom_wa_text(query: types.CallbackQuery, state: FSMContext):
    country = query.data.split(":")[1]
    user = User.get(user_id=query.from_user.id)
    text_models = list(BazosText.select().where(BazosText.owner == user, BazosText.country == country))
    if text_models:
        await query.message.edit_text(
            text=texts.parser_texts,
            reply_markup=texts_markup("bazos", text_models, country)
        )
    else:
        await query.message.edit_text(text=texts.new_text_without_seller)
        await state.update_data(country=country)
        await state.set_state(BazosTextG.text)


@router.callback_query(text="bazos_create_text")
async def bazos_create_text(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_text(text=texts.new_text)
    await state.set_state(BazosTextG.text)


@router.callback_query(lambda cb: cb.data.split(":")[0] == "bazos_text")
async def bazos_text_info(query: types.CallbackQuery):
    payload = query.data.split(":")
    text_id = int(payload[1])
    country = payload[2]
    text = BazosText.get(id=text_id, country=country)
    await query.message.edit_text(
        text=texts.parser_text_info.format(
            name=text.name,
            text=text.text
        ),
        reply_markup=back_texts_markup("bazos", country)
    )


@router.message(BazosTextG.text)
async def bazos_new_text(message: types.Message, state: FSMContext):
    await message.answer(
        text=texts.new_text_name
    )
    await state.update_data(text=message.text)
    await state.set_state(BazosTextG.name)


@router.message(BazosTextG.name)
async def bazos_new_text_name(message: types.Message, state: FSMContext):
    user = User.get(user_id=message.from_user.id)
    data = await state.get_data()
    country = data["country"]
    try:
        BazosText.get(owner=user, country=country, name=message.text)
        await message.answer(
            text=texts.new_text_name_exists
        )
    except BazosText.DoesNotExist:
        data = await state.get_data()
        BazosText.create(
            owner=user,
            country=country,
            name=message.text,
            text=data["text"]
        )
    finally:
        text_models = list(BazosText.select().where(BazosText.owner == user, BazosText.country == country))
        await message.answer(
            text=texts.parser_texts,
            reply_markup=texts_markup("bazos", text_models, country)
        )
