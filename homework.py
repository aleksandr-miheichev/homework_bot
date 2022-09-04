import logging
import os
import requests
import telegram
import time

from dotenv import load_dotenv
from exception import (
    ConnectionErrorException,
    JSONDecodeErrorException,
    HTTPErrorException,
    TimeoutException,
    URLRequiredException
)
from http.client import OK
from logging.handlers import RotatingFileHandler

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
NO_VERDICTS = 'Новые вердикты по работам отсутствуют'
NO_ERROR = 'Новые ошибки при работе программы отсутствуют'
START_SENDING_MESSAGE = 'Началась отправка сообщения "{}" в чат {} Telegram'
API_REQUEST_START = (
    'Начата отправка запроса к API c эндпоинтом "{ENDPOINT}", '
    'заголовком "{HEADERS}" и параметрами "{params}"'
)
SENT_MESSAGE = 'Сообщение: "{}" успешно отправлено в чат {}'
UNSENT_MESSAGE = 'Сообщение "{}" не отправлено в чат из-за ошибки: {}'
REQUEST_ERROR = (
    'Ошибка "{}" при запросе к API c эндпоинтом "{}", заголовком "{}" и '
    'параметрами "{}"'
)
INVALID_RESPONSE_CODE = (
    'Запрос с сервера c эндпоинтом "{}", заголовком "{}" и параметрами "{}" '
    'вернулся с кодом ответа: {}'
)
INVALID_RESPONSE_TYPE = (
    'Тип данных ответа API "{}" отличается от необходимого - словарь'
)
MISSING_KEY = 'Отсутствие ключа "homeworks" в словаре ответа API'
WRONG_DATATYPE_BY_KEY = (
    'Тип данных ответа API под ключом "homeworks": "{}" отличается от '
    'необходимого - список'
)
UNKNOWN_STATUS = (
    'Неизвестный статус домашней работы, обнаруженный в ответе API: {}'
)
CHANGED_VERDICT = 'Изменился статус проверки работы "{}". {}'
MISSING_ENVIRONMENT_VARIABLES = (
    'Отсутствуют переменные окружения необходимые для работы программы'
)
JSON_ERROR = 'Ошибка декодирования информации от сервера в JSON формат'
MISSING_TOKEN = 'Отсутствует токен {} для работы программы'
PROGRAM_ERROR = 'Сбой в работе программы: {}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            START_SENDING_MESSAGE.format(message, TELEGRAM_CHAT_ID))
    except telegram.error.TelegramError as error:
        logging.exception(UNSENT_MESSAGE.format(message, error))


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса и возвращает ответ API."""
    params = {'from_date': current_timestamp}
    data = {
        'ENDPOINT': ENDPOINT,
        'params': params,
        'HEADERS': HEADERS,
    }
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        logging.info(API_REQUEST_START.format(**data))
        if homework_statuses.status_code != OK:
            status_code = homework_statuses.status_code
            raise HTTPErrorException(
                INVALID_RESPONSE_CODE.format(
                    ENDPOINT,
                    HEADERS,
                    params,
                    status_code
                )
            )
        try:
            statuses = homework_statuses.json()
        except requests.exceptions.JSONDecodeError:
            raise JSONDecodeErrorException(JSON_ERROR)
    except requests.ConnectionError as error:
        raise ConnectionErrorException(
            REQUEST_ERROR.format(error, ENDPOINT, HEADERS, params)
        )
    except requests.URLRequired as error:
        raise URLRequiredException(
            REQUEST_ERROR.format(error, ENDPOINT, HEADERS, params)
        )
    except requests.Timeout as error:
        raise TimeoutException(
            REQUEST_ERROR.format(error, ENDPOINT, HEADERS, params)
        )
    return statuses


def check_response(response):
    """Проверяет ответ API на корректность.
    Возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError(INVALID_RESPONSE_TYPE.format(type(response)))
    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(MISSING_KEY)
    if not isinstance(homeworks, list):
        raise TypeError(WRONG_DATATYPE_BY_KEY.format(type(homeworks)))
    return homeworks


def parse_status(homework):
    """Извлекает из конкретной домашней работы вердикт по этой работе."""
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status))
    verdict = HOMEWORK_VERDICTS[status]
    return CHANGED_VERDICT.format(name, verdict)


def check_tokens():
    """Проверяет доступность переменных окружения необходимых для работы бота.
    Если отсутствует хотя бы одна переменная — возвращает False, иначе — True.
    """
    for variable in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if not globals()[variable]:
            logging.exception(MISSING_TOKEN.format(variable))
            return False
        return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical(MISSING_ENVIRONMENT_VARIABLES, exc_info=True)
        raise NameError(MISSING_ENVIRONMENT_VARIABLES)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_report = {'name': homeworks[0]['homework_name']}
            prev_report = {}
            if homeworks:
                current_report.get(
                    'verdict',
                    HOMEWORK_VERDICTS[homeworks[0]['status']]
                )
            else:
                current_report.get('verdict', NO_VERDICTS)
            if current_report != prev_report:
                send_message(bot, parse_status(homeworks[0]))
                logging.info(SENT_MESSAGE.format(
                    parse_status(homeworks[0]),
                    TELEGRAM_CHAT_ID)
                )
                prev_report = current_report.copy()
                current_timestamp = response.get(
                    'current_date',
                    current_timestamp
                )
            else:
                logging.info(NO_VERDICTS)
        except Exception as error:
            message = PROGRAM_ERROR.format(error)
            current_report.get('error', message)
            logging.exception(message)
            if message and current_report != prev_report:
                send_message(bot, message)
                logging.info(SENT_MESSAGE.format(message, TELEGRAM_CHAT_ID))
                prev_report = current_report.copy()
            else:
                logging.info(NO_ERROR)
        finally:
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
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
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
