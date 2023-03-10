import asyncio

from config import config, bot, dp, scheduler
from data.commands import base_commands
from middleware.throttling import ThrottlingMiddleware
from parsers.parsing import append_scheduler_job
from routers import router
from utils.logger import setup_logger
from utils.notify import notify_users


async def sleep_time():
    print('start sleep')
    await asyncio.sleep(10)
    print('end sleep')


async def on_startup(dispatcher, bot):
    # scheduler.start()
    # append_scheduler_job()
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
