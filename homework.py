import logging
import os
import requests
import time

from dotenv import load_dotenv
from http.client import OK
from logging.handlers import RotatingFileHandler
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
EMPTY_MESSAGE = ''
logging.basicConfig(
    format='%(asctime)s - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) '
           '- %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='UTF-8'
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) '
    '- %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            f'Сообщение {message} успешно отправлено в чат {TELEGRAM_CHAT_ID}'
        )
    except Exception as error:
        logging.error(f'Сообщение не отправлено из-за ошибки: {error}')
        raise Exception(f'Сообщение не отправлено из-за ошибки: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса и возвращает ответ API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise Exception(f'Ошибка при запросе к API: {error}')
    if homework_statuses.status_code != OK:
        status_code = homework_statuses.status_code
        logging.error(
            f'Запрос с сервера вернулся с кодом ответа: {status_code}'
        )
        raise Exception(
            f'Запрос с сервера вернулся с кодом ответа: {status_code}'
        )
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность.
    Возвращает список домашних работ.
    """
    if type(response) is not dict:
        logger.error(
            f'Тип данных ответа API: {type(response)} отличается от '
            f'необходимого - словарь'
        )
        raise TypeError(
            f'Тип данных ответа API: {type(response)} отличается от '
            f'необходимого - словарь'
        )
    try:
        homework_list = response['homeworks']
    except KeyError:
        logger.error('Отсутствие ключа "homeworks" в словаре ответа API')
        raise KeyError('Отсутствие ключа "homeworks" в словаре ответа API')
    if len(homework_list) == 0:
        logger.info('Домашних работ нет')
    if type(homework_list) is not list:
        logger.error(
            'Тип данных ответа API под ключом "homeworks" - список'
        )
        raise TypeError(
            'Тип данных ответа API под ключом "homeworks" - список'
        )
    return homework_list


def parse_status(homework):
    """Извлекает из конкретной домашней работы статус этой работы.
    Возвращает строку со статусом работы.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        logger.error('Отсутствие ключа "homework_name" в словаре ответа API')
        raise KeyError('Отсутствие ключа "homework_name" в словаре ответа API')
    if 'status' not in homework:
        logger.error('Отсутствие ключа "status" в словаре ответа API')
        raise KeyError('Отсутствие ключа "status" в словаре ответа API')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(
            'Недокументированный статус домашней работы, обнаруженный в '
            f'ответе API: {homework_status}'
        )
        raise KeyError(
            'Недокументированный статус домашней работы, обнаруженный в '
            f'ответе API: {homework_status}'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения необходимых для работы бота.
    Если отсутствует хотя бы одна переменная — возвращает False, иначе — True.
    """
    for token in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if not token:
            return False
        return True


def main():
    """Основная логика работы бота."""
    global EMPTY_MESSAGE
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical(
            'Отсутствуют переменные окружения необходимые для работы программы'
        )
        raise Exception(
            'Отсутствуют переменные окружения необходимые для работы программы'
        )
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_timestamp = response.get('current_date')
            if (
                    (type(homeworks) is list)
                    and (len(homeworks) > 0)
                    and homeworks
                    and parse_status(homeworks[0]) != EMPTY_MESSAGE
            ):
                send_message(bot, parse_status(homeworks[0]))
                EMPTY_MESSAGE = parse_status(homeworks[0])
            elif 'Новых статусов домашних работ нет' != EMPTY_MESSAGE:
                send_message(bot, 'Новых статусов домашних работ нет')
                EMPTY_MESSAGE = 'Новых статусов домашних работ нет'
                time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            if message != EMPTY_MESSAGE:
                send_message(bot, message)
                EMPTY_MESSAGE = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
