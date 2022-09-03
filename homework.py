import logging
import os
import requests
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from http.client import OK
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
VARIABLES = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
sent_message = 'Сообщение: "{}" успешно отправлено в чат {}'
unsent_message = 'Сообщение "{}" не отправлено в чат из-за ошибки: {}'
request_error = (
    'Ошибка "{}" при запросе к API c эндпоинтом "{}", заголовком "{}" и '
    'параметрами "{}"'
)
invalid_response_code = (
    'Запрос с сервера c эндпоинтом "{}", заголовком "{}" и параметрами "{}" '
    'вернулся с кодом ответа: {}'
)
invalid_response_type = (
    'Тип данных ответа API "{}" отличается от необходимого - словарь'
)
MISSING_KEY = 'Отсутствие ключа "homeworks" в словаре ответа API'
wrong_datatype_by_key = (
    'Тип данных ответа API под ключом "homeworks": "{}" отличается от '
    'необходимого - список'
)
unknown_status = (
    'Неизвестный статус домашней работы, обнаруженный в ответе API: {}'
)
changed_verdict = 'Изменился статус проверки работы "{}". {}'
MISSING_ENVIRONMENT_VARIABLES = (
    'Отсутствуют переменные окружения необходимые для работы программы'
)
JSON_ERROR = 'Ошибка декодирования информации от сервера в JSON формат'
missing_token = 'Отсутствует токен {} для работы программы'
program_error = 'Сбой в работе программы: {}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            sent_message.format(message, TELEGRAM_CHAT_ID))
    except Exception as error:
        logging.exception(unsent_message.format(message, error))


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса и возвращает ответ API."""
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.ConnectionError as error:
        raise requests.ConnectionError(
            request_error.format(error, ENDPOINT, HEADERS, params)
        )
    except requests.URLRequired as error:
        raise requests.URLRequired(
            request_error.format(error, ENDPOINT, HEADERS, params)
        )
    except requests.Timeout as error:
        raise requests.Timeout(
            request_error.format(error, ENDPOINT, HEADERS, params)
        )
    if homework_statuses.status_code != OK:
        status_code = homework_statuses.status_code
        raise requests.HTTPError(
            invalid_response_code.format(
                ENDPOINT,
                HEADERS,
                params,
                status_code
            )
        )
    try:
        statuses = homework_statuses.json()
    except requests.exceptions.JSONDecodeError:
        raise requests.exceptions.JSONDecodeError(JSON_ERROR)
    return statuses


def check_response(response):
    """Проверяет ответ API на корректность.
    Возвращает список домашних работ.
    """
    if not (issubclass(type(response), dict) or type(response) is dict):
        raise TypeError(invalid_response_type.format(type(response)))
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(MISSING_KEY)
    if not (issubclass(type(homeworks), list) or type(homeworks) is list):
        raise TypeError(wrong_datatype_by_key.format(type(homeworks)))
    return homeworks


def parse_status(homework):
    """Извлекает из конкретной домашней работы вердикт по этой работе."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(unknown_status.format(status))
    verdict = HOMEWORK_VERDICTS[status]
    return changed_verdict.format(name, verdict)


def check_tokens():
    """Проверяет доступность переменных окружения необходимых для работы бота.
    Если отсутствует хотя бы одна переменная — возвращает False, иначе — True.
    """
    for variable in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if not globals()[variable]:
            logging.exception(missing_token.format(variable))
            return False
        return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical(MISSING_ENVIRONMENT_VARIABLES, exc_info=True)
        raise NameError(MISSING_ENVIRONMENT_VARIABLES)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = program_error.format(error)
            logging.exception(program_error.format(error))
            try:
                if message:
                    send_message(bot, message)
            except Exception:
                raise
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s '
               '- (%(filename)s).%(funcName)s(%(lineno)d) '
               '- %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            RotatingFileHandler(
                __file__ + '.log',
                maxBytes=50000000,
                backupCount=5
            ),
            logging.StreamHandler()
        ],
        encoding='utf-8'
    )
    logger = logging.getLogger(__name__)
    main()

# "сбой сети"
# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     ReqEx = requests.RequestException
#     class TestReq(TestCase):
#         @mock.patch('requests.get')
#         def test_raised(self, rq_get):
#             rq_get.side_effect = mock.Mock(side_effect=ReqEx('testing'))
#             main()
#     uni_main()

# "отказ сервера"
# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     JSON = {'error': 'testing'}
#     class TestReq(TestCase):
#         @mock.patch('requests.get')
#         def test_error(self, rq_get):
#             resp = mock.Mock()
#             resp.json = mock.Mock(return_value=JSON)
#             rq_get.return_value = resp
#             main()
#     uni_main()

#  неожиданный код-возврата
# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     class TestReq(TestCase):
#         @mock.patch('requests.get')
#         def test_error(self, rq_get):
#             resp = mock.Mock()
#             resp.status_code = 333
#             rq_get.return_value = resp
#             main()
#     uni_main()

# неожиданный статус для домашки
# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     JSON = {'homeworks': [{'homework_name': 'test', 'status': 'test'}]}
#     class TestReq(TestCase):
#         @mock.patch('requests.get')
#         def test_error(self, rq_get):
#             resp = mock.Mock()
#             resp.json = mock.Mock(return_value=JSON)
#             rq_get.return_value = resp
#             main()
#     uni_main()

# некорректный json
# if __name__ == '__main__':
#     from unittest import TestCase, mock, main as uni_main
#     JSON = {'homeworks': 1}
#     class TestReq(TestCase):
#         @mock.patch('requests.get')
#         def test_error(self, rq_get):
#             resp = mock.Mock()
#             resp.json = mock.Mock(return_value=JSON)
#             rq_get.return_value = resp
#             main()
#     uni_main()