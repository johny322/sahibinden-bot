import asyncio

from aiogram.types import BufferedInputFile

from config import bot, config, dp
from data.texts import create_result_text, PostFromDict
from log import decode_log_config
from models import User, Post, Alert
from parsers.sahibinden import AlertMessage


async def send_excel(user_id, ex, parser_name):
    df = ex.get_df_bytes()
    f = BufferedInputFile(df, f'Результат {parser_name}.xlsx')
    await bot.send_document(user_id, f)


async def send_new_post_message(user_id, post):
    await bot.send_message(
        user_id,
        text=f'Новое объявление: {post.link}\n'
             f'Число объявлений продавца: {post.seller_posts}'
    )


async def send_good_post_message(user_id, post):
    await bot.send_message(
        user_id,
        text=f'Новое <b>подходящее</b> объявление: {post.link}\n'
             f'Число объявлений продавца: {post.seller_posts}'
    )


async def send_post_messages():
    users = User.select()
    for user in users:
        user_posts = Post.select().where(Post.owner == user)
        log = decode_log_config(user.log_config)
        for user_post in user_posts:
            post = PostFromDict(user_post.post_json)
            extra = dict(
                currency='TL'
            )
            text = create_result_text(post, log, extra)
            await bot.send_message(
                user.user_id,
                text=text
            )
            user_post.delete().execute()
            await asyncio.sleep(0.1)


async def send_error_alert():
    alert = Alert.select().first()
    if not alert:
        return
    error_text = alert.message

    user_id = config.admin_ids[0]
    if error_text == AlertMessage.need_cookies:
        await bot.send_message(
            user_id,
            text='Куки устарели. Отправьте файл с куки'
        )
    elif error_text == AlertMessage.email_code:
        await bot.send_message(
            user_id,
            text='Отправьте код с почты'
        )
    else:
        await bot.send_message(
            user_id,
            text='Неизвестная ошибка. Требуется перезапуск бота'
        )
