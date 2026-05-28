from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    """Главное меню с красивыми кнопками и эмодзи"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Контакты"),
                KeyboardButton(text="📁 Документы")
            ],
            [
                KeyboardButton(text="🛠 ИТ-поддержка"),
                KeyboardButton(text="📅 Совещания")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел..."
    )
    return keyboard