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