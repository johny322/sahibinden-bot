import asyncio
from datetime import datetime

from parsers.parsing import append_scheduler_job
from routers import router
from config import config, bot, dp, scheduler
from utils.notify import notify_users
from utils.logger import setup_logger
from data.commands import base_commands
from middleware.throttling import ThrottlingMiddleware


async def sleep_time():
    print('start sleep')
    await asyncio.sleep(10)
    print('end sleep')


async def on_startup(dispatcher, bot):
    scheduler.start()
    # scheduler.add_job(sleep_time, 'date', run_date=datetime.now())
    append_scheduler_job()
    await bot.set_my_commands(commands=base_commands)
    await notify_users(bot, config.admin_ids)


if __name__ == "__main__":
    setup_logger()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.message.outer_middleware(
        ThrottlingMiddleware()
    )
    dp.run_polling(bot)
