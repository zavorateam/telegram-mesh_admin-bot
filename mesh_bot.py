from telebot import TeleBot, types
import json
from dataclasses import dataclass
from typing import List, Optional
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))
TESTS_FILE = "tests.json"
ITEMS_PER_PAGE = 10

@dataclass
class Test:
    name: str
    homeworks: List[dict]

class TestManager:
    def __init__(self):
        self.tests: List[Test] = []
        self.current_test: Optional[Test] = None
        self.formatting_mode = False
        self.messages_to_format: List[str] = []
        self.load_tests()

    def load_tests(self):
        try:
            with open(TESTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tests = [Test(**test) for test in data]
        except FileNotFoundError:
            self.tests = []
        except Exception as e:
            print(f"Ошибка загрузки тестов: {e}")
            self.tests = []

    def save_tests(self):
        try:
            with open(TESTS_FILE, 'w', encoding='utf-8') as f:
                json.dump([test.__dict__ for test in self.tests], f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения тестов: {e}")

    def format_task(self, text: str) -> str:
        if "ЗАДАНИЕ:" in text and "ОТВЕТ:" in text:
            task = text.split('ЗАДАНИЕ:')[1].split('ОТВЕТ')[0].strip()
            answer = text.split('ОТВЕТ:')[1].split(')')[0].strip('():').strip()
            return f"""⌜⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⎺⌝
**ЗАДАНИЕ:** {task}
**ОТВЕТ:** __{answer}__
⌞⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⎽⌟"""
        return f"**{text}**\n__{'—' * 22}__"

class TelegramBot:
    def __init__(self):
        self.bot = TeleBot(BOT_TOKEN)
        self.test_manager = TestManager()
        self.setup_handlers()

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.bot.send_message(message.chat.id, "Привет! Используй /homeworks, чтобы увидеть доступные задания.")

        @self.bot.message_handler(commands=['admini'])
        def start_admin(message):
            if message.chat.id != ADMIN_CHAT_ID:
                return self.bot.reply_to(message, "Эта команда доступна только в административном чате.")
            
            if self.test_manager.current_test:
                return self.bot.reply_to(message, "Уже создается тест. Завершите его с помощью /xadmini.")
            
            self.test_manager.current_test = Test(name='Без названия', homeworks=[])
            self.test_manager.formatting_mode = True
            self.test_manager.messages_to_format = []
            self.bot.reply_to(message, "Режим администратора активирован. Отправьте тест одним сообщением, где первая строка - название теста.")

        @self.bot.message_handler(commands=['xadmini'])
        def end_admin(message):
            if message.chat.id != ADMIN_CHAT_ID:
                return self.bot.reply_to(message, "Эта команда доступна только в административном чате.")
            
            if not self.test_manager.current_test:
                return self.bot.reply_to(message, "Сейчас не создается тест.")
            
            if self.test_manager.messages_to_format:
                self.test_manager.current_test.name = self.test_manager.messages_to_format[0].splitlines()[0]
                for msg in self.test_manager.messages_to_format[1:]:
                    formatted = self.test_manager.format_task(msg)
                    self.test_manager.current_test.homeworks.append({'content': formatted})
            
            self.test_manager.tests.append(self.test_manager.current_test)
            self.test_manager.save_tests()
            self.test_manager.current_test = None
            self.test_manager.formatting_mode = False
            self.test_manager.messages_to_format = []
            self.bot.reply_to(message, "Режим администратора завершен. Тест сохранен.")

        @self.bot.message_handler(func=lambda m: self.test_manager.formatting_mode and m.chat.id == ADMIN_CHAT_ID)
        def collect_messages(message):
            self.test_manager.messages_to_format.append(message.text)

        @self.bot.message_handler(commands=['homeworks'])
        def homeworks_command(message):
            self.show_homeworks(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('get_test_'))
        def get_test_callback(call):
            test_index = int(call.data.split('_')[2])
            test = self.test_manager.tests[test_index]
            response = f"**ТЕСТ:** {test.name}\n\n"
            response += "\n\n".join(hw['content'] for hw in test.homeworks)
            self.bot.send_message(call.message.chat.id, response, parse_mode="Markdown")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
        def pagination_callback(call):
            page = int(call.data.split('_')[1])
            self.show_homeworks(call.message, page)

    def show_homeworks(self, message, page=0):
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        current_tests = self.test_manager.tests[start_idx:end_idx]

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for test in current_tests:
            keyboard.add(types.InlineKeyboardButton(
                text=test.name,
                callback_data=f"get_test_{self.test_manager.tests.index(test)}"
            ))

        if page > 0 or end_idx < len(self.test_manager.tests):
            row = []
            if page > 0:
                row.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page - 1}"))
            if end_idx < len(self.test_manager.tests):
                row.append(types.InlineKeyboardButton("Вперед ▶️", callback_data=f"page_{page + 1}"))
            keyboard.row(*row)

        self.bot.send_message(message.chat.id, "Выберите тест:", reply_markup=keyboard)

    def run(self):
        self.bot.infinity_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()