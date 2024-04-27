import ast
import asyncio
import json
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardBuilder, \
    ReplyKeyboardMarkup

from config import TOKEN
import keyboard as kb
from states import *
import sqlite3
import random
from captcha.image import ImageCaptcha


# создание базы
def create_database(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS Users (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        instructions_rating INTEGER,
        answers_rating INTEGER,
        FOREIGN KEY (instructions_rating) REFERENCES Ranks(ID),
        FOREIGN KEY (answers_rating) REFERENCES Ranks(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Admins (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        user INTEGER,
        login TEXT,
        password TEXT,
        FOREIGN KEY (user) REFERENCES Users(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Tags (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        name TEXT
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Subscribes (
        user INTEGER,
        tags INTEGER,
        FOREIGN KEY (user) REFERENCES Users(ID),
        FOREIGN KEY (tags) REFERENCES Tags(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Instructions (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        is_active INT,
        author TEXT,
        addition_date TEXT,
        tags TEXT,
        -- FOREIGN KEY (author) REFERENCES Users(ID),
        FOREIGN KEY (tags) REFERENCES Tags(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Answers (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        content INT,
        is_active INT,
        author INT,
        addition_date TEXT,
        instruction_id INT,
        FOREIGN KEY (author) REFERENCES Users(ID),
        FOREIGN KEY (instruction_id) REFERENCES Instructions(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS InstructionsVotes (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        user INTEGER,
        instruction_id INTEGER,
        FOREIGN KEY (user) REFERENCES Users(ID),
        FOREIGN KEY (instruction_id) REFERENCES Instructions(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS AnswersVotes (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        user INTEGER,
        answer_id INTEGER,
        FOREIGN KEY (user) REFERENCES Users(ID),
        FOREIGN KEY (answer_id) REFERENCES Answers(ID)
    );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Ranks (
        ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        sphere TEXT,
        name TEXT
    );""")


# добавление юзера в базу
def add_user(user_id, instructions, answers, notifications, cur, con):
    last_id = cur.execute('SELECT MAX (id) FROM Users').fetchone()

    if last_id[0] is None:
        id = 1
    else:
        id = last_id[0] + 1

    cur.execute(
        'INSERT INTO Users VALUES ("{}","{}", "{}", "{}", "{}")'.format(
            id, user_id, instructions, answers, notifications))
    con.commit()

    cur.execute("SELECT * FROM Users;")
    one_result = cur.fetchall()
    for i in one_result:
        print(i)


# Создаем объект ImageCaptcha
captcha_generator = ImageCaptcha(width=200, height=100)


# Функция для генерации случайной капчи
def generate_captcha():
    random_digits = ''.join(random.choices('0123456789', k=4))
    image_data = captcha_generator.generate(random_digits)
    return image_data, random_digits


def get_users_instructions_count(cur):
    cur.execute("""
        SELECT  Users.user_id, COUNT(Instructions.ID) AS num_instructions
        FROM Users
        LEFT JOIN Instructions ON Users.user_id = Instructions.author_id
        GROUP BY Users.user_id
        ORDER BY num_instructions DESC;
    """)
    return cur.fetchall()


def get_users_answers_count(cur):
    cur.execute("""
        SELECT Users.user_id, COUNT(Answers.ID) AS num_answers
        FROM Users
        LEFT JOIN Answers ON Users.user_id= Answers.author
        GROUP BY Users.user_id
        ORDER BY num_answers DESC;
        """)
    return cur.fetchall()


def add_instruction(title, content, active, name, user_id, date, hashtags, notified, cur, con):
    last_id = cur.execute('SELECT MAX(id) FROM Instructions').fetchone()

    if last_id[0] is None:
        id = 1
    else:
        id = last_id[0] + 1

    cur.execute(
        'INSERT INTO Instructions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (id, title, content, active, name, user_id, date, hashtags, notified)
    )
    con.commit()
    print("Инструкция добавлена в базу")


def add_answer(content, is_active, author, addition_date, instruction_id, cur, con):
    last_id = cur.execute('SELECT MAX(id) FROM Answers').fetchone()

    if last_id[0] is None:
        id = 1
    else:
        id = last_id[0] + 1

    cur.execute(
        'INSERT INTO Answers VALUES (?, ?, ?, ?, ?, ?)',
        (id, content, is_active, author, addition_date, instruction_id)
    )
    con.commit()
    print("Ответ добавлен в базу")


# получаем хэштеги из статей
def get_hashtags(cur):
    cur.execute("select distinct tags from Instructions where is_active = 1")
    res = cur.fetchall()
    tags = set()

    for row in res:
        tags_str = row[0]
        try:
            # Пробуем преобразовать строку в список
            tags_list = ast.literal_eval(tags_str)
            if isinstance(tags_list, list):
                for tag in tags_list:
                    tags.add(tag)
        except (ValueError, SyntaxError):
            # В случае ошибки просто добавляем строку в множество
            tags.add(tags_str)

    return tags


async def send_notifications(cur, con, bot):
    while True:
        # Получение новых записей из таблицы Instructions
        cur.execute("SELECT tags FROM Instructions WHERE notified = 0 and is_active = 1")
        instructions = cur.fetchall()

        for instruction in instructions:
            tags = instruction[0]
            tag = tags.strip('[').strip(']').strip("'")
            # Получение подписчиков для каждого тега
            cur.execute(f"SELECT user FROM Subscribes WHERE tags LIKE '%{tag}%'")
            subscribers = cur.fetchall()

            # Отправка уведомлений подписчикам
            for subscriber in subscribers:
                user_id = subscriber[0]
                await bot.send_message(user_id, f"💬 Новая запись с тегом #{tag} добавлена!")

            # Пометить запись как уже отправленную
            cur.execute(f"UPDATE Instructions SET notified = 1 WHERE tags LIKE '%{tag}%'")
            con.commit()

        await asyncio.sleep(5)


async def send_next_instruction(user_id, bot, instructions_data):
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
                    types.InlineKeyboardButton(text="Ответить", callback_data=f"reply_{instruction_id}"),
                    types.InlineKeyboardButton(text="Посмотреть ответы", callback_data=f"viewAnswer_{instruction_id}"),
                    types.InlineKeyboardButton(text="Пропустить", callback_data="skip")
                ],
                [types.InlineKeyboardButton(text="Отдать голос", callback_data="vote_question")]
            ]

            keyboard_answer = types.InlineKeyboardMarkup(inline_keyboard=answer, resize_keyboard=True,
                                                         input_field_placeholder="Ты кем будешь, вацок")

            if content.isdigit():
                message_id = int(content)
                await bot.copy_message(user_id, from_chat_id=author_id, message_id=message_id, caption=title)
                await bot.send_message(user_id,
                                       f"{instruction_id}\n author @{username} \nКоличество голосов {votes}",
                                       reply_markup=keyboard_answer)
            else:

                await bot.send_message(user_id, f"{instruction_id} \n{title}: {content}\n Количество голосов {votes}",
                                       reply_markup=keyboard_answer)
        else:
            await bot.send_message(user_id, "Вы просмотрели все инструкции.")
    else:
        await bot.send_message(user_id, "Начните сначала, чтобы просмотреть инструкции.")
