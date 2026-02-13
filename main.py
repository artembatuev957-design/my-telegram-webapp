import telebot
import requests
import json
from currency_converter import CurrencyConverter
from telebot import types

# Инициализация бота и конвертера
# ТОКЕН И API КЛЮЧ (Рекомендуется хранить их в переменных окружения)
TOKEN = '8452228553:AAHhIdVrTxs7R2AcmRg1m-0CU0J3YEguoiI'
WEATHER_API = '5c9a7eb45c7040dfef95ed49a576f363'

bot = telebot.TeleBot(TOKEN)
currency = CurrencyConverter()

# Временное хранилище для сумм (чтобы данные разных юзеров не смешивались)
user_data = {}


# --- ПРОВЕРКА НА КОМАНДУ ---
def is_command(message):
    """Проверяет, является ли сообщение новой командой, чтобы прервать текущий шаг"""
    if message.text and message.text.startswith('/'):
        bot.send_message(message.chat.id, "Операция отменена. Выполняю новую команду...")
        bot.process_new_messages([message])
        return True
    return False


# --- ОБРАБОТКА КОМАНД ---

@bot.message_handler(commands=['start', 'hello'])
def main_start(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}! Я готов к работе.')


@bot.message_handler(commands=['help'])
def main_help(message):
    help_text = (
        "Доступные команды:\n"
        "/weather - узнать погоду\n"
        "/valute - конвертер валют\n"
        "/site - ссылка на видео\n"
        "/love - секретное сообщение"
    )
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['site', 'сайт'])
def site(message):
    bot.send_message(message.chat.id, 'Вот ссылка: https://youtu.be/dQw4w9WgXcQ')


@bot.message_handler(commands=['love'])
def love_command(message):
    bot.send_message(message.chat.id, 'Я люблю свою заю <3 @mashkissr')


# --- БЛОК ПОГОДЫ ---

@bot.message_handler(commands=['weather'])
def weather_request(message):
    bot.send_message(message.chat.id, 'В каком городе ты сейчас? (Введите название)')
    bot.register_next_step_handler(message, get_weather)


def get_weather(message):
    if is_command(message): return  # Если ввели команду вместо города

    city = message.text.strip().lower()
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric'

    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            temp = data['main']['temp']
            bot.reply_to(message, f'Сейчас в городе {city.capitalize()}: {temp}°C')
        else:
            bot.reply_to(message, 'Город не найден. Попробуйте еще раз: /weather')
    except Exception:
        bot.reply_to(message, 'Ошибка связи с сервисом погоды.')


# --- БЛОК КОНВЕРТЕРА ВАЛЮТ ---

@bot.message_handler(commands=['valute'])
def valute_request(message):
    bot.send_message(message.chat.id, 'Введите сумму для конвертации:')
    bot.register_next_step_handler(message, process_sum)


def process_sum(message):
    if is_command(message): return

    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0:
            bot.send_message(message.chat.id, 'Сумма должна быть больше нуля. Введите число:')
            bot.register_next_step_handler(message, process_sum)
            return

        user_data[message.chat.id] = amount

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('RUB -> EUR', callback_data='RUB/EUR')
        btn2 = types.InlineKeyboardButton('RUB -> USD', callback_data='RUB/USD')
        btn3 = types.InlineKeyboardButton('RUB -> JPY', callback_data='RUB/JPY')
        btn4 = types.InlineKeyboardButton('RUB -> GBP', callback_data='RUB/GBP')
        markup.add(btn1, btn2, btn3, btn4)

        bot.send_message(message.chat.id, f'Сумма: {amount}. Выберите валюту:', reply_markup=markup)
    except ValueError:
        bot.send_message(message.chat.id, 'Нужно ввести число (например, 150.50):')
        bot.register_next_step_handler(message, process_sum)


@bot.callback_query_handler(func=lambda call: True)
def callback_converter(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id

    if chat_id not in user_data:
        bot.send_message(chat_id, "Данные устарели. Начните заново: /valute")
        return

    amount = user_data[chat_id]

    if call.data != 'else':
        cur_from, cur_to = call.data.split('/')
        try:
            res = currency.convert(amount, cur_from, cur_to)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f'Результат: {round(res, 2)} {cur_to}\n\nЧтобы посчитать снова, введите /valute'
            )
        except Exception:
            bot.send_message(chat_id, 'Ошибка конвертации этой валюты.')
    else:
        bot.send_message(chat_id, 'Введите валюты через слэш (например, USD/GBP):')
        bot.register_next_step_handler(call.message, custom_currency)


def custom_currency(message):
    if is_command(message): return
    chat_id = message.chat.id

    try:
        cur_from, cur_to = message.text.upper().replace(' ', '').split('/')
        res = currency.convert(user_data[chat_id], cur_from, cur_to)
        bot.send_message(chat_id, f'Результат: {round(res, 2)} {cur_to}')
    except Exception:
        bot.send_message(chat_id, 'Ошибка! Неверный формат. Используйте формат: USD/EUR')


# --- ОБРАБОТКА ОБЫЧНОГО ТЕКСТА И МЕДИА ---

@bot.message_handler(content_types=['photo', 'audio', 'video'])
def handle_media(message):
    bot.reply_to(message, 'Я пока не умею обрабатывать файлы. Присылай текст или команды!')


@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.lower()
    if text == 'привет':
        bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!')
    elif text == 'id':
        bot.reply_to(message, f'Ваш Telegram ID: {message.from_user.id}')
    else:
        bot.reply_to(message, 'Я не знаю такой команды. Напиши /help, чтобы увидеть список возможностей.')


# Запуск
if __name__ == '__main__':
    print('Бот успешно запущен...')
    bot.infinity_polling(none_stop=True)
