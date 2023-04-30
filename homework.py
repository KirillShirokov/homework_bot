import logging
import os
import time
import sys
from http import HTTPStatus
import requests
from telegram import Bot
from dotenv import load_dotenv
from logging import StreamHandler


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяется доступность переменных окружения."""
    try:
        return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    except Exception:
        logger.debug('Недоступны переменные окружения')


def send_message(bot, message):
    """Отправляется сообщение в телеграм чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.info('Сообщение в ТГ отправлено')


def get_api_answer(timestamp):
    """Делается запрос к эндпоинту."""
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
        return api_answer.json()
    except Exception as error:
        logger.error(f'Ответ API {error}')
    if api_answer.status_code != HTTPStatus.OK:
        logger.error(f'Получен ответ {api_answer.status_code}')


def check_response(response):
    """Проверяется ответ API на соответствие документации."""
    KEY_RESPONSE = 'homeworks'
    if KEY_RESPONSE not in response:
        raise KeyError('Ответ не содержит нужного ключа')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Нет списка в ответе API по ключу homeworks')
    print(response.get('homeworks'))
    if len(response.get('homeworks')) != 0:
        try:
            return response.get('homeworks')[0]
        except Exception as error:
            logger.error(f'Из ответа не получен список работ: {error}')
    else:
        return False


def parse_status(homework):
    """Извлекается статус из конкретной д/р."""
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_VERDICTS[homework_status]
        if homework_status not in HOMEWORK_VERDICTS:
            raise KeyError(f'Ошибка {homework_status}')
        elif homework_name is None:
            raise Exception('Ошибка ответа')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logging.error(f'Ошибка {error}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise SystemExit
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            logger.info('Запрос выполнен')
            timestamp = response.get('current_date')
            homework = check_response(response)
            logger.info('Запрос проверен')
            if homework is not False:
                status = parse_status(homework)
                logger.info(f'Статус {status} получен')
                if status != last_status:
                    send_message(bot, status)
                else:
                    message = 'Статус работы не изменился'
                    send_message(bot, message)
            else:
                message = 'Работ для проверки нет'
                send_message(bot, message)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
