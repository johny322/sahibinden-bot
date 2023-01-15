import asyncio
import json
import traceback
from datetime import timedelta, datetime

from asyncstdlib import zip_longest
from loguru import logger

from config import scheduler
from data.constants import PARSER_LINKS, MAX_COUNT, MAX_POSTS_COUNT, START_PARSER_INTERVAL, START_DB_CLEAN_INTERVAL, \
    PARSER_SLEEP_INTERVAL_SECONDS
from log import decode_log_config
from models import Parser, ParserBanned, ParserFirstBanned, BlackWord, get_datetime_now, Post
from parsers import PARSERS_FUNCTIONS
from parsers.sahibinden import sahibinden_parser
from utils.exel_worker import create_excel
from utils.messages import send_excel, send_error_alert, send_post_messages


async def new_market_parser_tasks(parser):
    parser_name = parser.parser_name

    main_parser_func = PARSERS_FUNCTIONS[parser_name]['main']
    fetch_post = PARSERS_FUNCTIONS[parser_name]['fetch_post']
    user = parser.owner
    log = decode_log_config(user.log_config)
    currency = PARSER_LINKS[parser_name]['currency']
    stop = False
    start_page_number = parser.start_page_number
    if start_page_number > 2:
        start_page_number -= 2
    elif start_page_number > 1:
        start_page_number -= 1
    async for res, current_page_number in main_parser_func(parser.url, start_page_number):

        is_tops = [result.get('is_top') for result in res]
        if all(is_tops):
            continue
        if current_page_number != parser.start_page_number:
            logger.debug('update old start_page_number {} to current_page_number {}', parser.start_page_number, current_page_number)
            Parser.update(start_page_number=current_page_number).where(
                Parser.parser_name == parser_name,
                Parser.url == parser.url
            ).execute()
        for context in res:
            link = context.get('url')
            already_pars_link = ParserFirstBanned.get_or_none(
                owner=user,
                parser_name=parser_name,
                search_url=parser.url,
                post=link
            )
            if already_pars_link and context.get('is_top'):
                logger.debug('link {} is top, continue', link)
                continue
            if already_pars_link and not context.get('is_top'):
                stop = True
                logger.debug('no new posts in {}, last post {}', parser.url, already_pars_link.post)
                break
            logger.debug('new link: {}', link)
            try:
                post = await fetch_post(context)
                if post.seller_posts > MAX_POSTS_COUNT:
                    logger.debug('seller posts ({}) > {}', post.seller_posts, MAX_POSTS_COUNT)
                    if not already_pars_link:
                        ParserFirstBanned.create(
                            owner=user,
                            parser_name=parser_name,
                            search_url=parser.url,
                            post=link
                        )
                    continue
            except Exception as exception:
                logger.exception(exception)
                continue
            if not already_pars_link:
                ParserFirstBanned.create(
                    owner=user,
                    parser_name=parser_name,
                    search_url=parser.url,
                    post=link
                )
            if user.black_words:
                black_words = BlackWord.select().where(BlackWord.owner == user)
                black_words = [black_word.name for black_word in black_words]
                if black_words:
                    if any(black_w in post.title.split(' ') for black_w in black_words):
                        logger.debug('black words in title: {}', post.title)
                        continue
            try:
                ParserBanned.get(
                    owner=user,
                    parser_name=parser_name,
                    seller=post.seller_url
                )
                logger.debug('post in black list: {}', post.seller_url)
                continue

            except ParserBanned.DoesNotExist:
                ParserBanned.create(
                    owner=user,
                    parser_name=parser_name,
                    seller=post.seller_url
                )
            # print(post)
            Post.create(
                owner=user,
                parser_name=parser_name,
                post_json=json.loads(post.json()),
            )

        if stop:
            break


async def new_market_parsing():
    parsers = Parser.select()
    for parser in parsers.group_by(Parser.owner):
        user = parser.owner
        log = decode_log_config(user.log_config)
        parser_name = parser.parser_name
        user_results = Post.select().where(Post.owner == user, Post.parser_name == parser_name)
        logger.debug('User {} has posts count: {}', user.username, user_results.count())
        if user_results.count() > MAX_COUNT:
            currency = PARSER_LINKS[parser_name]['currency']
            extra = {
                'currency': currency,
            }
            posts = [user_result.post_json for user_result in user_results]
            excel = create_excel(posts, log, extra)
            await send_excel(user.user_id, excel, parser_name)

            Post.delete().where(Post.owner == user, Post.parser_name == parser_name).execute()
        await asyncio.sleep(0.1)

    logger.debug('Urls count: {}', len(parsers))
    tasks = []
    for parser in parsers:
        task = asyncio.create_task(new_market_parser_tasks(parser))
        tasks.append(task)

    await asyncio.gather(*tasks)


async def set_first_banned(parser_name, url, user):
    main_parser_func = PARSERS_FUNCTIONS[parser_name]['main']
    async for first_results, current_page_number in main_parser_func(url):
        is_tops = [result.get('is_top') for result in first_results]
        if all(is_tops):
            logger.debug('all posts are top in {}, page: {}', url, current_page_number)
            continue
        first_links = [result.get('url') for result in first_results]
        # print(f'{first_results=}')
        insert_data = [
            dict(
                owner=user,
                parser_name=parser_name,
                search_url=url,
                post=link,
            )
            for link in first_links[::-1][:-4]
        ]
        ParserFirstBanned.insert_many(insert_data).execute()
        return current_page_number


def clear_last_posts():
    now = get_datetime_now() - timedelta(days=1)
    count = ParserFirstBanned.delete().where(ParserFirstBanned.created < now).execute()
    logger.debug('cleaned {} last posts', count)


def append_scheduler_job():
    scheduler.add_job(sahibinden_parser, 'date', run_date=datetime.now())
    scheduler.add_job(send_post_messages, 'interval', seconds=PARSER_SLEEP_INTERVAL_SECONDS)
    scheduler.add_job(send_error_alert, 'interval', seconds=PARSER_SLEEP_INTERVAL_SECONDS)
    scheduler.add_job(clear_last_posts, 'interval', hours=START_DB_CLEAN_INTERVAL)
    logger.debug('added jobs')
