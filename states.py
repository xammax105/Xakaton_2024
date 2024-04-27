from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


# ввод капчи
class EnterCapthca(StatesGroup):
    entering_captcha = State()


# хуй знает
class RasStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_password = State()
    waiting_for_instructions = State()
    waiting_for_tegs = State()
    waiting_for_answer = State()
    waiting_for_title = State()
    waiting_for_confirm = State()
    processing = State()
    waiting_for_button = State()
    waiting_for_new_answer = State()
    waiting_for_new_instract = State()
    waiting_for_delete = State()
    waiting_for_tag_search = State()
    waiting_for_administr_new = State()
    waiting_for_administr_del = State()
