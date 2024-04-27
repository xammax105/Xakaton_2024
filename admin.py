from aiogram import Bot, Router, types, F
import keyboard as kb
from states import *
import sqlite3
import os
import logging
from config import TOKEN, admin_num
import functions as f

# подключение к базе данных
con = sqlite3.connect(r'bot_database.db')
cur = con.cursor()

# роутер
router = Router()
bot = Bot(token=TOKEN)


@router.message(F.text.lower() == 'выйти')
async def leave(message: types.Message):
    await bot.send_message(message.from_user.id, "📄 Вы покинули этот раздел. Выберите, что вам подходит:",
                           reply_markup=kb.kb_keyboard)


@router.message(F.text.lower() == 'редактировать состав администрации бота')
async def administr(message: types.Message, state: FSMContext):
    men_kb = [

        [
            types.InlineKeyboardButton(text='➕ Добавить', callback_data='AddAdmin'),
            types.InlineKeyboardButton(text='➖ Удалить', callback_data='deleteAdmin'),
        ]
    ]

    keyboard_ans = types.InlineKeyboardMarkup(inline_keyboard=men_kb,
                                              resize_keyboard=True,
                                              input_field_placeholder="Изменения в составне администрации"
                                              )

    await bot.send_message(message.chat.id, f"Изменение состава администрации",
                           reply_markup=keyboard_ans)


@router.callback_query(F.data == 'AddAdmin')
async def confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id,
                           "✏ Введите Telegram ID пользователя для добавления в состав администрации")
    await state.set_state(RasStates.waiting_for_administr_new)


@router.message(RasStates.waiting_for_administr_new)
async def process_password(message: types.Message, state: FSMContext):
    text = message.text
    last_id = cur.execute('SELECT MAX (id) FROM Admins').fetchone()

    if last_id[0] is None:
        id = 1
    else:
        id = last_id[0] + 1
    if text.isdigit():
        user = await bot.get_chat(text)
        username = user.username
        cur.execute(f"INSERT INTO Admins (ID, user, password) VALUES ({id}, '{text}', '123')")
        con.commit()
        await bot.send_message(message.from_user.id, "✅ Успешно")
    else:
        await bot.send_message(message.from_user.id, "❌ Введены некоректные данные")


@router.callback_query(F.data == 'deleteAdmin')
async def confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id,
                           "✏ Введите Telegram ID пользователя для удаления из состава администрации")
    await state.set_state(RasStates.waiting_for_administr_del)


@router.message(RasStates.waiting_for_administr_del)
async def process_password(message: types.Message, state: FSMContext):
    text = message.text
    if text.isdigit():
        last_id = cur.execute('SELECT MAX (id) FROM Admins').fetchone()

        if last_id[0] is None:
            id = 1
        else:
            id = last_id[0] + 1

        cur.execute(f"DELETE FROM Admins WHERE user = {text}")
        con.commit()
        await bot.send_message(message.from_user.id, "✅ Успешно")
    else:
        await bot.send_message(message.from_user.id, "❌ Введены некорректные данные")


@router.message(F.text.lower() == 'рассылка')
async def admin_ras(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, 'Введите сообщение для рассылки🧐:')
    await state.set_state(RasStates.waiting_for_message)


@router.message(RasStates.waiting_for_message)
async def ras(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, 'Рассылка создана!')
    await broadcast_message(f"🔔 Уведомление от администратора: {message.text}")
    await state.clear()


async def broadcast_message(message: types.Message):
    # Функция для рассылки сообщения всем пользователям бота.
    cur.execute("SELECT user_id FROM Users")
    user_ids = cur.fetchall()

    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id[0], text=message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")


def but():
    but = [
        [
            types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        ],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=but)
    return keyboard


# Подтверждение вопросов
@router.message(F.text.lower() == 'инструкции')
async def process_questions(message: types.Message):
    cur.execute("SELECT id, content, author_id FROM Instructions WHERE is_active = 0;")
    all_instructions = cur.fetchall()

    await bot.send_message(message.chat.id, f"Instruction ID")

    unique_contents = set()  # Set to store unique instruction contents

    for instruction in all_instructions:
        instruction_id, content, user_id = instruction

        if content.isdigit():  # Check if the content is a message ID (numeric value)
            message_id = int(content)

            if message_id:
                await bot.copy_message(message.chat.id, from_chat_id=user_id, message_id=message_id)

                await bot.send_message(message.chat.id, f"Instruction ID: {instruction_id}\n\n{content}",
                                       reply_markup=but())

            else:
                # Invalid message ID, handle as text instruction
                await process_text_instruction(instruction_id, content, unique_contents, message.chat.id)
        else:
            # Non-numeric content, handle as text instruction
            await process_text_instruction(instruction_id, content, unique_contents, message.chat.id)


async def process_text_instruction(instruction_id, content, unique_contents, chat_id):
    if content in unique_contents:
        cur.execute("DELETE FROM Instructions WHERE id = ?", (instruction_id,))
        con.commit()
        return

    unique_contents.add(content)
    await bot.send_message(chat_id, f"Instruction ID: {instruction_id}\n\n{content}", reply_markup=but())


def but():
    buttons = [
        types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard


@router.callback_query(F.data == 'confirm')
async def confirm_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, "confirm")
    message_text = callback_query.message.text
    instruction_id = int(message_text.split()[2])  # Extract the instruction id from the callback data

    # Update the instruction status in the database
    cur.execute("UPDATE Instructions SET is_active = 1 WHERE id = ?", (instruction_id,))
    con.commit()

    # Get the author_id and content of the instruction from the Instructions table
    cur.execute("SELECT author_id, content FROM Instructions WHERE id = ?", (instruction_id,))
    result = cur.fetchone()

    author_id = result[0]
    instruction_content = result[1]
    cur.execute("UPDATE Users Set instructions = instructions+1 WHERE user_id = ?", (author_id,))
    con.commit()

    # Check if the user has enabled notifications
    cur.execute("SELECT notifications FROM Users WHERE user_id = ?", (author_id,))
    user_notification_row = cur.fetchone()

    if user_notification_row is not None:
        user_notifications = user_notification_row[0]

        # Если у пользователя включены уведомления, отправьте сообщение
        if user_notifications == 1:
            if author_id not in admin_num:
                if instruction_content.isdigit():
                    await bot.copy_message(chat_id=author_id, from_chat_id=author_id, message_id=instruction_content,
                                           caption="Ваша инструкция была опубликована",
                                           reply_markup=kb.menu_keyboard)
                else:
                    await bot.send_message(author_id,
                                           f"Ваша инструкция была опубликована\nСодержание: {instruction_content}",
                                           reply_markup=kb.menu_keyboard)

    # добавим повынесение изменений в базу данных вне if
    con.commit()


@router.callback_query(F.data == 'cancel')
async def cancel_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, "Отмена")

    message_text = callback_query.message.text

    if message_text:
        instruction_id = int(message_text.split()[2])  # Извлекаем ID инструкции из текста сообщения

        # Получаем ID автора и содержимое инструкции из таблицы Instructions
        cur.execute("SELECT author_id, content FROM Instructions WHERE id = ?", (instruction_id,))
        result = cur.fetchone()

        if result:
            author_id = result[0]
            instruction_content = result[1]

            # Удаляем инструкцию из базы данных
            cur.execute("DELETE FROM Instructions WHERE id = ?", (instruction_id,))
            con.commit()
            if author_id not in admin_num:
                # Отправляем сообщение пользователю, чья инструкция была отменена, включая содержимое
                await bot.send_message(author_id,
                                       f"Ваша инструкция была отклонена.\nID инструкции: {instruction_id}",
                                       reply_markup=kb.menu_keyboard)


@router.message(F.text == 'Ответы')
async def process_answers(message: types.Message):
    cur.execute("SELECT id,instruction_id, content, author FROM Answers WHERE is_active = 0;")
    all_instructions = cur.fetchall()

    unique_contents = set()  # Set to store unique instruction contents

    for instruction in all_instructions:
        ans_id, instruction_id, content, user_id = instruction

        message_id = None
        try:
            message_id = int(content)
            print(message_id, "559")
        except ValueError:
            pass

        if message_id:
            await bot.copy_message(message.chat.id, from_chat_id=user_id, message_id=message_id)
            await bot.send_message(message.chat.id, f"ID Ответа {ans_id} ID Инструкции {instruction_id}\n\n{content}",
                                   reply_markup=buts())
        else:
            # Handle as text instruction
            await process_text_answer(ans_id, instruction_id, content, unique_contents, message.chat.id)


async def process_text_answer(ans_id, instruction_id, content, unique_contents, chat_id):
    if content in unique_contents:
        cur.execute("DELETE FROM Answers WHERE id = ?", (ans_id,))
        con.commit()
        return

    unique_contents.add(content)

    await bot.send_message(chat_id, f"ID Ответа {ans_id} ID Инструкции {instruction_id}\n\n{content}",
                           reply_markup=buts())


def buts():
    buttons = [
        types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="yes"),
        types.InlineKeyboardButton(text="❌ Отменить", callback_data="no")
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard


@router.callback_query(F.data == 'yes')
async def confirma_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, "confirm")
    message_text = callback_query.message.text

    instruction_id = int(message_text.split()[5])

    ans_id = int(message_text.split()[2])
    print(instruction_id, "593")  # Extract the instruction id from the callback data

    # Update the instruction status in the database
    cur.execute("UPDATE Answers SET is_active = 1 WHERE id = ?", (ans_id,))
    con.commit()

    # Get the author_id and content of the instruction from the Instructions table
    cur.execute("SELECT author, content FROM Answers WHERE id = ?", (ans_id,))
    result = cur.fetchone()
    print(result, "Чето не нравится")
    author_id = result[0]
    instruction_content = result[1]
    if author_id not in admin_num:
        if type(instruction_content) == int:

            await bot.copy_message(chat_id=author_id, from_chat_id=author_id, message_id=instruction_content,
                                   caption=f"✅ Ваш ответ был опубликован.", reply_markup=kb.menu_keyboard)
        else:
            await bot.send_message(author_id,
                                   f"✅ Ваш ответ был опубликован.\nСодержание ответа: {instruction_content}")

    # Find all users who have requested notifications for this instruction
    cur.execute("SELECT author_id FROM Instructions WHERE id = ?", (instruction_id,))
    users_to_notify = cur.fetchall()
    print(users_to_notify, '613')

    for user in users_to_notify:
        user_id = user[0]
        # это вставил для проврки увед
        cur.execute("SELECT notifications FROM Users WHERE user_id = ?", (user_id,))
        user_notification_row = cur.fetchone()

        if user_notification_row is not None:
            user_notifications = user_notification_row[0]

            # Если у пользователя включены уведомления, отправьте сообщение
            # конец проверки увед

            if user_notifications == 1:
                print(user[0], '617')
                await bot.send_message(user_id,
                                       f"🚀 Новый ответ на вашу инструкцию \n Айди инструкции: {instruction_id}")

    con.commit()


@router.callback_query(F.data == 'no')
async def cancela_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, "Отменено")

    message_text = callback_query.message.text

    if message_text:
        instruction_id = int(message_text.split()[2])  # Извлекаем ID инструкции из текста сообщения

        # Получаем ID автора и содержимое инструкции из таблицы Instructions
        cur.execute("SELECT author, content FROM Answers WHERE id = ?", (instruction_id,))
        result = cur.fetchone()

        if result:
            author_id = result[0]
            instruction_content = result[1]

            # Удаляем инструкцию из базы данных
            cur.execute("DELETE FROM Answers WHERE id = ?", (instruction_id,))
            con.commit()
            if author_id not in admin_num:
                # Отправляем сообщение пользователю, чья инструкция была отменена, включая содержимое
                await bot.send_message(author_id,
                                       f"❌ Ваша инструкция была отменена.\nНомер ответа: {instruction_id}",
                                       reply_markup=kb.menu_keyboard)
            else:
                await bot.send_message(author_id,
                                       f"❌ Ваша инструкция была отменена.\nНомер ответа: {instruction_id}")
