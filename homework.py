import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from exception import (
    ConnectionErrorException,
    DenyServiceErrorException,
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
TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
NO_VERDICTS = 'Новые вердикты по работам отсутствуют'
ERROR = 'Появились новые ошибки при работе программы'
NO_ERROR = 'Новые ошибки при работе программы отсутствуют'
START_SENDING_MESSAGE = 'Началась отправка сообщения "{}" в чат {} Telegram'
API_REQUEST_START = (
    'Начата отправка запроса к API c url "{url}", заголовком "{headers}" и '
    'параметрами "{params}"'
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
DENY_SERVICE = (
    'В ответе ендпоинта содержится ошибка: {error_code} - {error} - '
    '{url} - {params} - {headers}'
)
ERROR_CODES = ('error', 'code')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info(
            START_SENDING_MESSAGE.format(message, TELEGRAM_CHAT_ID))
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logging.exception(UNSENT_MESSAGE.format(message, error))
        return False
    else:
        logging.info(
            SENT_MESSAGE.format(message, TELEGRAM_CHAT_ID))
        return True


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса и возвращает ответ API."""
    params = {'from_date': current_timestamp}
    data = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }
    try:
        logging.info(API_REQUEST_START.format(**data))
        homework_statuses = requests.get(**data)
        status_code = homework_statuses.status_code
        if status_code != OK:
            raise HTTPErrorException(
                INVALID_RESPONSE_CODE.format(
                    ENDPOINT,
                    HEADERS,
                    params,
                    status_code
                )
            )
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
    for error_code in ERROR_CODES:
        if error_code in statuses:
            raise DenyServiceErrorException(
                DENY_SERVICE.format(
                    error_code=error_code,
                    error=statuses[error_code],
                    **data
                )
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
    if status not in VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status))
    return CHANGED_VERDICT.format(name, VERDICTS[status])


def check_tokens():
    """Проверяет доступность переменных окружения необходимых для работы бота.
    Если отсутствует хотя бы одна переменная — возвращает False, иначе — True.
    """
    missed_tokens = [token for token in TOKENS if not globals()[token]]
    if missed_tokens:
        logging.exception(MISSING_TOKEN.format(missed_tokens))
    return not missed_tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(MISSING_ENVIRONMENT_VARIABLES, exc_info=True)
        raise NameError(MISSING_ENVIRONMENT_VARIABLES)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    server_variable = 0
    prev_report = {}
    current_report = {}
    while True:
        try:
            response = get_api_answer(server_variable)
            homeworks = check_response(response)
            if homeworks:
                current_report['key'] = parse_status(homeworks[0])
            else:
                current_report['key'] = NO_VERDICTS
            if (
                    current_report != prev_report
                    and send_message(bot, current_report['key'])
            ):
                prev_report = current_report.copy()
                server_variable = response.get(
                    'current_date',
                    server_variable
                )
            else:
                logging.info(NO_VERDICTS)
        except Exception as error:
            message = PROGRAM_ERROR.format(error)
            current_report['key'] = message
            logging.exception(message)
            if current_report != prev_report and send_message(bot, message):
                logging.info(ERROR)
            else:
                logging.info(NO_ERROR)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s '
               '- (%(filename)s).%(funcName)s(%(lineno)d) '
               '- %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            RotatingFileHandler(
                __file__ + '.log',
                maxBytes=50000000,
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler(sys.stdout)
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

# "неожиданный код-возврата"
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

# "неожиданный статус для домашки"
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

# "некорректный json"
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
