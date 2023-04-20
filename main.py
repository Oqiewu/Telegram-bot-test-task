from decouple import config
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from pyowm import OWM
from pyowm.utils.config import get_default_config
import requests
import random
import os

#Инициализация бота
bot = Bot(token=config('api_key'))
dp = Dispatcher(bot, storage=MemoryStorage())

#Конфиг для погодной функции
config_dict = get_default_config()
config_dict['language'] = 'ru'
owm = OWM(config('weather_api'))

#Состояния
class SelectButton(StatesGroup):
    wait_button = State()
    wait_town = State()
    wait_currency = State()
    wait_amount = State()
    wait_poll_question = State()
    wait_options = State()
    wait_corrent_option = State()
    wait_anonimus = State()
    wait_chat_id = State()

#Команда старт. спрашивает, что конкретно нужно от бота.
@dp.message_handler(Text(equals='⬅'))
@dp.message_handler(state=SelectButton.wait_button)
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    weather_button = types.KeyboardButton(text="Погода 🌤")
    keyboard.add(weather_button)
    
    currency_converter_button = types.KeyboardButton(text="Конвертатор валют 💲")
    keyboard.add(currency_converter_button)

    random_picture_button = types.KeyboardButton(text="Случайная картинка 🏞")
    keyboard.add(random_picture_button)

    polls_button = types.KeyboardButton(text="Создать опрос ❓")
    keyboard.add(polls_button)
    
    await state.finish()
    await message.answer("Что вас интересует?", reply_markup=keyboard)

#Погода. Уточняет город, в котором нужно узнать погоду.
@dp.message_handler(Text(equals='Погода 🌤'))
async def entry_weather_message(message: types.Message, state: FSMContext):

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    await message.answer('Введите свой город.', reply_markup=keyboard_to_main)
    await state.set_state(SelectButton.wait_town.state)

#Погода. Отправляет температуру в указаном городе.
@dp.message_handler(state=SelectButton.wait_town)
async def track_weather(message: types.Message, state: FSMContext):
    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    if message.text != '⬅':
        try:
            mgr = owm.weather_manager()
            observation = mgr.weather_at_place(message.text)
            w = observation.weather

            await message.answer(f"{message['text']}: {round(w.temperature('celsius')['temp'])}°C")
            await state.set_state(SelectButton.wait_button.state)
        except:
            await message.answer('Введите корректное название города!', reply_markup=keyboard_to_main)
            await state.set_state(SelectButton.wait_town.state)
    else:
        await state.set_state(SelectButton.wait_button)

#Конвертатор валют. уточняет пару для конвертрования
@dp.message_handler(Text(equals='Конвертатор валют 💲'))
async def converter(message: types.Message, state:FSMContext):

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    await message.answer('Введите пару используя коды валют. Например: USD RUB', reply_markup=keyboard_to_main)
    await state.set_state(SelectButton.wait_currency.state)

#Конвертатор валют. На основании выбранной пары создаёт переменные для подсчёта и уточняет сумму для конвертации
@dp.message_handler(state=SelectButton.wait_currency)
async def amount(message: types.Message, state: FSMContext):
    global currency_1_code, currency_1_value, currency_2_code, currency_2_value

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)
    
    if message.text != '⬅':
        try:
            currency_url = f"https://open.er-api.com/v6/latest/USD"
            response = requests.get(currency_url)
            data = response.json()
            couple = data['rates']

            for i in couple.keys():
                if i == str(message['text'][0:3:1]):
                    currency_1_code = str(message['text'][0:3:1])
                    currency_1_value = couple[str(message['text'][0:3:1])]
                if i == str(message['text'][4::1]):
                    currency_2_code = str(message['text'][4::1])
                    currency_2_value = couple[str(message['text'][4::1])]

            await message.answer(f'Введите сумму {currency_1_code}', reply_markup=keyboard_to_main)
            await state.set_state(SelectButton.wait_amount.state)

        except:
            await message.answer('Введите корректную пару', reply_markup=keyboard_to_main)
            await state.set_state(SelectButton.wait_currency.state)
    else:
        await state.set_state(SelectButton.wait_button)

#Конвертация валют. Конвертирует нужную валюту и отправляет пользователю сообщение с информацией
@dp.message_handler(state=SelectButton.wait_amount)
async def converter(message: types.Message, state: FSMContext):
    if message.text != '⬅':    
        try:
            amount = int(message['text'])
            amount = amount / currency_1_value
            amount = round(amount * currency_2_value, 2)

            await message.answer(f'{message["text"]} {currency_1_code} = {amount} {currency_2_code}')
            await state.set_state(SelectButton.wait_button.state)
        except:
            await message.answer('Введите корректную сумму!')
            await state.set_state(SelectButton.wait_amount.state)


#Отправление случайной картинки
@dp.message_handler(Text(equals="Случайная картинка 🏞"))
async def send_random_image(message: types.Message):
    photo = open('images/' + random.choice(os.listdir('images')), 'rb')

    await bot.send_photo(message.from_user.id, photo)
    
#Начальная функция для создания опроса
@dp.message_handler(Text(equals="Создать опрос ❓"))
async def entry_create_poll(message: types.Message, state: FSMContext):
    global type_quiz

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    type_quiz = 'quiz'
    if message.text != '⬅':
        await message.answer('1. Введите вопрос для опроса', reply_markup=keyboard_to_main)
        await state.set_state(SelectButton.wait_poll_question)
    else:
        await state.set_state(SelectButton.wait_button)

#Устанавливает вопрос для опроса и спрашивает варианты ответа
@dp.message_handler(state=SelectButton.wait_poll_question)
async def question_for_poll(message: types.Message, state: FSMContext):
    global question_quiz

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    question_quiz = message.text

    if message.text != '⬅':
        await message.answer('2. Введите варианты ответа в разных строках', reply_markup=keyboard_to_main)
        await state.set_state(SelectButton.wait_options)
    else:
        await state.set_state(SelectButton.wait_button)


#Устанавливает варианты ответа и спрашивает верный вариант
@dp.message_handler(state=SelectButton.wait_options)
async def options_for_poll(message: types.Message, state: FSMContext):
    global options_quiz

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    options_quiz = message.text.split('\n')

    if message.text != '⬅':
        await message.answer('3. Какой вариант будет правильным? (Введите цифру)', reply_markup=keyboard_to_main)
        await state.set_state(SelectButton.wait_corrent_option)
    else:
        await state.set_state(SelectButton.wait_button)

#Устанавливает верный вариант и спрашивает будет ли функция анонимной
@dp.message_handler(state=SelectButton.wait_corrent_option)
async def correct_option_for_poll(message: types.Message, state: FSMContext):
    global correct_option

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    if message.text != '⬅':
        try:
            correct_option = int(message.text)
            
            await message.answer('4. Будет ли опрос анонимным? (Да или Нет)', reply_markup=keyboard_to_main)
            await state.set_state(SelectButton.wait_anonimus)
        except:
            await message.answer('Введите цифру!')
            await state.set_state(SelectButton.wait_corrent_option)
    else:
        await state.set_state(SelectButton.wait_button)

#Устанавливает анонимность и спрашивает ID чата, в который нужно прислать опрос
@dp.message_handler(state=SelectButton.wait_anonimus)
async def is_anonimus_poll(message: types.Message, state: FSMContext):
    global anonimus

    keyboard_to_main = types.ReplyKeyboardMarkup(resize_keyboard=True)
    left_button = types.KeyboardButton('⬅')
    keyboard_to_main.add(left_button)

    if message.text != '⬅':
        if message.text.lower == 'да' or message.text.lower == 'нет':
            anonimus = message.text
            if anonimus.lower() == 'да':
                anonimus = True
            elif anonimus.lower() == 'нет':
                anonimus = False
        else:
            await message.answer('Введите "Да" или "Нет"!')
            await state.set_state(SelectButton.wait_anonimus)

        await message.answer('5. Введите ID чата в который нужно отправить опрос с тире перед ID, Например: -100200300', reply_markup=keyboard_to_main)
        await state.set_state(SelectButton.wait_chat_id)
    else:
        await state.set_state(SelectButton.wait_button)
    

#Отправляет опрос, если всё указано верно
@dp.message_handler(state=SelectButton.wait_chat_id)
async def send_poll(message: types.Message, state: FSMContext):
    if message.text != '⬅':
        try:
            chat_id = message.text

            await bot.send_poll(chat_id=chat_id,
                            question=question_quiz,
                            options=options_quiz,
                            correct_option_id=correct_option,
                            is_anonymous=anonimus
                            )
            state.set_state(SelectButton.wait_button.state)
        except:
            await message.answer('Введите корректный ID чата!')
            await state.set_state(SelectButton.wait_chat_id)
    else:
        await state.set_state(SelectButton.wait_button)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)