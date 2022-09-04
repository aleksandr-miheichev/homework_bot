class ConnectionErrorException(Exception):
    """Возникла ошибка подключения (сбой сети, ошибка DNS)."""

    pass


class URLRequiredException(Exception):
    """Некорректный URL-адрес запроса."""

    pass


class TimeoutException(Exception):
    """Время запроса истекло."""

    pass


class JSONDecodeErrorException(Exception):
    """Наличие проблемы с декодированием данных в JSON."""

    pass


class HTTPErrorException(Exception):
    """Сервер вернул код ошибки HTTP в ответ на сделанный запрос."""

    pass
