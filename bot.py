import ast
import logging
import asyncio
import json
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart
from config import TOKEN
import keyboard as kb
from states import *
import sqlite3
import functions as f
import admin, answers_handlers, instructions_handlers, menu_handlers, profile_handlers, subscriptions_handlers
import random
from captcha.image import ImageCaptcha
import os


# поллинг
async def main():
    # подключаем роутеры
    dp.include_router(admin.router)
    dp.include_router(answers_handlers.router)
    dp.include_router(instructions_handlers.router)
    dp.include_router(menu_handlers.router)
    dp.include_router(profile_handlers.router)
    dp.include_router(subscriptions_handlers.router)


    # запускаем поллинг
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup(dp))
    await bot.delete_webhook(drop_pending_updates=True)  # пропуск обновлений
    await dp.start_polling(bot)


async def on_startup(dp):
    asyncio.create_task(f.send_notifications(cur, con, bot))


# бот и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# подключение к базе данных
con = sqlite3.connect(r'bot_database.db')
cur = con.cursor()
f.create_database(cur)

# cur.execute("Delete From InstructionsVotes")
# con.commit()
# cur.execute("Delete From Instructions")
# con.commit()
# cur.execute("Delete From Answers")
# con.commit()
# cur.execute("Delete From Users")
# con.commit()
# cur.execute("Delete From Subscribes")
# con.commit()

# Создаем объект ImageCaptcha
captcha_generator = ImageCaptcha(width=200, height=100)
correct_captchas = {}


# обработка старта
@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    # проверка на наличие пользователя в базе
    cur.execute(f"SELECT EXISTS (SELECT user_id FROM Users WHERE user_id = {message.from_user.id})")
    in_base_res = cur.fetchone()[0]

    if in_base_res == 0:
        # Генерируем капчу
        image_data, captcha_code = f.generate_captcha()
        correct_captchas[message.from_user.id] = captcha_code
        # Сохраняем изображение капчи
        captcha_file = f'images/{captcha_code}.png'
        with open(captcha_file, 'wb') as ff:
            ff.write(image_data.read())
        # Отправляем изображение капчи пользователю
        with open(captcha_file, 'rb'):
            file_to_send = types.FSInputFile(captcha_file)
            await message.answer_photo(file_to_send, caption="🔐 Введите капчу:")
            await state.set_state(EnterCapthca.entering_captcha)
        # Удаляем временный файл
        os.remove(captcha_file)

        @dp.message(EnterCapthca.entering_captcha)
        async def check_captcha(message: types.Message, state: FSMContext):
            # Получаем введенную пользователем капчу
            user_input = message.text.strip()
            # Получаем правильный ответ на капчу для данного пользователя
            correct_captcha = correct_captchas.get(message.from_user.id)
            # Проверяем правильность капчи
            if user_input == correct_captcha:
                await message.answer("✅ Капча введена правильно!")
                # Очищаем правильный ответ на капчу после успешной проверки
                del correct_captchas[message.from_user.id]
                putin_gif = types.FSInputFile('images/putin.gif')
                await bot.send_video(message.from_user.id, putin_gif)
                await state.clear()
                await message.reply(f"Привет, {message.from_user.first_name} 🙋‍♂️! Я твой новый <i>чат-бот</i>. "
                                    "Меня создали, чтобы помочь в изучении новых инструкций и советов "
                                    "по организации процессов на производстве "
                                    "с комфортом. Давай начнем!😉", parse_mode='HTML',
                                    reply_markup=kb.kb_keyboard)

                f.add_user(message.from_user.id, 0, 0, 1, cur, con)
                await bot.send_message(message.from_user.id, f"🗃 Меню:", reply_markup=kb.menu_keyboard)
            else:
                await message.reply("❌ Попробуйте снова.")
                print(correct_captchas)
    elif in_base_res == 1:
        await bot.send_message(message.from_user.id, f"🗃 Меню:", reply_markup=kb.menu_keyboard)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  # логирование
    asyncio.run(main())
