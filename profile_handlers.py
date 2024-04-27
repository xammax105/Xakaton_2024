from aiogram import Bot, Router, types, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import keyboard as kb
from states import *
import sqlite3
import os
import logging
from config import TOKEN
import functions as f

# подключение к базе данных
con = sqlite3.connect(r'bot_database.db')
cur = con.cursor()

# роутер
router = Router()
bot = Bot(token=TOKEN)


# вывод своих инструкций
@router.callback_query(lambda a: a.data == 'edit_ins_ans')
async def select_edit(callback_query: types.CallbackQuery):
    men_kb = [
        [
            types.InlineKeyboardButton(text='Изменить Ответ ✏️', callback_data='More'),
            types.InlineKeyboardButton(text='Изменить Инструкцию ✍️', callback_data='editinstr'),
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=men_kb,
                                          resize_keyboard=True,
                                          input_field_placeholder="Выберите действие"
                                          )
    await bot.send_message(callback_query.from_user.id, f"Что вас интересует? 🛠️", reply_markup=keyboard)


@router.callback_query(lambda a: a.data == 'editinstr')
async def process_edit_answer_callback(callback_query: types.CallbackQuery, state: FSMContext):
    offset = int(callback_query.data.split('_')[-1]) if '_' in callback_query.data else 0
    sql_query = f"SELECT * FROM Instructions WHERE author_id = {callback_query.from_user.id}"
    cur.execute(sql_query)
    answers = cur.fetchall()
    if offset < len(answers):
        answer = answers[offset]
        idd = answer[0]
        print(idd)
        answer_title = answer[1]
        answer_text = answer[2]

        more_kb = [
            [
                types.InlineKeyboardButton(text='Редактировать', callback_data=f'EditInsrtact_{idd}'),
                types.InlineKeyboardButton(text='Удалить', callback_data=f'Delete_instr_{idd}'),
                types.InlineKeyboardButton(text='Пропустить', callback_data=f'skipe_{offset}')
            ]
        ]
        upd_answer = types.InlineKeyboardMarkup(inline_keyboard=more_kb)

        if type(answer_text) == int:
            await bot.copy_message(callback_query.from_user.id, from_chat_id=callback_query.from_user.id,
                                   message_id=answer_text, reply_markup=upd_answer)
        else:
            await bot.send_message(callback_query.from_user.id,
                                   f"Заголовок: {answer_title}\nСодержание: {answer_text}",
                                   reply_markup=upd_answer)

        new_offset = offset + 1
        if new_offset < len(answers):
            await bot.answer_callback_query(callback_query.id,
                                            f"Следующий ответ ({new_offset + 1}/{len(answers)})")

    else:
        await bot.send_message(callback_query.from_user.id, "Все ответы просмотрены.")

    @router.callback_query(F.data.startswith('skipe'))
    async def process_skip_callback(callback_query: types.CallbackQuery):
        offset = int(callback_query.data.split('_')[-1])

        sql_query = f"SELECT * FROM Instructions WHERE author_id = {callback_query.from_user.id}"
        cur.execute(sql_query)
        answers = cur.fetchall()

        if offset < len(answers):
            # Skip to the next answer
            answer = answers[offset]
            idd = answer[0]
            answer_title = answer[1]
            answer_text = answer[2]

            more_kb = [
                [
                    types.InlineKeyboardButton(text='Редактировать', callback_data=f'EditAnswer_{idd}'),
                    types.InlineKeyboardButton(text='Удалить', callback_data=f'DeleteAnswer_{idd}'),
                    types.InlineKeyboardButton(text='Пропустить', callback_data=f'skiped_{offset + 1}')
                ]
            ]
            upd_answer = types.InlineKeyboardMarkup(inline_keyboard=more_kb)

            if answer_text.isdigit():
                await bot.copy_message(callback_query.from_user.id, from_chat_id=callback_query.from_user.id,
                                       message_id=answer_text, reply_markup=upd_answer)
            else:
                await bot.send_message(callback_query.from_user.id,
                                       f"Заголовок: {answer_title}\nСодержание: {answer_text}",
                                       reply_markup=upd_answer)

            await bot.answer_callback_query(callback_query.id, "Пропущено\nСледующий ответ")
        else:
            await bot.send_message(callback_query.from_user.id, "Все ответы просмотрены.")


@router.callback_query(lambda c: c.data.startswith ('EditInsrtact'))
async def process_edit_answer_callback(callback_query: types.CallbackQuery, state: FSMContext):
    cont_1 = callback_query.data.split('_')[1]

    ans_id = int(cont_1)
    await state.update_data(ans_id=ans_id)

    # Запрашиваем у пользователя новое содержимое ответа
    await bot.send_message(callback_query.from_user.id, "Введите новое содержание Инструкци:")
    await state.set_state(RasStates.waiting_for_new_instract)
@router.message(RasStates.waiting_for_new_instract)
async def process_new_answer_content(message: types.Message, state: FSMContext):
    cont_1 = message.text
    if cont_1 is None:
        cont_1 = message.message_id
        print(cont_1, "33300005555")
    else:
        cont_1 = message.text
        print(cont_1)
    ans_id = (await state.get_data())['ans_id']
    print(cont_1, "ОТВЕТ")
    print(ans_id, "AUDIiiiii")
    # Обновляем запись в таблице Answers с новым содержанием и устанавливаем is_active на 0
    cur.execute("UPDATE Instructions SET content = ?, is_active = 0 WHERE id = ?", (cont_1, ans_id))
    con.commit()
    await message.answer("Ответ успешно обновлен. Отправлен на модерацию. Вам придет оповещение о результате модерирования")

    await state.clear()


@router.callback_query(lambda c: c.data.startswith('Delete_instr'))
async def process_edit_answer_callback(callback_query: types.CallbackQuery):
    cont_1 = callback_query.data.split('_')[2]

    ans_id = int(cont_1)
    cur.execute("DELETE FROM Instructions WHERE ID = ?", (ans_id,))
    con.commit()
    cur.execute("Delete From InstructionsVotes WHERE instruction_id = ?", (ans_id,))
    con.commit()
    await bot.send_message(callback_query.from_user.id, "Успешно удалено")




# вывод своих ответов
@router.callback_query(F.data == 'More')
async def edit_my_answers(callback_query: types.CallbackQuery):
    offset = int(callback_query.data.split('_')[-1]) if '_' in callback_query.data else 0

    sql_query = f"SELECT * FROM Answers WHERE author = {callback_query.from_user.id}"
    cur.execute(sql_query)
    answers = cur.fetchall()

    if offset < len(answers):
        answer = answers[offset]
        idd = answer[0]
        answer_text = answer[1]

        more_kb = [
            [
                types.InlineKeyboardButton(text='Редактировать', callback_data=f'EditAnswer_{idd}'),
                types.InlineKeyboardButton(text='Удалить', callback_data=f'DeleteAnswer_{idd}'),
                types.InlineKeyboardButton(text='Пропустить', callback_data=f'skiped_{offset + 1}')
            ]
        ]
        upd_answer = types.InlineKeyboardMarkup(inline_keyboard=more_kb)

        if type(answer_text) == int:
            await bot.copy_message(callback_query.from_user.id, from_chat_id=callback_query.from_user.id,
                                   message_id=answer_text, reply_markup=upd_answer)
        else:
            await bot.send_message(callback_query.from_user.id,
                                   f"Содержание: {answer_text}",
                                   reply_markup=upd_answer)

        new_offset = offset + 1
        if new_offset < len(answers):
            await bot.answer_callback_query(callback_query.id,
                                            f"Следующий ответ ({new_offset + 1}/{len(answers)})")

    else:
        await bot.send_message(callback_query.from_user.id, "Все ответы просмотрены.")

    # обработка пропуска

    @router.callback_query(lambda a: a.data.startswith('EditAnswer_'))
    async def process_edit_answer_callback(callback_query: types.CallbackQuery, state: FSMContext):
        cont_1 = callback_query.data.split('_')[1]

        ans_id = int(cont_1)
        await state.update_data(ans_id=ans_id)

        # Запрашиваем у пользователя новое содержимое ответа
        await bot.send_message(callback_query.from_user.id, "Введите новое содержание ответа:")
        await state.set_state(RasStates.waiting_for_new_answer)

    @router.message(RasStates.waiting_for_new_answer)
    async def process_new_answer_content(message: types.Message, state: FSMContext):
        cont_1 = message.text

        if cont_1 is None:
            cont_1 = message.message_id
            print(cont_1, "33300005555")
        else:
            cont_1 = message.text
            print(cont_1)

        ans_id = (await state.get_data())['ans_id']
        print(cont_1, "ОТВЕТ")
        print(ans_id, "AUDIiiiii")

        # Обновляем запись в таблице Answers с новым содержанием и устанавливаем is_active на 0
        cur.execute("UPDATE Answers SET content = ?, is_active = 0 WHERE id = ?", (cont_1, ans_id))
        con.commit()
        await message.answer(
            "Ответ успешно обновлен. Отпрвлен на модерацию. Вам придет оповещение о результате модерирования")

        await state.clear()

    @router.callback_query(F.data.startswith('skiped'))
    async def process_skip_callback(callback_query: types.CallbackQuery):
        offset = int(callback_query.data.split('_')[-1])

        sql_query = f"SELECT * FROM Answers WHERE author = {callback_query.from_user.id}"
        cur.execute(sql_query)
        answers = cur.fetchall()

        if offset < len(answers):
            # Skip to the next answer
            answer = answers[offset]
            idd = answer[0]
            answer_text = answer[1]

            more_kb = [
                [
                    types.InlineKeyboardButton(text='Редактировать', callback_data=f'EditAnswer_{idd}'),
                    types.InlineKeyboardButton(text='Удалить', callback_data=f'DeleteAnswer_{idd}'),
                    types.InlineKeyboardButton(text='Пропустить', callback_data=f'skiped_{offset + 1}')
                ]
            ]
            upd_answer = types.InlineKeyboardMarkup(inline_keyboard=more_kb)

            if type(answer_text) == int:
                await bot.copy_message(callback_query.from_user.id, from_chat_id=callback_query.from_user.id,
                                       message_id=answer_text, reply_markup=upd_answer)
            else:
                await bot.send_message(callback_query.from_user.id,
                                       f"Содержание: {answer_text}",
                                       reply_markup=upd_answer)

            await bot.answer_callback_query(callback_query.id, "Пропущено\nСледующий ответ")
        else:
            await bot.send_message(callback_query.from_user.id, "Все ответы просмотрены.")

    @router.callback_query(lambda a: a.data.startswith('DeleteAnswer'))
    async def process_edit_answer_callback(callback_query: types.CallbackQuery):
        cont_1 = callback_query.data.split('_')[1]

        ans_id = int(cont_1)
        cur.execute("DELETE FROM Answers WHERE id = ?", (ans_id,))
        con.commit()
        cur.execute("Delete From AnswersVotes WHERE answer_id = ?", (ans_id,))
        con.commit()
        await bot.send_message(callback_query.from_user.id, "Успешно удалено")

    # редактирование ответа


# вывод своих подписок
@router.callback_query(lambda a: a.data == 'my_subscriptions')
async def get_my_subscriptions(callback_query: types.CallbackQuery):
    cur.execute(f"SELECT tags FROM Subscribes WHERE user = {callback_query.from_user.id}")
    my_subscriptions = cur.fetchall()

    tags = [tag[0] for tag in my_subscriptions]
    if len(tags) == 0:
        await bot.send_message(callback_query.from_user.id, "Вы ни на что не подписаны")
    else:
        await bot.send_message(callback_query.from_user.id, "Мои подписки:")
        for tag in tags:
            unsub_keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="Отписаться",
                                                             callback_data=f"unsub_{tag}")]])
            await bot.send_message(callback_query.from_user.id, f"#{tag}", reply_markup=unsub_keyboard)


# обработка отмены подписки
@router.callback_query(lambda a: a.data.startswith('unsub_'))
async def unsub_hashtag(callback_query: types.CallbackQuery):
    hashtag = callback_query.data.split('_')[1]
    cur.execute(f"DELETE FROM Subscribes WHERE user = {callback_query.from_user.id} AND tags = '{hashtag}'")
    con.commit()

    await callback_query.answer(f"Вы отписались от тега #{hashtag}")


@router.callback_query(F.data == 'DeleteDB')
async def send_locate(callback_query: types.CallbackQuery, state: FSMContext):
    mell_gif = types.FSInputFile('images/plakiplaki.gif', 'rb')

    await bot.send_message(callback_query.from_user.id, "<b>Зря...</b>\n"
                                                        "За тобой уже выехали", parse_mode='HTML')
    await bot.send_location(callback_query.from_user.id, latitude=55.708902, longitude=37.721058)
    await bot.send_video(callback_query.from_user.id, mell_gif)


@router.callback_query(F.data == 'DeleteProfile')
async def delete_profile(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, f"🔓 Для подтверждения удаления профиля введите: {callback_query.from_user.id}")
    await state.set_state(RasStates.waiting_for_delete)


@router.message(RasStates.waiting_for_delete)
async def process_delete(message: types.Message, state: FSMContext):
    mes = message.text

    if mes.isdigit() and int(mes) == message.from_user.id:
        cur.execute(f"SELECT ID FROM Instructions WHERE author_id = {mes}")
        rows = cur.fetchall()
        cur.execute(f"SELECT ID FROM Answers WHERE author = {mes}")
        ans = cur.fetchall()
        for row in rows:
            instruction_id = row[0]

            cur.execute(f"Delete  FROM InstructionsVotes WHERE instruction_id = {instruction_id}")
            cur.execute(f"Delete  FROM Instructions WHERE author_id = {mes}")  # УДАЛЕНИ из табл с голосами за инструкции

        for an in ans:
            instruction_id = an[0]

            cur.execute(f"Delete  FROM AnswersVotes WHERE answer_id = {instruction_id}")

            cur.execute(f"Delete  FROM Answers WHERE author = {mes}")  # УДАЛЕНИ из табл с голосами за инструкции

        cur.execute(f"Delete  FROM Users Where user_id = {mes}")
        con.commit()
        await bot.send_message(message.from_user.id,"Надеюсь вы вернетесь😢 \n Если вы вновь захотите пользоваться "
                                                    "ботом, просто введите /start")
    else:
        await bot.send_message(message.from_user.id, "Введен некорректный ответ, удаление отменено")

        await state.clear()


@router.callback_query(lambda a: a.data == 'ofonnotifs')
async def check_notifs(callback_query: types.CallbackQuery):
    cur.execute(f"SELECT notifications from Users WHERE user_id = {callback_query.from_user.id}")
    res = cur.fetchone()[0]

    if res == 0:
        # включение уведомлений
        cur.execute(f"UPDATE Users SET notifications = 1 WHERE user_id = {callback_query.from_user.id}")
        con.commit()
        await callback_query.answer("🔔 Уведомления включены")
    elif res == 1:
        # выключение уведомлений
        cur.execute(f"UPDATE Users SET notifications = 0 WHERE user_id = {callback_query.from_user.id}")
        con.commit()
        await callback_query.answer("🔕 Уведомления выключены")