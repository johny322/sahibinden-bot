from aiogram import Router

from .main import router as main_router
from .settings import router as settings_router
# from .parse import router as parse_router
from .help import router as help_router
from .admin import router as admin_router
from .sahibinden import router as sahibinden_router

router = Router()
router.include_router(main_router)
router.include_router(settings_router)

router.include_router(sahibinden_router)

# router.include_router(parse_router)
router.include_router(help_router)
router.include_router(admin_router)

