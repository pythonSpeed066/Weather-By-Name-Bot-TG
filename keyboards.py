from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# стартовая клавиатура
b1 = KeyboardButton("/настройки")
b2 = KeyboardButton("Погода у меня", request_location=True)
b3 = KeyboardButton("/вкл")
b4 = KeyboardButton("/выкл")
b5 = KeyboardButton("/запомни")
b6 = KeyboardButton("/забудь")

start_kb = ReplyKeyboardMarkup(resize_keyboard=True)
start_kb.row(b1, b2).row(b3, b4).row(b5, b6)

icons = ("🌡", "❄", "💨", "🧭", "💧", "🎈", "🌇", "🌄", "🕒", "☀")
inline_settings_kb = InlineKeyboardMarkup(row_width=5)
ok_buttons = [InlineKeyboardButton(text=icon + "✅", callback_data=f"1_{i+1}") for i, icon in enumerate(icons)]
cancel_buttons = [InlineKeyboardButton(text=icon + "❌", callback_data=f"0_{i+1}") for i, icon in enumerate(icons)]

inline_settings_kb.row(*ok_buttons[:5])
inline_settings_kb.row(*ok_buttons[5:])

inline_settings_kb.row(*cancel_buttons[:5])
inline_settings_kb.row(*cancel_buttons[5:])