from aiogram import Router, types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.fsm.context import FSMContext

from models import User
from log import decode_log_config, encode_log_config
from data import texts
from data.keyboards import menu_markup, parsers_markup, cancel_markup
from routers.filters import IsAdminFilter

router = Router()


@router.callback_query(text="delete")
async def delete_handler(query: types.CallbackQuery, state: FSMContext):
    await query.message.delete()
    await state.clear()


@router.message(IsAdminFilter(), commands={"start"})
async def welcome_handler(message: types.Message):
    payload = message.text.split()
    ref_id = None
    new_log = None
    try:
        if payload[1].split("_")[0] == "cfg":
            ref = None
            new_log = decode_log_config(payload[1])
        else:
            ref = User.get(user_id=int(payload[1]))
            ref_id = ref.user_id
    except (IndexError, ValueError, User.DoesNotExist):
        ref = None

    full_name = message.from_user.first_name
    if message.from_user.last_name:
        full_name += " " + message.from_user.last_name
    try:
        user = User.get(user_id=message.from_user.id)
        if new_log is not None:
            user.log_config = encode_log_config(new_log)
            user.save()
            await message.answer(
                text=texts.new_config_log
            )
    except User.DoesNotExist:
        log_config = "cfg_1_1_1_1_1_1_1_1_1_1"
        if new_log is not None:
            log_config = encode_log_config(new_log)
        User.create(
            user_id=message.from_user.id,
            full_name=full_name,
            username=message.from_user.username,
            referal_id=ref_id,
            log_config=log_config
        )
    await message.answer(
        text=texts.welcome.format(
            user_id=message.from_user.id,
            full_name=full_name
        ),
        reply_markup=menu_markup
    )


@router.message(Text(text_contains="отмена", text_ignore_case=True))
@router.message(commands={"cancel"}, state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    # await message.answer(text=texts.cancel)
    await state.clear()
    await welcome_handler(message)


@router.message(Text(text_contains="добавить ссылки", text_ignore_case=True))
async def start_parse(message: types.Message):
    await message.answer(
        text=texts.choose_parser,
        reply_markup=parsers_markup
    )


@router.callback_query(text="parse")
async def back_parse(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text(
        text=texts.choose_parser,
        reply_markup=parsers_markup
    )


@router.message(Text(text_contains="в главное меню", text_ignore_case=True))
async def go_main_menu(message: types.Message):
    await welcome_handler(message)


@router.message(Text(text_contains="начать парсинг", text_ignore_case=True))
async def start_parse(message: types.Message):
    await message.answer(
        text=texts.choose_parser,
        reply_markup=parsers_markup
    )


@router.message(Text(text_contains="завершить парсинг", text_ignore_case=True), state="*")
async def parsing_end_handler(message: types.Message, state: FSMContext):
    curr_state = await state.get_state()
    if curr_state:
        if curr_state.split(":")[1] == "cancel":
            await state.clear()
            return

    full_name = message.from_user.first_name
    if message.from_user.last_name:
        full_name += " " + message.from_user.last_name
    try:
        User.get(user_id=message.from_user.id)
    except User.DoesNotExist:
        User.create(
            user_id=message.from_user.id,
            full_name=full_name,
            username=message.from_user.username
        )
    await message.answer(
        text=texts.welcome.format(
            user_id=message.from_user.id,
            full_name=full_name
        ),
        reply_markup=menu_markup
    )
    await state.clear()
