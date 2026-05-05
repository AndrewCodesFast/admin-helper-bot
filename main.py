import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
import keyboards as kb

load_dotenv()
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

FAKE_DB = {
    "contacts": "📞 Архив: 205\n📞 Экономика: 310\n📞 ИТ-отдел: 111",
    "docs": "📑 Регламенты доступны на внутреннем портале: \n//admin-nchk/shared/docs",
    "meetings": "📅 Ближайшее совещание: Понедельник, 09:00, Малый зал."
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Добрый день, {message.from_user.full_name}!\n"
        "Вы подключены к системе автоматизации Администрации г. Новочебоксарска.",
        reply_markup=kb.get_main_menu()
    )

@dp.message(F.text == "🔍 Контакты")
async def show_contacts(message: types.Message):
    await message.answer(f"Справочник отделов:\n{FAKE_DB['contacts']}")

@dp.message(F.text == "📄 Документы")
async def show_docs(message: types.Message):
    await message.answer(FAKE_DB['docs'])

@dp.message(F.text == "🛠 ИТ-поддержка")
async def it_support(message: types.Message):
    await message.answer("🔧 Пожалуйста, опишите проблему. Заявка будет передана дежурному администратору.")

@dp.message(F.text == "📅 Совещания")
async def meetings(message: types.Message):
    await message.answer(FAKE_DB['meetings'])

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())