import asyncio

from aiogram import Bot, Router, types, F
import keyboard as kb
from states import *
import sqlite3
import os
import logging
from config import TOKEN
import functions as f
import re

# подключение к базе данных
con = sqlite3.connect(r'bot_database.db')
cur = con.cursor()

# роутер
router = Router()
bot = Bot(token=TOKEN)


# создание инструкции
@router.callback_query(lambda a: a.data == 'сreate_instruction')
async def create_instruction(message: types.Message, state: FSMContext):
    await bot.send_message(message.from_user.id, "✏ Введите инструкцию:")
    await state.set_state(RasStates.waiting_for_instructions)

    @router.message(RasStates.waiting_for_instructions)
    async def process_instruction(message: types.Message, state: FSMContext):
        content = message.text
        if message.text:
            await state.update_data(text_content=content)
        else:
            forwarded_msg_id = message.message_id
            await state.update_data(forwarded_message_id=forwarded_msg_id, content_type=message.content_type)
        await bot.send_message(message.from_user.id, "✏ Введите заголовок:")
        await state.set_state(RasStates.waiting_for_title)

    @router.message(RasStates.waiting_for_title)
    async def process_title(message: types.Message, state: FSMContext):
        data = await state.get_data()
        title = message.text
        content = data.get('text_content')

        if content:
            hashtags = re.findall(r'#(\w+)', content)
            f.add_instruction(title, content, 0, message.from_user.username, message.from_user.id, message.date,
                              str(hashtags), 0, cur, con)
            await bot.send_message(message.from_user.id, "✅ Успешно")
        else:
            fwd_msg_id = data.get('forwarded_message_id')
            hashtags = data.get('content_type')
            f.add_instruction(title, fwd_msg_id, 0, message.from_user.username, message.from_user.id, message.date,
                              hashtags, 0, cur, con)
            await bot.send_message(message.from_user.id, "✅ Успешно")

        await state.clear()


instructions_data = {}


# просмотр всех инструкций
@router.callback_query(lambda a: a.data == 'view_instructions')
async def to_sort_callback(message: types.Message, state: FSMContext):
    sort_kb = [

        [
            types.InlineKeyboardButton(text='👥 Популярные', callback_data='View'),
            types.InlineKeyboardButton(text='🆕 Новые', callback_data='Date'),
        ]

    ]

    keyboard_sord = types.InlineKeyboardMarkup(inline_keyboard=sort_kb,
                                               resize_keyboard=True,
                                               input_field_placeholder="Фильтр"
                                               )

    await bot.send_message(message.from_user.id, f"Выберите параметр вывода инструкций📋", reply_markup=keyboard_sord)


@router.callback_query(F.data == 'Date')
async def date_sort(message: types.Message):
    cur.execute("""
                    SELECT author_id, content, title, id, addition_date FROM Instructions
                    WHERE is_active > 0
                    ORDER BY addition_date DESC;
                """)
    all_instructions = cur.fetchall()

    index = 0  # Индекс текущей инструкции пользователя

    instructions_data[message.from_user.id] = {'index': index, 'all_instructions': all_instructions}

    await send_next_instruction(message.from_user.id)


async def send_next_instruction(user_id):
    user_data = instructions_data.get(user_id)
    if user_data:
        index = user_data.get('index')
        all_instructions = user_data.get('all_instructions')
        print(all_instructions)
        if index < len(all_instructions):
            instruction = all_instructions[index]
            print(instruction, '289--------------------------------------------------------')
            author_id, content, title, instruction_id, vote_count = instruction
            user = await bot.get_chat(user_id)
            username = user.username
            if vote_count is None:
                votes = 0
            else:
                votes = vote_count
            answer = [
                [
                    types.InlineKeyboardButton(text="✉ Ответить", callback_data=f"reply_{instruction_id}"),
                    types.InlineKeyboardButton(text="📑 Посмотреть ответы",
                                               callback_data=f"viewAnswer_{instruction_id}"),
                    types.InlineKeyboardButton(text="➡ Пропустить", callback_data="skip")
                ],
                [types.InlineKeyboardButton(text="👍 Отдать голос", callback_data=f"voteQuestion_{instruction_id}")]
            ]
            keyboard_answer = types.InlineKeyboardMarkup(inline_keyboard=answer, resize_keyboard=True,
                                                         input_field_placeholder="Ты кем будешь, вацок")
            if content.isdigit():
                message_id = int(content)
                await bot.copy_message(user_id, from_chat_id=author_id, message_id=message_id, caption=title)
                await bot.send_message(user_id,
                                       f"{instruction_id}\n Автор @{username} \nДата Создания  {votes}",
                                       reply_markup=keyboard_answer)
            else:
                await bot.send_message(user_id,
                                       f"{instruction_id} \n{title}: {content}\n Количество голосов {votes}",
                                       reply_markup=keyboard_answer)
        else:
            await bot.send_message(user_id, "🫡 Вы просмотрели все инструкции.")
    else:
        await bot.send_message(user_id, "Начните сначала, чтобы просмотреть инструкции.")


@router.callback_query(F.data == 'View')
async def view_instructions(message: types.Message):
    cur.execute("""
                    SELECT i.author_id, i.content, i.title, i.id, (iv.user) as votes_count
                    FROM Instructions i
                    LEFT JOIN InstructionsVotes iv ON i.id = iv.instruction_id
                    WHERE i.is_active > 0
                    GROUP BY i.id
                    ORDER BY votes_count DESC;
            """)
    all_instructions = cur.fetchall()
    index = 0  # Индекс текущей инструкции пользователя
    instructions_data[message.from_user.id] = {'index': index, 'all_instructions': all_instructions}
    await send_next_instruction(message.from_user.id)


async def send_next_instruction(user_id):
    user_data = instructions_data.get(user_id)
    if user_data:
        index = user_data.get('index')
        all_instructions = user_data.get('all_instructions')
        print(all_instructions)

        if index < len(all_instructions):
            instruction = all_instructions[index]
            print(instruction, '289--------------------------------------------------------')
            author_id, content, title, instruction_id, vote_count = instruction
            user = await bot.get_chat(user_id)
            username = user.username
            if vote_count is None:
                votes = 0
            else:
                votes = vote_count

            answer = [
                [
                    types.InlineKeyboardButton(text="✉ Ответить", callback_data=f"reply_{instruction_id}"),
                    types.InlineKeyboardButton(text="📑 Посмотреть ответы",
                                               callback_data=f"viewAnswer_{instruction_id}"),
                    types.InlineKeyboardButton(text="➡ Пропустить", callback_data="skip")
                ],
                [types.InlineKeyboardButton(text="👍 Отдать голос", callback_data=f"voteQuestion_{instruction_id}")]
            ]

            keyboard_answer = types.InlineKeyboardMarkup(inline_keyboard=answer, resize_keyboard=True,
                                                         input_field_placeholder="Ты кем будешь, вацок")

            if content.isdigit():
                message_id = int(content)
                await bot.copy_message(user_id, from_chat_id=author_id, message_id=message_id, caption=title,
                                       reply_markup=keyboard_answer)
                # await bot.send_message(user_id,
                #                        f"{instruction_id}\n author @{username} \nКоличество голосов {votes}",
                #                        reply_markup=keyboard_answer)
            else:

                await bot.send_message(user_id, f"{instruction_id} \n{title}: {content}\n Количество голосов {votes}",
                                       reply_markup=keyboard_answer)
        else:
            await bot.send_message(user_id, "🫡 Вы просмотрели все инструкции.")
    else:
        await bot.send_message(user_id, "Начните сначала, чтобы просмотреть инструкции.")


@router.callback_query(lambda a: a.data == 'skip')
async def skip_instruction(message: types.Message):
    user_id = message.from_user.id

    user_data = instructions_data.get(user_id)
    if user_data:
        index = user_data.get('index')
        instructions_data[user_id]['index'] = index + 1

        await f.send_next_instruction(user_id, bot, instructions_data)
    else:
        await bot.send_message(user_id, "Начните сначала, чтобы просмотреть инструкции.")


@router.callback_query(lambda c: c.data.startswith('reply'))
async def reply_instruction(callback_query: types.CallbackQuery, state: FSMContext):
    cont_1 = callback_query.data.split('_')[1]

    instruction_id = int(cont_1)

    await state.update_data(instruction_id=instruction_id)  # Update instruction_id in the FSMContext
    await bot.send_message(callback_query.from_user.id,
                           "Введите ответ: ")
    await state.set_state(RasStates.waiting_for_answer)


@router.message(RasStates.waiting_for_answer)
async def process_instruction(message: types.Message, state: FSMContext):
    content = message.text
    user_id = message.from_user.id

    data = await state.get_data()
    instruction_id = data.get('instruction_id', None)  # Retrieve instruction_id from the FSMContext

    print(f"{content}\n{user_id}\n{instruction_id}    это уйдет в бд")

    if message.text:
        await state.update_data(text_content=content, text_instruction_id=instruction_id)
        f.add_answer(content, 0, user_id, message.date, instruction_id, cur, con)
        await state.clear()
        await bot.send_message(message.from_user.id, "🛃 Отправлено на модерацию")

    else:
        forwarded_msg_id = message.message_id
        await state.update_data(forwarded_message_id=forwarded_msg_id, content_type=message.content_type,
                                text_instruction_id=instruction_id)
        f.add_answer(forwarded_msg_id, 0, user_id, message.date, instruction_id, cur, con)
        await state.clear()
        await bot.send_message(message.from_user.id, "🛃 Отправлено на модерацию")


@router.callback_query(lambda c: c.data.startswith('voteQuestion'))
async def vote_question(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cont_1 = callback_query.data.split('_')[1]
    print(cont_1)
    ans_id = int(cont_1)
    cur.execute('UPDATE Users SET instructions = instructions + 1 WHERE user_id = ?', (user_id,))

    # Check if the answer has been already rated by the user
    cur.execute('SELECT * FROM InstructionsVotes WHERE instruction_id = ?', (ans_id,))
    existing_vote = cur.fetchone()

    if existing_vote:
        # If the user has already voted for this answer, update the user's vote count
        cur.execute('UPDATE InstructionsVotes SET user = user + 1 WHERE instruction_id = ?', (ans_id,))
    else:
        last_id = cur.execute('SELECT MAX(id) FROM InstructionsVotes').fetchone()

        if last_id[0] is None:
            id = 1
        else:
            id = last_id[0] + 1
        # If the user has not voted for this answer yet, insert a new vote record
        cur.execute('INSERT INTO InstructionsVotes (id,user,instruction_id) VALUES (?,1, ?)',
                    (id, ans_id))

    con.commit()
    await bot.answer_callback_query(callback_query.id, "✅ Ваш голос засчитан")
