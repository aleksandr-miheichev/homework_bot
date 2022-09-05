class ConnectionErrorException(Exception):
    """Возникла ошибка подключения (сбой сети, ошибка DNS)."""


class URLRequiredException(Exception):
    """Некорректный URL-адрес запроса."""


class TimeoutException(Exception):
    """Время запроса истекло."""


class JSONDecodeErrorException(Exception):
    """Наличие проблемы с декодированием данных в JSON."""


class HTTPErrorException(Exception):
    """Сервер вернул код ошибки HTTP в ответ на сделанный запрос."""

class DenyServiceErrorException(Exception):
    """Отказ в обслуживании от ендпоинта."""
