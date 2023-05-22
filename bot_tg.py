from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor

from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text

import exceptions
import weather
import os
import logging
import keyboards

logging.basicConfig(level=logging.INFO)
bot_token = os.getenv("bot_token")
bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


async def on_startup(_):
    weather.create_db()
    print("\nБот запущен.\n\n", "=" * 11, "\n")


@dp.message_handler(commands=["start", "help"])
async def start_command(message: types.Message):
    await message.answer("""
👁⛅Покажу вам прогноз погоды по названию города! Введите название города на русском или английском языке. 
Например, Калининград или kaliningrad. Также я понимаю координаты и знаю погоду там, где вы находитесь
Команды:

/start или /help - помощь (это сообщение)
                                
/настройки - мои параметры (✅включить и ❌выключить)

/вкл и /выкл параметры с помощью ввода цифр 7️⃣

/запомни координаты 📌
                         
/забудь координаты 🗑

/рекомендации - рекомендации по одежде в зависимости от погоды""", reply=False,
                         reply_markup=keyboards.start_kb)

    weather.add_user_to_db(message.from_user.id)


@dp.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    rtw = weather.RealtimeWeather(message.from_user.id)
    answer = rtw.get_weather(lat=lat, lon=lon)
    await message.answer(answer)


@dp.message_handler(commands=["настройки"])
async def show_weather_settings_command(message: types.Message):
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    await message.answer(rtw.display_settings(), reply=False, reply_markup=keyboards.inline_settings_kb)


class FSMAddSettings(StatesGroup):
    settings = State()


class FSMDelSettings(StatesGroup):
    settings = State()


@dp.message_handler(commands=["вкл"], state=None)
async def start_adding_settings(message: types.Message):
    await FSMAddSettings.settings.set()
    await message.reply("Что добавить? Номера через пробел: 1 2 3")


@dp.message_handler(state=FSMAddSettings.settings)
async def handle_settings_to_add(message: types.Message, state: FSMContext):
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    try:
        rtw.add_settings(message.text)
    except exceptions.InvalidParametersList as e:
        await message.answer(str(e))
    except:
        await message.answer("Неверный список!", reply=False, reply_markup=keyboards.start_kb)
    else:
        await message.answer(rtw.display_settings(), reply=False, reply_markup=keyboards.start_kb)
    await state.finish()


@dp.message_handler(commands=["выкл"], state=None)
async def start_deleting_command(message: types.Message):
    await FSMDelSettings.settings.set()
    await message.reply("Что убрать? Номера через пробел: 1 2 3")


@dp.message_handler(state=FSMDelSettings.settings)
async def handle_settings_to_delete(message: types.Message, state: FSMContext):
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    try:
        rtw.del_settings(message.text)
    except exceptions.InvalidParametersList as e:
        await message.answer(str(e))
    except:
        await message.answer("Неверный список!")
    else:
        await message.answer(rtw.display_settings(), reply=False)
    await state.finish()


class FSMLink(StatesGroup):
    label = State()
    coord = State()


class FSMUnlink(StatesGroup):
    label = State()


@dp.message_handler(commands=["запомни"], state=None)
async def link_coord_start(message: types.Message):
    await FSMLink.label.set()
    await message.answer("Я запомню координаты под именем...")


@dp.message_handler(state=FSMLink.label)
async def link_coord_get_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["label"] = message.text
    await FSMLink.next()
    await message.reply("Введи координаты")


@dp.message_handler(state=FSMLink.coord)
async def link_coord(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["coord"] = message.text
    async with state.proxy() as data:
        label = data["label"]
        raw_coord = data["coord"]
    await state.finish()
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    coord = rtw.coord(raw_coord)
    if not coord:
        await message.answer("❌Неверные координаты!")
    else:
        ans = rtw.link_coord(label, *coord)
        if ans:
            await message.answer(ans)
        else:
            await message.answer(f"Запомнил! {label} - это {coord[0]} {coord[1]}")


@dp.message_handler(commands=["забудь"])
async def unlink_coord_start(message: types.Message):
    await FSMUnlink.label.set()
    await message.answer("Название, которое хотите удалить...")


@dp.message_handler(state=FSMUnlink.label)
async def unlink_coord(message: types.Message, state: FSMContext):
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    rtw.unlink_coord(message.text)
    await state.finish()
    await message.answer("Удалил!", reply=False, reply_markup=keyboards.start_kb)


@dp.callback_query_handler(Text(startswith="0_"))
async def setting_off(callback: types.CallbackQuery):
    rtw = weather.RealtimeWeather(userid=callback.from_user.id)
    rtw.del_settings(callback.data.split("_")[1])
    await callback.message.answer(rtw.display_settings(), reply=False, reply_markup=keyboards.inline_settings_kb)
    await callback.answer()


@dp.callback_query_handler(Text(startswith="1_"))
async def setting_on(callback: types.CallbackQuery):
    rtw = weather.RealtimeWeather(userid=callback.from_user.id)
    rtw.add_settings(callback.data.split("_")[1])
    await callback.message.answer(rtw.display_settings(), reply=False, reply_markup=keyboards.inline_settings_kb)
    await callback.answer()


@dp.message_handler()
async def send_weather_command(message: types.Message):
    rtw = weather.RealtimeWeather(userid=message.from_user.id)
    try:
        coord = rtw.coord(message.text)
    except exceptions.InvalidCoord as e:
        await message.answer(str(e))
    else:
        answer = rtw.get_weather(lat=coord[0], lon=coord[1]) if coord else rtw.get_weather(city=message.text)
        await message.answer(answer, reply_markup=keyboards.start_kb)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
