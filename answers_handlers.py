from aiogram import Bot, Router, types, F
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


@router.callback_query(lambda c: c.data.startswith('viewAnswer'))
async def view_answer(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split('_')[1]
    # Extract the first word from the message text
    instruction_id = int(user_id)

    cur.execute('''
                SELECT A.id, A.content, A.author, V.user AS vote_count
                FROM Answers A
                LEFT JOIN AnswersVotes V ON A.id = V.answer_id
                WHERE A.instruction_id = ?
                GROUP BY A.id
                ORDER BY vote_count DESC
    ''', (instruction_id,))

    result = cur.fetchall()  # тут добавить проверку по result с табл с колво голосов, по столбцу id и потом сортирвка, тяжелый запрос пиздец
    if result:
        for instruction in result:
            ans_id, content, user_id, vote_count = instruction
            user = await bot.get_chat(user_id)
            username = user.username
            if vote_count is None:
                votes = 0
            else:
                votes = vote_count
            men_kb = [

                [
                    types.InlineKeyboardButton(text='👍 Оценить', callback_data=f'voteAnswer_{ans_id}'),
                    types.InlineKeyboardButton(text='🗑 Удалить из чата', callback_data='delete_answer'),
                ]
            ]

            keyboard_ans = types.InlineKeyboardMarkup(inline_keyboard=men_kb,
                                                      resize_keyboard=True,
                                                      input_field_placeholder="Ты кем будешь,вацок"
                                                      )

            message_id = None
            try:
                message_id = int(content)
                print(message_id, "559")
            except ValueError:
                pass

            if message_id:
                await bot.copy_message(callback_query.from_user.id, from_chat_id=user_id, message_id=message_id,
                                       caption=f"{instruction_id}\n\n Автор @{username} \n🗳 Количество голосов {votes}",
                                       reply_markup=keyboard_ans)
                # await bot.send_message(message.from_user.id,
                #                        f"{ans_id} id Инструкции {instruction_id}\n\n author @{username} \nКоличество голосов {votes}"  ,
                #                        reply_markup=keyboard_ans)

            else:
                response_text = f"{ans_id} Содержание: {content}\nАвтор: @{username}\n\n🗳 Количество голосов {votes}"

                # Create inline keyboard

                await bot.send_message(callback_query.from_user.id, f"{response_text}", reply_markup=keyboard_ans)

    else:
        response_text = "😬 На данную инструкцию нет ответов"
        await bot.send_message(callback_query.from_user.id, response_text)

    @router.callback_query(lambda c: c.data.startswith('voteAnswer'))
    async def vote_answer(callback_query: types.CallbackQuery):
        user_id = callback_query.from_user.id
        ans_id = callback_query.data.split('_')[1]
        # Extract the first word from the message text
        instruction_id = int(user_id)
        cur.execute('UPDATE Users SET answers = answers + 1 WHERE user_id = ?', (user_id,))

        # Check if the answer has been already rated by the user
        cur.execute('SELECT * FROM AnswersVotes WHERE answer_id = ?', (ans_id,))
        existing_vote = cur.fetchone()

        if existing_vote:
            # If the user has already voted for this answer, update the user's vote count
            cur.execute('UPDATE AnswersVotes SET user = user + 1 WHERE answer_id = ?', (ans_id,))
        else:
            last_id = cur.execute('SELECT MAX(id) FROM AnswersVotes').fetchone()

            if last_id[0] is None:
                id = 1
            else:
                id = last_id[0] + 1
            # If the user has not voted for this answer yet, insert a new vote record
            cur.execute('INSERT INTO AnswersVotes (id,user,answer_id) VALUES (?,1, ?)',
                        (id, ans_id))

        con.commit()
        await bot.answer_callback_query(callback_query.id, "✅ Ваш голос засчитан")

    @router.callback_query(F.data == 'delete_answer')
    async def delete_answer(callback_query: types.CallbackQuery):
        message_id = callback_query.message.message_id
        chat_id = callback_query.message.chat.id
        await bot.delete_message(chat_id, message_id)
