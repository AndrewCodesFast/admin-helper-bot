from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Контакты"), KeyboardButton(text="📄 Документы")],
            [KeyboardButton(text="🛠 ИТ-поддержка"), KeyboardButton(text="📅 Совещания")]
        ],
        resize_keyboard=True
    )
    return keyboard