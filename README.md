# Чат-бот для проверки статуса домашних заданий в Практикуме

## Содержание

- [Описание проекта](#описание-проекта)
- [Технологический стек](#технологический-стек)
- [Как развернуть проект](#как-развернуть-проект)
- [Шаблон наполнения файла .env](#шаблон-наполнения-файла-env)
- [Запуск приложения](#запуск-приложения)
- [Над проектом работал](#над-проектом-работал)

---

### Описание проекта:

Telegram-бот, который будет обращаться к API сервиса Практикум.Домашка и
узнавать статус вашей домашней работы: взята ли ваша домашка в ревью, проверена
ли она, а если проверена — то принял её ревьюер или вернул на доработку.

#### Что может данный чат-бот:

- раз в 10 минут опрашивать API сервиса Практикум.Домашка и проверять статус
  отправленной на ревью домашней работы;
- при обновлении статуса анализировать ответ API и отправлять вам
  соответствующее уведомление в Telegram;
- логировать свою работу и сообщать вам о важных проблемах сообщением в
  Telegram.

---

### Технологический стек:

- [![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
- [python-telegram-bot](https://docs.python-telegram-bot.org/en/stable/index.html)
- [Requests](https://requests.readthedocs.io/en/latest/)

---

### Как развернуть проект:

Клонировать репозиторий и перейти в него в терминале используя команду

```bash
cd
```

```bash
git clone git@github.com:aleksandr-miheichev/homework_checker_telegram_bot.git
```

Создать и активировать виртуальное окружение:

```bash
python -m venv venv
```

```bash
source venv/Scripts/activate
```

Установить зависимости из файла requirements.txt:

```bash
pip install -r requirements.txt
```

---

### Шаблон наполнения файла .env:

```
PRACTICUM_TOKEN=y9_AgAAAAAJtz4kAAYckQAAAADNWT6s7IrQ_VYgSS-g-zs6YJ2lmgxt7Xs
TELEGRAM_TOKEN=1234567897:AAE_tKY1c2NpQmnjNkBl7vLZiEQ5OXj9m90
TELEGRAM_CHAT_ID=123456789
```

---

### Запуск приложения:

Чтобы запустить модуль, необходимо в терминале использовать команду:

```bash
python .\homework.py
```

---

### Над проектом работал:

- [Михеичев Александр](https://github.com/aleksandr-miheichev)
