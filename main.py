import asyncio
import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import keyboards as kb

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

# ─── Файловая система для логирования заявок (БЕЗ БД) ────────────────────────

LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def log_request(user_id: int, user_name: str, request_type: str, content: str):
    """Логирует заявку в JSON файл вместо БД"""
    log_file = os.path.join(LOGS_DIR, "requests.json")

    request_data = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "user_id": user_id,
        "user_name": user_name,
        "request_type": request_type,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }

    # Читаем существующие логи
    requests = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                requests = json.load(f)
        except:
            requests = []

    # Добавляем новую заявку
    requests.append(request_data)

    # Сохраняем
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)


# ─── Хранилище document file_id (вместо путей к файлам) ─────────────────────
# ВАЖНО: file_id получаются при загрузке документа в Telegram!
# Как получить file_id: см. инструкцию в RAILWAY_SETUP.md

DOCUMENTS = {
    "fz210": {
        "name": "Федеральный закон N 210-ФЗ",
        "file_id": os.getenv("FILE_ID_FZ_210", None),  # Получи это из Telegram!
        "description": "Федеральный закон от 27.07.2010 N 210-ФЗ"
    },
    "fz131": {
        "name": "Федеральный закон N 131-ФЗ",
        "file_id": os.getenv("FILE_ID_FZ_131", None),
        "description": "Федеральный закон от 06.10.2003 N 131-ФЗ"
    }
}


# Белый список Telegram ID ────────────────────────────────────────────────

def get_allowed_ids() -> set[int]:
    """Загружает белый список из переменной окружения."""
    raw = os.getenv("ALLOWED_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def is_allowed(user_id: int) -> bool:
    """Проверяет, входит ли пользователь в белый список."""
    return user_id in get_allowed_ids()


# ─── Middleware для проверки доступа ─────────────────────────────────────────

from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable


class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if not is_allowed(user_id):
            return
        return await handler(event, data)


dp.message.middleware(WhitelistMiddleware())


# ─── FSM для ИТ-поддержки ────────────────────────────────────────────────────

class SupportRequest(StatesGroup):
    waiting_for_problem = State()


# ─── Справочные данные ────────────────────────────────────────────────────────

# Контакты с кликабельными номерами
CONTACTS = {
    "it_department": {
        "name": "ИТ-отдел",
        "room": "111",
        "phone": "+79123456789"
    },
    "archive": {
        "name": "Архив",
        "room": "205",
        "phone": "+79198765432"
    },
    "economics": {
        "name": "Отдел экономики",
        "room": "310",
        "phone": "+79111111111"
    }
}

FAKE_DB = {
    "meetings": "📅 Ближайшее совещание: Понедельник, 09:00, Малый зал."
}


# ─── Обработчики ─────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветственное сообщение"""
    await message.answer(
        f"👋 Добрый день, {message.from_user.full_name}!\n\n"
        "🏢 Вы подключены к системе автоматизации\n"
        "Администрации г. Новочебоксарска\n\n"
        "Выберите нужный раздел:",
        reply_markup=kb.get_main_menu()
    )

@dp.message(F.text)
async def debug(message: types.Message):
    print(f"Получено: '{message.text}'")
    await message.answer(f"Вы написали: {message.text}")
# ─── КОНТАКТЫ с кликабельными номерами ──────────────────────────────────────

@dp.message(F.text == "📋 Контакты")
async def show_contacts(message: types.Message):
    """Показывает контакты с кликабельными номерами телефонов"""

    response = "📋 <b>Справочник отделов</b>\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for contact_key, contact in CONTACTS.items():
        response += f"<b>{contact['name']}</b>\n"
        response += f"   Кабинет: {contact['room']}\n"

    response += "\n<i>Нажмите на номер ниже, чтобы позвонить или отправить СМС:</i>\n\n"

    # Добавляем кнопки с номерами
    for contact_key, contact in CONTACTS.items():
        button = InlineKeyboardButton(
            text=f"☎️ {contact['name']}: {contact['phone']}",
            url=f"tel:{contact['phone']}"
        )
        keyboard.inline_keyboard.append([button])

    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")


# ─── ДОКУМЕНТЫ с отправкой файлов (через file_id) ───────────────────────────

@dp.message(F.text == "📁 Документы")
async def show_documents(message: types.Message):
    """Показывает доступные документы с возможностью скачивания"""

    response = "📁 <b>Доступные документы</b>\n\n"
    response += "Выберите документ для скачивания:\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Проверяем, какие документы доступны (имеют file_id)
    available_count = 0
    for doc_key, doc in DOCUMENTS.items():
        if doc.get("file_id"):  # Если есть file_id
            button = InlineKeyboardButton(
                text=f"📄 {doc['name']}",
                callback_data=f"download_{doc_key}"
            )
            keyboard.inline_keyboard.append([button])
            available_count += 1
        else:
            # Показываем недоступный документ
            response += f"⚠️ {doc['name']} — <i>еще не загружен</i>\n"

    if available_count == 0:
        response = (
            "❌ <b>На данный момент документов нет</b>\n\n"
            "Администратор еще не загрузил документы."
        )
        await message.answer(response, parse_mode="HTML")
        return

    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")


# ─── Callback для скачивания документов ──────────────────────────────────────

@dp.callback_query(F.data.startswith("download_"))
async def download_document(callback: types.CallbackQuery):
    """Отправляет выбранный документ (через file_id)"""
    doc_key = callback.data.replace("download_", "")

    if doc_key not in DOCUMENTS:
        await callback.answer("❌ Документ не найден", show_alert=True)
        return

    doc = DOCUMENTS[doc_key]

    # Проверяем, есть ли file_id
    if not doc.get("file_id"):
        await callback.answer(
            f"❌ Документ '{doc['name']}' еще не загружен администратором",
            show_alert=True
        )
        return

    try:
        # Отправляем уведомление о загрузке
        await bot.send_chat_action(callback.from_user.id, "upload_document")

        # Отправляем файл по file_id (работает везде, включая Railway!)
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=doc["file_id"],
            caption=f"📥 {doc['name']}\n\n{doc.get('description', '')}"
        )

        await callback.answer("✅ Документ отправлен!", show_alert=False)

    except Exception as e:
        print(f"Ошибка при отправке файла: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ─── ИТ-ПОДДЕРЖКА с логированием ────────────────────────────────────────────

@dp.message(F.text == "🛠 ИТ-поддержка")
async def it_support(message: types.Message, state: FSMContext):
    """Начинает процесс создания заявки в ИТ"""

    await message.answer(
        "🔧 <b>Заявка в ИТ-поддержку</b>\n\n"
        "Пожалуйста, <b>опишите вашу проблему</b>:\n\n"
        "<i>Будьте подробнее — это поможет быстрее решить проблему</i>",
        parse_mode="HTML"
    )

    await state.set_state(SupportRequest.waiting_for_problem)


@dp.message(SupportRequest.waiting_for_problem)
async def receive_problem_description(message: types.Message, state: FSMContext):
    """Получает описание проблемы и отправляет служебное сообщение"""

    problem_description = message.text

    # Логируем заявку
    log_request(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name,
        request_type="IT_SUPPORT",
        content=problem_description
    )

    # Генерируем ID заявки
    ticket_id = datetime.now().strftime("%Y%m%d%H%M%S")

    # Отправляем служебное сообщение
    confirmation_text = (
        "✅ <b>Ваша заявка успешно отправлена!</b>\n\n"
        f"🎫 <b>Номер заявки:</b> #{ticket_id}\n"
        "⏱ <b>Время ответа:</b> в течение 10 минут\n"
        "📧 <b>Ответ поступит в этот чат</b>\n\n"
        "🔔 <i>Следите за уведомлениями</i>"
    )

    await message.answer(confirmation_text, parse_mode="HTML")

    # Очищаем состояние
    await state.clear()


# ─── СОВЕЩАНИЯ ───────────────────────────────────────────────────────────────

@dp.message(F.text == "📅 Совещания")
async def meetings(message: types.Message):
    """Показывает информацию о совещаниях"""

    response = (
        "📅 <b>Расписание совещаний</b>\n\n"
        f"{FAKE_DB['meetings']}\n\n"
    )

    await message.answer(response, parse_mode="HTML")


# ─── КОМАНДА ДЛЯ АДМИНИСТРАТОРА: Загрузка документа ────────────────────────

@dp.message(Command("upload_doc"))
async def upload_doc_command(message: types.Message):
    """
    Команда для администратора: загрузить документ и получить file_id
    Использование: отправь /upload_doc ответом на документ
    """
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только администратор может использовать эту команду")
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer(
            "📝 <b>Инструкция по загрузке документа:</b>\n\n"
            "1. Ответь на мое сообщение командой /upload_doc\n"
            "2. Вложи документ в ответ\n"
            "3. Я получу file_id\n"
            "4. Добавь file_id в переменную окружения в Railway",
            parse_mode="HTML"
        )
        return

    doc = message.reply_to_message.document
    file_id = doc.file_id

    response = (
        f"✅ <b>Документ загружен успешно!</b>\n\n"
        f"📄 <b>Имя:</b> {doc.file_name}\n"
        f"📊 <b>Размер:</b> {doc.file_size / 1024 / 1024:.2f} МБ\n\n"
        f"🔑 <b>file_id:</b>\n<code>{file_id}</code>\n\n"
        f"✏️ <b>Добавь в .env на Railway."
    )

    await message.answer(response, parse_mode="HTML")


# ─── КОМАНДА ДЛЯ АДМИНИСТРАТОРА: Просмотр текущих file_id ────────────────────

@dp.message(Command("show_docs"))
async def show_docs_command(message: types.Message):
    """Показывает текущее состояние документов"""
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

    if message.from_user.id != ADMIN_ID:
        return

    response = "📚 <b>Текущие документы:</b>\n\n"

    for doc_key, doc in DOCUMENTS.items():
        if doc.get("file_id"):
            response += f"✅ <b>{doc['name']}</b>\n"
            response += f"   ID: {doc['file_id'][:20]}...\n\n"
        else:
            response += f"❌ <b>{doc['name']}</b> — не загружен\n"
            response += f"   Команда загрузки: /upload_doc\n\n"

    await message.answer(response, parse_mode="HTML")


# ─── Запуск ───────────────────────────────────────────────────────────────────

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("Переменная окружения BOT_TOKEN не задана")
    print("✅ Бот запущен на Railway!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())