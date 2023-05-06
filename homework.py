from http import HTTPStatus

import logging
import os
import requests
import sys
import time

from dotenv import load_dotenv
from telegram import Bot


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MY_ERROR = 'Результат ответа не соответствует ожидаемому'


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=(
        logging.StreamHandler(sys.stdout),
    )
)
logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяется доступность переменных окружения."""
    if not PRACTICUM_TOKEN and not TELEGRAM_TOKEN and not TELEGRAM_CHAT_ID:
        logger.critical('Недоступны переменные окружения.')
        sys.exit('Чего-то не хватает')


def send_message(bot, message):
    """Отправляется сообщение в телеграм чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Делается запрос к эндпоинту."""
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(f'Ответ API {error}')
    if api_answer.status_code != HTTPStatus.OK:
        raise Exception(f'Получен ответ {api_answer.status_code}')
    return api_answer.json()


def check_response(response):
    """Проверяется ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error(MY_ERROR)
        raise TypeError(MY_ERROR)
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        logging.error(MY_ERROR)
        raise TypeError(MY_ERROR)
    if not homework:
        if not isinstance(homework[0], dict):
            logging.error(MY_ERROR)
            raise TypeError(MY_ERROR)


def parse_status(homework):
    """Извлекается статус из конкретной д/р."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        message = f'Неизвестный статус: {homework_status}'
        raise KeyError(message)
    if homework_name is None:
        raise KeyError('Отсутствует имя работы')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            logger.info('Запрос выполнен')
            timestamp = response.get('current_date')
            check_response(response)
            logger.info('Запрос проверен')
            homeworks = response.get('homeworks')
            first, *other = homeworks
            homework = first
            status = parse_status(homework)
            logger.info(f'Статус {status} получен')
            if status != last_status:
                try:
                    send_message(bot, status)
                except Exception as error:
                    logger.error(f'ERROR MESSAGE {error}')
            else:
                message = 'Статус работы не изменился'
                send_message(bot, message)
        except Exception as error:
            logger.critical(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
