
from aiogram import Bot, Router, types, F
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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


@router.message(F.text.lower() == 'меню📄')
async def user(message: types.Message):
    await bot.send_message(message.from_user.id, f"Меню: ", reply_markup=kb.menu_keyboard)


@router.message(F.text.lower() == 'разработчики🥴')
async def history(message: types.Message):
    photo_maks =  await bot.get_user_profile_photos(989808944, limit=10)
    photo_file_maks = photo_maks.photos[0][-1].file_id
    photo_den = await bot.get_user_profile_photos(1662425966, limit=10)
    photo_file_den = photo_den.photos[0][-1].file_id
    photo_gosha = await bot.get_user_profile_photos(666366306, limit=10)
    photo_file_gosha = photo_gosha.photos[0][-1].file_id

    await bot.send_photo(chat_id=message.from_user.id, photo=photo_file_maks,caption=f"<b>Максим Каничев</b>\n18 "
                                                                                     f"годиков\nстудент ПК "
                                                                                     f"БГТУ\nномер карты "
                                                                                     f"<code>2202201367764954</code>",
                         parse_mode='HTML')
    await bot.send_photo(chat_id=message.from_user.id, photo=photo_file_den,caption=f"<b>Денис Арапов</b>\n18 "
                                                                                    f"годиков\nстудент ПК БГТУ\nномер"
                                                                                    f" карты "
                                                                                    f"<code>2202201367764954</code>",
                         parse_mode='HTML')
    await bot.send_photo(chat_id=message.from_user.id, photo=photo_file_gosha,caption=f"<b>Георгий Беришвили</b>\n18 "
                                                                                      f"годиков\nстудент ПК "
                                                                                      f"БГТУ\nномер карты "
                                                                                      f"<code>2200701014139775</code>",
                         parse_mode='HTML')


@router.callback_query(F.data == 'admin')
async def admin(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_num:
        await bot.send_message(message.from_user.id, "Введите пароль: 🔐")
        # Ожидаем ответ с паролем
        await state.set_state(RasStates.waiting_for_password)
    else:
        await bot.send_message(message.from_user.id, "Вы не являетесь <b>админом</b>🤔", parse_mode='HTML')

    @router.message(RasStates.waiting_for_password)
    async def process_password(message: types.Message, state: FSMContext):
        password = message.text
        if password == "123":  # Замените "your_password" на реальный пароль
            await bot.send_message(message.from_user.id, "Добро пожаловать в админ-панель💪",
                                   reply_markup=kb.get_admin_keyboard())
        else:
            await bot.send_message(message.from_user.id, "Неправильный пароль🔒")
            # Вызываем функцию user(message)
            await user(message)
        # Сброс состояния после проверки пароля
        await state.clear()


# обработка кнопки профиль
@router.callback_query(F.data == 'profile')
async def profile_command(message: types.Message):
    # Получение количества ответов пользователя
    query = """SELECT answers FROM Users WHERE user_id = ?"""
    cur.execute(query, (message.from_user.id,))
    answers_count = cur.fetchone()[0]

    # Определение статуса пользователя по количеству ответов
    if answers_count < 5:
        answers_rank = "🧑 Новичок"
    elif 5 <= answers_count < 10:
        answers_rank = "🧐 Знаток"
    elif 10 <= answers_count < 20:
        answers_rank = "👨🏼‍🎓 Гуру"
    else:
        answers_rank = "🌌 Высший разум"

    if answers_count is None:
        answers_rank = "🧑 Новичок"

    # Получение инструкций пользователя
    query1 = """SELECT instructions FROM Users WHERE user_id = ?"""
    cur.execute(query1, (message.from_user.id,))
    instr_count = cur.fetchone()[0]

    # Определение статуса пользователя по инструкциям
    if instr_count < 5:
        inst_rank = "🧑 Ученик"
    elif 5 <= instr_count < 10:
        inst_rank = "🧐 Помощник"
    elif 10 <= instr_count < 20:
        inst_rank = "👨🏼‍🎓 Мыслитель"
    else:
        inst_rank = "🌌 Гений"

    if instr_count is None:
        inst_rank = "🧑 Ученик"

    try:
        photos = await bot.get_user_profile_photos(message.from_user.id, limit=10)
        photo_file = photos.photos[0][-1].file_id
        await bot.send_photo(message.from_user.id, photo_file, caption=f'👤 Ваш профиль:\n'
                                                                       f'Имя: {message.from_user.first_name}\n'
                                                                       f'Юзернейм: @{message.from_user.username}\n\n'
                                                                       f'🌟 Ранг инструкций: {inst_rank}\n'
                                                                       f'Инструкций: {instr_count}\n\n'
                                                                       f'🌟 Ранг ответов: {answers_rank}\n'
                                                                       f'Ответов: {answers_count}',
                             reply_markup=kb.get_profile_kb(message.from_user.id)
                             )

    except Exception as e:
        print(e)
        await bot.send_message(message.from_user.id, f'👤 Ваш профиль:\n'
                                                     f'Имя: {message.from_user.first_name}\n'
                                                     f'Юзернейм: @{message.from_user.username}\n\n'
                                                     f'🌟 Ранг инструкций: {inst_rank}\n'
                                                     f'Инструкций: {instr_count}\n\n'
                                                     f'🌟 Ранг ответов: {answers_rank}\n'
                                                     f'Ответов: {answers_count}',
                               reply_markup=kb.get_profile_kb(message.from_user.id)
                               )


# обработка кнопки наш топ
@router.callback_query(F.data == 'top')
async def Top(callback_query: types.CallbackQuery):
    # берем топ по интсрукциям
    users_instructions = f.get_users_instructions_count(cur)
    users_answers = f.get_users_answers_count(cur)

    # топ по инструкциям
    inst_keyboard = InlineKeyboardBuilder()
    for user_id, num_instructions in users_instructions:
        user = await bot.get_chat(user_id)
        username = user.username
        button = types.InlineKeyboardButton(text=f"@{username} - {num_instructions} инструкций",
                                            callback_data=f"user_{user_id}")
        inst_keyboard.row(button)

    # топ по ответам
    answ_keyboard = InlineKeyboardBuilder()
    for user_id, num_answers in users_answers:
        user = await bot.get_chat(user_id)
        username = user.username
        button = types.InlineKeyboardButton(text=f"@{username} - {num_answers} ответов",
                                            callback_data=f"user_{user_id}")
        answ_keyboard.row(button)

    await bot.send_message(callback_query.message.chat.id,
                           "🏆 Топ пользователей по инструкциям:",
                           reply_markup=inst_keyboard.as_markup())
    await bot.send_message(callback_query.message.chat.id,
                           "🏆 Топ пользователей по ответам:",
                           reply_markup=answ_keyboard.as_markup())


# выводим инфу по юзеру
@router.callback_query(lambda a: a.data.startswith('user_'))
async def show_user_info(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split('_')[1]
    # Получение количества ответов пользователя
    query = """SELECT answers FROM Users WHERE user_id = ?"""
    cur.execute(query, (user_id,))
    answers_count = cur.fetchone()[0]

    # Определение статуса пользователя по количеству ответов
    if answers_count < 5:
        answers_rank = "🧑 Новичок"
    elif 5 <= answers_count < 10:
        answers_rank = "🧐 Знаток"
    elif 10 <= answers_count < 20:
        answers_rank = "👨🏼‍🎓 Гуру"
    else:
        answers_rank = "🌌 Высший разум"

    if answers_count is None:
        answers_rank = "🧑 Новичок"

    # Получение инструкций пользователя
    query1 = """SELECT instructions FROM Users WHERE user_id = ?"""
    cur.execute(query1, (user_id,))
    instr_count = cur.fetchone()[0]

    # Определение статуса пользователя по инструкциям
    if instr_count < 5:
        inst_rank = "🧑 Ученик"
    elif 5 <= instr_count < 10:
        inst_rank = "🧐 Помощник"
    elif 10 <= instr_count < 20:
        inst_rank = "👨🏼‍🎓 Мыслитель"
    else:
        inst_rank = "🌌 Гений"

    if instr_count is None:
        inst_rank = "🧑 Ученик"
    try:
        # вытягиваем имя и юзернейм
        user = await bot.get_chat(user_id)
        user_first_name = user.first_name
        username = user.username

        # вытягиваем счет инструкций
        cur.execute(f"SELECT COUNT(ID) + 1 AS num_instructions FROM Instructions WHERE author_id = {user_id};")
        author_instr = cur.fetchone()[0]

        # вытягиваем счет ответов
        cur.execute(f"SELECT COUNT(ID) AS num_answers FROM Answers WHERE author = {user_id};")
        author_answ = cur.fetchone()[0]

        # # вытягиваем ранги
        # cur.execute(f"""
        #     SELECT Ranks.name
        #     FROM Users
        #     LEFT JOIN Ranks ON Users.instructions = Ranks.id
        #     WHERE Users.user_id = {user_id}
        # """)
        # instr_rank = cur.fetchone()[0]
        #
        # cur.execute(f"""
        #             SELECT Ranks.name
        #             FROM Users
        #             LEFT JOIN Ranks ON Users.answers = Ranks.id
        #             WHERE Users.user_id = {user_id}
        #         """)
        # answ_rank = cur.fetchone()[0]
        # переделать ранги и прочую хуйню
        # выводим
        await bot.send_message(callback_query.message.chat.id, f"👤 Автор: {user_first_name}\n"
                                                               f"@{username}\n"
                                                               f"Инструкций: {author_instr}\n"
                                                               f"Ответов: {author_answ}\n"
                                                               f"🌟 Ранг инструкций: {inst_rank}\n"
                                                               f"🌟 Ранг ответов: {answers_rank}\n")
    except Exception as e:
        print(e)


# обработка кнопки инструкции
@router.callback_query(F.data == 'instructions')
async def instructions(message: types.Message):
    await bot.send_message(message.from_user.id, f"📚 Инструкции", reply_markup=kb.keyboard_inst)


# обработка кнопки теги
@router.callback_query(F.data == 'tags')
async def tags(message: types.Message):
    tags_keyboard = InlineKeyboardBuilder()
    tags = f.get_hashtags(cur)
    for tag in tags:
        button = types.InlineKeyboardButton(text=f"#{tag}", callback_data=f"subscribe_tag_{tag}")
        tags_keyboard.add(button)
    tags_keyboard.adjust(2)
    await bot.send_message(message.from_user.id, f"📩 Выберите теги, на которые хотите подписаться:",
                           reply_markup=tags_keyboard.as_markup())


# подписаться на тег
@router.callback_query(lambda a: a.data.startswith("subscribe_tag_"))
async def subscribe_tag(callback_query: types.CallbackQuery):
    # берем тег
    tag = callback_query.data.split("_")[2]

    # проверяем, нет ли уже такой подписки
    cur.execute(
        f"select exists (select 1 from Subscribes where user = {callback_query.from_user.id} and tags = '{tag}');")
    is_subscribed = cur.fetchone()[0]

    if is_subscribed == 0:
        # если не подписан на этот тег
        # добавляем запись в таблицу подписок
        cur.execute(f"INSERT INTO Subscribes (user, tags) VALUES ({callback_query.from_user.id}, '{tag}')")
        con.commit()
        await callback_query.answer(f"✅ Вы подписались на тег {tag}!")
    elif is_subscribed == 1:
        # если подписан
        await callback_query.answer(f"✅ Вы уже подписаны на этот тег")


@router.callback_query(lambda a: a.data == 'search')
async def search_for_tags(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "🔎 Введите тег, чтобы найти статьи, содержащие его:")
    await state.set_state(RasStates.waiting_for_tag_search)

    @router.message(RasStates.waiting_for_tag_search)
    async def search_tags(message: types.Message, state: FSMContext):
        tag = message.text

        if tag[0] == "#":
            tag = tag[1:]

        cur.execute(f"SELECT * FROM Instructions WHERE tags LIKE '%{tag}%' AND is_active = 1")
        res = cur.fetchall()

        # Ищем инструкции по тегу
        instructions = res

        # Отправляем результат пользователю
        if instructions:
            for instruction in instructions:
                answer = [
                    [
                        types.InlineKeyboardButton(text="Ответить", callback_data=f"reply_{instruction[0]}"),
                        types.InlineKeyboardButton(text="Посмотреть ответы", callback_data="viewAnswer")
                    ],
                    [types.InlineKeyboardButton(text="Отдать голос", callback_data=f"voteQuestion_{instruction[0]}")]
                ]

                keyboard_answer = types.InlineKeyboardMarkup(inline_keyboard=answer, resize_keyboard=True)
                await message.reply(f"Найдена инструкция:\n"
                                    f"Название: {instruction[1]}\n"
                                    f"Содержание: {instruction[2]}\n"
                                    f"Автор: @{instruction[4]}", reply_markup=keyboard_answer)
        else:
            await message.reply("По вашему запросу ничего не найдено.")
        await state.clear()