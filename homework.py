import logging
import os
import requests
import sys
import time
from http import HTTPStatus

import telegram
from dotenv import load_dotenv
from telegram import Bot


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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=(
        logging.StreamHandler(sys.stdout),
    )
)
logger = logging.getLogger(__name__)


def my_error(error):
    """Функция формирования ответа ошибки."""
    answer = f'Результат ответа не соответствует ожидаемому. Ошибка {error}'
    return answer


def check_tokens():
    """Проверяется доступность переменных окружения."""
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID}
    token_flag = False
    for key, value in tokens.items():
        if not value:
            token_flag = True
            message = f'Недоступна переменная окружения {key}.'
            logger.critical(message)
    if token_flag:
        sys.exit(message)


def send_message(bot, message):
    """Отправляется сообщение в телеграм чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.debug('Сообщение отправлено.')


def get_api_answer(timestamp):
    """Делается запрос к эндпоинту."""
    params = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if api_answer.status_code != HTTPStatus.OK:
            raise Exception(f'Получен ответ {api_answer.status_code}.')
        return api_answer.json()
    except Exception as error:
        logger.error(my_error(error))
        raise Exception(my_error(error))


def check_response(response):
    """Проверяется ответ API на соответствие документации."""
    message_non_dict = 'Тип данных не является словарем.'
    message_non_list = 'Тип данных не является списком.'
    if not isinstance(response, dict):
        logging.error(message_non_dict)
        raise TypeError(message_non_dict)
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logging.error(message_non_list)
        raise TypeError(message_non_list)


def parse_status(homework):
    """Извлекается статус из конкретной д/р."""
    check_keys = ['homework_name', 'status']
    for check_key in check_keys:
        if check_key not in homework:
            message = 'Отсутвуют ключи для словаря.'
            logger.critical(message)
            raise KeyError(message)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        message = f'Неизвестный статус: {homework_status}'
        raise KeyError(message)
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
            logger.info('Запрос проверен.')
            homeworks = response.get('homeworks')
            if homeworks:
                homework, *_ = homeworks
                status = parse_status(homework)
                logger.info(f'Статус {status} получен.')
            else:
                logger.info('Список пуст.')            
            if status != last_status:
                message = status
            else:
                message = 'Статус работы не изменился.'
            send_message(bot, message)
        except telegram.error.TelegramError as error:
            logger.error(my_error(error))
        except Exception as error:
            logger.critical(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
