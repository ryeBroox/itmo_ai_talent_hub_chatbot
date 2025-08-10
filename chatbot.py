import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
import requests
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pdfplumber

parsed_data = None

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option('prefs', {
        "download.default_directory": os.getcwd(), # Скачивает в текущую директорию
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True # Открывать PDF вне браузера
    })

    # Укажите путь к chromedriver
    service = Service('path_to_chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def download_pdf(driver, url):
    driver.get(url)

    # Используйте селектор или метод, чтобы найти и кликнуть на кнопку загрузки PDF
    try:
        download_button = driver.find_element(By.LINK_TEXT, "Скачать учебный план")
        download_button.click()
        time.sleep(5)  # Подождите, пока завершится загрузка
    except Exception as e:
        print("Ошибка при нажатии на кнопку:", str(e))

def parse_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]  # Предполагаем, что информация на первой странице
        parsed_data = page.extract_table()

urls = [
    "https://abit.itmo.ru/program/master/ai",
    "https://abit.itmo.ru/program/master/ai_product"
]

driver = setup_driver()

for url in urls:
    download_pdf(driver, url)
    
    # Проверяем, что файл загружен
    pdf_file = "учебный_план.pdf"  # Имя файла должно совпадать с загружаемым
    if os.path.exists(pdf_file):
        parse_pdf(pdf_file)
        os.remove(pdf_file)  # Удаляем после обработки

driver.quit()

API_TOKEN = 'TELEGRAM_BOT_TOKEN'
DEESEEK_API_URL = 'https://api.deepseek.com/generate'  # Этот URL нужно заменить на фактический URL API

# Настроим логирование
logging.basicConfig(level=logging.INFO)

# Создание бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я помогу вам выбрать образовательную программу. Пожалуйста, расскажите о вашем фоне и интересах.")

# Обработчик текстовых сообщений
@dp.message_handler()
async def handle_message(message: types.Message):
    user_input = message.text
    
    # Формируем промпт для LLM
    prompt = f"""
    Пользователь написал: {user_input}
    Данные магистратур: {parsed_data}
    Пожалуйста, порекомендуйте подходящие дисциплины и дайте информацию об образовательных программах.
    """
    
    # Вызов API DeepSeek
    response = requests.post(DEESEEK_API_URL, json={'prompt': prompt})
    
    if response.status_code == 200:
        result = response.json().get('response', 'Извините, я не могу помочь с этой темой.')
        await message.reply(result)
    else:
        await message.reply("Произошла ошибка при обращении к LLM. Пожалуйста, попробуйте позже.")

# Запуск лонг-поллинга
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
