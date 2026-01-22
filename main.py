import asyncio
import json
import os
import random
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Файлы базы данных
USERS_DB_FILE = 'users.json'
CASES_DB_FILE = 'cases.json'
WITHDRAWALS_DB_FILE = 'withdrawals.json'
ADMINS_FILE = 'admins.json'
PROMOCODES_FILE = 'promocodes.json'
DEPOSITS_FILE = 'deposits.json'
SETTINGS_FILE = 'settings.json'

# Токен бота (замените на свой)
BOT_TOKEN = "8148376386:AAHVVNm3Jt4Iqp16ZIAXDzOAI-jV_Ne_hlQ"

# ID админа (замените на свой)
ADMIN_ID = 6539341659

# Классы состояний для FSM
class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    waiting_user_id = State()
    waiting_amount = State()
    waiting_withdrawal_action = State()
    waiting_case_data = State()
    waiting_promo_code = State()
    waiting_promo_amount = State()
    waiting_promo_uses = State()
    waiting_deposit_percent = State()
    waiting_deposit_amount = State()
    waiting_case_quantity = State()  # Новое состояние для ограничения кейсов

class UserWithdrawStates(StatesGroup):
    """Состояния пользователя для вывода"""
    waiting_contact_info = State()

class PromoStates(StatesGroup):
    """Состояния для активации промокодов"""
    waiting_promo_code = State()

class DepositStates(StatesGroup):
    """Состояния для вкладов"""
    waiting_deposit_amount = State()
    waiting_withdraw_deposit = State()

# Классы для работы с данными
class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class Database:
    """Класс для работы с JSON базой данных"""
    
    @staticmethod
    def load_users() -> Dict:
        """Загрузить данные пользователей"""
        if os.path.exists(USERS_DB_FILE):
            with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_users(users: Dict) -> None:
        """Сохранить данные пользователей"""
        with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_cases() -> Dict:
        """Загрузить кейсы"""
        if os.path.exists(CASES_DB_FILE):
            with open(CASES_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_cases(cases: Dict) -> None:
        """Сохранить кейсы"""
        with open(CASES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_withdrawals() -> Dict:
        """Загрузить заявки на вывод"""
        if os.path.exists(WITHDRAWALS_DB_FILE):
            with open(WITHDRAWALS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_withdrawals(withdrawals: Dict) -> None:
        """Сохранить заявки на вывод"""
        with open(WITHDRAWALS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(withdrawals, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_admins() -> List[int]:
        """Загрузить список админов"""
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return [ADMIN_ID]
    
    @staticmethod
    def save_admins(admins: List[int]) -> None:
        """Сохранить список админов"""
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(admins, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_promocodes() -> Dict:
        """Загрузить промокоды"""
        if os.path.exists(PROMOCODES_FILE):
            with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_promocodes(promocodes: Dict) -> None:
        """Сохранить промокоды"""
        with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(promocodes, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_deposits() -> Dict:
        """Загрузить вклады"""
        if os.path.exists(DEPOSITS_FILE):
            with open(DEPOSITS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_deposits(deposits: Dict) -> None:
        """Сохранить вклады"""
        with open(DEPOSITS_FILE, 'w', encoding='utf-8') as f:
            json.dump(deposits, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_settings() -> Dict:
        """Загрузить настройки"""
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        default_settings = {
            "deposit_percent": 5.0,
            "min_deposit_amount": 50,
            "deposit_enabled": True
        }
        Database.save_settings(default_settings)
        return default_settings
    
    @staticmethod
    def save_settings(settings: Dict) -> None:
        """Сохранить настройки"""
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

def init_default_cases():
    """Инициализировать кейсы по умолчанию с ограничениями"""
    cases = {
        "common_case": {
            "name": "📦 Обычный кейс",
            "description": "Содержит обычные предметы",
            "price": 100,
            "max_opens": None,  # None = без ограничений
            "opens_left": None,  # Сколько осталось открыть
            "total_opens": 0,  # Сколько уже открыто
            "is_limited": False,  # Ограниченный ли кейс
            "items": [
                {"id": "sword_common", "name": "🗡️ Обычный меч", "rarity": "common", "chance": 40.0},
                {"id": "shield_common", "name": "🛡️ Обычный щит", "rarity": "common", "chance": 35.0},
                {"id": "helmet_uncommon", "name": "⛑️ Необычный шлем", "rarity": "uncommon", "chance": 15.0},
                {"id": "potion_uncommon", "name": "🧪 Необычное зелье", "rarity": "uncommon", "chance": 9.5},
                {"id": "sword_rare", "name": "⚔️ Редкий меч", "rarity": "rare", "chance": 0.5}
            ]
        },
        "premium_case": {
            "name": "🎁 Премиум кейс",
            "description": "Шанс получить редкие предметы!",
            "price": 500,
            "max_opens": 100,  # Можно открыть максимум 100 раз
            "opens_left": 100,  # Осталось 100 открытий
            "total_opens": 0,
            "is_limited": True,
            "items": [
                {"id": "sword_uncommon", "name": "🗡️ Необычный меч", "rarity": "uncommon", "chance": 35.0},
                {"id": "shield_uncommon", "name": "🛡️ Необычный щит", "rarity": "uncommon", "chance": 30.0},
                {"id": "armor_rare", "name": "🥋 Редкая броня", "rarity": "rare", "chance": 20.0},
                {"id": "potion_rare", "name": "🧪 Редкое зелье", "rarity": "rare", "chance": 10.0},
                {"id": "sword_epic", "name": "🔪 Эпический меч", "rarity": "epic", "chance": 4.5},
                {"id": "artifact_legendary", "name": "💎 Легендарный артефакт", "rarity": "legendary", "chance": 0.5}
            ]
        },
        "legendary_case": {
            "name": "👑 Легендарный кейс",
            "description": "Шанс на легендарные предметы!",
            "price": 2000,
            "max_opens": 50,  # Можно открыть максимум 50 раз
            "opens_left": 50,  # Осталось 50 открытий
            "total_opens": 0,
            "is_limited": True,
            "items": [
                {"id": "sword_rare", "name": "⚔️ Редкий меч", "rarity": "rare", "chance": 40.0},
                {"id": "shield_epic", "name": "🛡️ Эпический щит", "rarity": "epic", "chance": 30.0},
                {"id": "armor_epic", "name": "🥋 Эпическая броня", "rarity": "epic", "chance": 20.0},
                {"id": "artifact_legendary", "name": "💎 Легендарный артефакт", "rarity": "legendary", "chance": 8.0},
                {"id": "sword_legendary", "name": "🗡️ Легендарный меч", "rarity": "legendary", "chance": 2.0}
            ]
        }
    }
    
    with open(CASES_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    
    logger.info("База данных кейсов инициализирована с ограничениями")

def generate_withdrawal_id() -> str:
    """Генерация ID заявки без точек"""
    timestamp_ms = int(datetime.now().timestamp() * 1000)
    withdrawal_id = f"wd{timestamp_ms}{random.randint(100, 999)}"
    return withdrawal_id

def safe_withdrawal_id(withdrawal_id: str) -> str:
    """Создание безопасного ID для команд Telegram (без точек)"""
    safe_id = withdrawal_id.replace('.', '_')
    return safe_id

def restore_withdrawal_id(safe_id: str) -> str:
    """Восстановление оригинального ID из безопасного"""
    original_id = safe_id.replace('_', '.')
    return original_id

def cleanup_inventory():
    """Очистка инвентаря от старых предметов без необходимых полей"""
    users = Database.load_users()
    cleaned = False
    
    for user_id_str, user_data in users.items():
        if "inventory" in user_data:
            new_inventory = []
            for item in user_data["inventory"]:
                if isinstance(item, dict):
                    if "name" not in item:
                        item["name"] = "Неизвестный предмет"
                    if "rarity" not in item:
                        item["rarity"] = "common"
                    if "item_id" not in item:
                        item["item_id"] = f"item_{datetime.now().timestamp()}_{random.randint(1000, 9999)}"
                    if "received_at" not in item:
                        item["received_at"] = datetime.now().isoformat()
                    if "id" not in item:
                        item["id"] = item.get("item_id", f"item_{random.randint(10000, 99999)}")
                    
                    new_inventory.append(item)
                else:
                    cleaned = True
            
            if len(new_inventory) != len(user_data["inventory"]):
                user_data["inventory"] = new_inventory
                cleaned = True
    
    if cleaned:
        Database.save_users(users)
        logger.info("Инвентарь очищен от поврежденных предметов")
    
    return cleaned

class UserManager:
    """Менеджер пользователей"""
    
    @staticmethod
    def get_user(user_id: int) -> Dict:
        """Получить данные пользователя"""
        users = Database.load_users()
        return users.get(str(user_id), None)
    
    @staticmethod
    def create_user(user_id: int, username: str = "") -> Dict:
        """Создать нового пользователя"""
        users = Database.load_users()
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "balance": 0,
            "deposit_balance": 0,
            "total_deposited": 0,
            "total_withdrawn_from_deposit": 0,
            "deposit_profit": 0,
            "inventory": [],
            "created_at": datetime.now().isoformat(),
            "cases_opened": 0,
            "withdrawals_count": 0,
            "total_withdrawn": 0,
            "used_promocodes": [],
            "items_on_withdrawal": [],
            "deposits": [],
            "opened_cases": {}  # Словарь для отслеживания открытых кейсов
        }
        
        users[str(user_id)] = user_data
        Database.save_users(users)
        return user_data
    
    @staticmethod
    def update_user(user_id: int, data: Dict):
        """Обновить данные пользователя"""
        users = Database.load_users()
        user_id_str = str(user_id)
        
        if user_id_str in users:
            users[user_id_str].update(data)
            Database.save_users(users)
    
    @staticmethod
    def add_balance(user_id: int, amount: int):
        """Добавить баланс пользователю"""
        user = UserManager.get_user(user_id)
        if user:
            user["balance"] += amount
            UserManager.update_user(user_id, {"balance": user["balance"]})
    
    @staticmethod
    def add_deposit_balance(user_id: int, amount: int):
        """Добавить баланс на вклад"""
        user = UserManager.get_user(user_id)
        if user:
            user["deposit_balance"] += amount
            user["total_deposited"] = user.get("total_deposited", 0) + amount
            UserManager.update_user(user_id, {
                "deposit_balance": user["deposit_balance"],
                "total_deposited": user["total_deposited"]
            })
    
    @staticmethod
    def withdraw_deposit_balance(user_id: int, amount: int):
        """Вывести с вклада"""
        user = UserManager.get_user(user_id)
        if user and user["deposit_balance"] >= amount:
            user["deposit_balance"] -= amount
            user["total_withdrawn_from_deposit"] = user.get("total_withdrawn_from_deposit", 0) + amount
            UserManager.update_user(user_id, {
                "deposit_balance": user["deposit_balance"],
                "total_withdrawn_from_deposit": user["total_withdrawn_from_deposit"]
            })
            return True
        return False
    
    @staticmethod
    def add_deposit_profit(user_id: int, amount: int):
        """Добавить прибыль с вкладов"""
        user = UserManager.get_user(user_id)
        if user:
            user["deposit_profit"] = user.get("deposit_profit", 0) + amount
            UserManager.update_user(user_id, {"deposit_profit": user["deposit_profit"]})
    
    @staticmethod
    def add_deposit_record(user_id: int, amount: int, deposit_type: str = "deposit"):
        """Добавить запись о вкладе"""
        user = UserManager.get_user(user_id)
        if user:
            if "deposits" not in user:
                user["deposits"] = []
            
            record = {
                "id": f"dep_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}",
                "amount": amount,
                "type": deposit_type,
                "date": datetime.now().isoformat(),
                "balance_after": user["deposit_balance"]
            }
            
            user["deposits"].append(record)
            UserManager.update_user(user_id, {"deposits": user["deposits"]})
    
    @staticmethod
    def add_to_inventory(user_id: int, item: Dict):
        """Добавить предмет в инвентарь"""
        user = UserManager.get_user(user_id)
        if user:
            item_with_date = {
                "name": item.get("name", "Неизвестный предмет"),
                "rarity": item.get("rarity", "common"),
                "id": item.get("id", f"item_{random.randint(10000, 99999)}"),
                "item_id": f"item_{datetime.now().timestamp()}_{random.randint(1000, 9999)}",
                "received_at": datetime.now().isoformat(),
                "chance": item.get("chance", 0),
                "original_id": item.get("id", ""),
                "on_withdrawal": False
            }
            
            for key, value in item.items():
                if key not in item_with_date:
                    item_with_date[key] = value
            
            user["inventory"].append(item_with_date)
            UserManager.update_user(user_id, {"inventory": user["inventory"]})
            
            logger.info(f"Добавлен предмет в инвентарь пользователя {user_id}: {item_with_date['name']} (ID: {item_with_date['item_id']})")
    
    @staticmethod
    def remove_from_inventory(user_id: int, item_id: str) -> Optional[Dict]:
        """Удалить предмет из инвентаря"""
        user = UserManager.get_user(user_id)
        if user:
            for i, item in enumerate(user["inventory"]):
                if (item.get("item_id") == item_id or 
                    item.get("id") == item_id or 
                    str(i) == item_id):
                    removed_item = user["inventory"].pop(i)
                    
                    if "items_on_withdrawal" in user:
                        if item_id in user["items_on_withdrawal"]:
                            user["items_on_withdrawal"].remove(item_id)
                    
                    UserManager.update_user(user_id, {
                        "inventory": user["inventory"],
                        "items_on_withdrawal": user.get("items_on_withdrawal", [])
                    })
                    logger.info(f"Удален предмет из инвентаря пользователя {user_id}: {removed_item.get('name')}")
                    return removed_item
        return None
    
    @staticmethod
    def get_item_by_index(user_id: int, index: int) -> Optional[Dict]:
        """Получить предмет по индексу в инвентаре"""
        user = UserManager.get_user(user_id)
        if not user:
            return None
        
        inventory = user.get("inventory", [])
        if 0 <= index < len(inventory):
            return inventory[index]
        return None
    
    @staticmethod
    def mark_item_on_withdrawal(user_id: int, item_id: str):
        """Пометить предмет как находящийся на выводе"""
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "items_on_withdrawal" not in user:
            user["items_on_withdrawal"] = []
        
        if item_id not in user["items_on_withdrawal"]:
            user["items_on_withdrawal"].append(item_id)
            UserManager.update_user(user_id, {"items_on_withdrawal": user["items_on_withdrawal"]})
            
            for item in user.get("inventory", []):
                if item.get("item_id") == item_id or item.get("id") == item_id:
                    item["on_withdrawal"] = True
                    UserManager.update_user(user_id, {"inventory": user["inventory"]})
                    break
    
    @staticmethod
    def unmark_item_on_withdrawal(user_id: int, item_id: str):
        """Снять отметку о выводе с предмета"""
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "items_on_withdrawal" in user and item_id in user["items_on_withdrawal"]:
            user["items_on_withdrawal"].remove(item_id)
            UserManager.update_user(user_id, {"items_on_withdrawal": user["items_on_withdrawal"]})
            
            for item in user.get("inventory", []):
                if item.get("item_id") == item_id or item.get("id") == item_id:
                    item["on_withdrawal"] = False
                    UserManager.update_user(user_id, {"inventory": user["inventory"]})
                    break
    
    @staticmethod
    def is_item_on_withdrawal(user_id: int, item_id: str) -> bool:
        """Проверить, находится ли предмет на выводе"""
        user = UserManager.get_user(user_id)
        if not user:
            return False
        
        if item_id in user.get("items_on_withdrawal", []):
            return True
        
        for item in user.get("inventory", []):
            if (item.get("item_id") == item_id or item.get("id") == item_id):
                return item.get("on_withdrawal", False)
        
        return False
    
    @staticmethod
    def add_used_promocode(user_id: int, promocode: str):
        """Добавить использованный промокод"""
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "used_promocodes" not in user:
            user["used_promocodes"] = []
        
        if promocode not in user["used_promocodes"]:
            user["used_promocodes"].append(promocode)
            UserManager.update_user(user_id, {"used_promocodes": user["used_promocodes"]})
    
    @staticmethod
    def has_used_promocode(user_id: int, promocode: str) -> bool:
        """Проверить, использовал ли пользователь промокод"""
        user = UserManager.get_user(user_id)
        if not user:
            return False
        
        return promocode in user.get("used_promocodes", [])
    
    @staticmethod
    def add_case_opened(user_id: int, case_id: str):
        """Добавить запись об открытии кейса"""
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "opened_cases" not in user:
            user["opened_cases"] = {}
        
        if case_id not in user["opened_cases"]:
            user["opened_cases"][case_id] = 0
        
        user["opened_cases"][case_id] += 1
        UserManager.update_user(user_id, {"opened_cases": user["opened_cases"]})

class DepositManager:
    """Менеджер вкладов"""
    
    @staticmethod
    def get_settings() -> Dict:
        """Получить настройки вкладов"""
        return Database.load_settings()
    
    @staticmethod
    def update_settings(settings: Dict):
        """Обновить настройки вкладов"""
        Database.save_settings(settings)
    
    @staticmethod
    def calculate_monthly_profit(deposit_amount: float) -> float:
        """Рассчитать месячную прибыль"""
        settings = DepositManager.get_settings()
        percent = settings.get("deposit_percent", 5.0)
        return deposit_amount * (percent / 100)
    
    @staticmethod
    def make_deposit(user_id: int, amount: int) -> Dict:
        """Сделать вклад"""
        user = UserManager.get_user(user_id)
        if not user:
            return {"success": False, "message": "❌ Пользователь не найден"}
        
        settings = DepositManager.get_settings()
        
        if not settings.get("deposit_enabled", True):
            return {"success": False, "message": "❌ Вклады временно отключены"}
        
        min_amount = settings.get("min_deposit_amount", 100)
        
        if amount < min_amount:
            return {"success": False, "message": f"❌ Минимальная сумма вклада: {min_amount} atm"}
        
        if user["balance"] < amount:
            return {"success": False, "message": f"❌ Недостаточно средств. На балансе: {user['balance']} atm"}
        
        # Переводим средства на вклад
        UserManager.add_balance(user_id, -amount)
        UserManager.add_deposit_balance(user_id, amount)
        UserManager.add_deposit_record(user_id, amount, "deposit")
        
        monthly_profit = DepositManager.calculate_monthly_profit(amount)
        
        return {
            "success": True,
            "message": f"✅ Вклад оформлен!\n\n"
                      f"💰 Сумма вклада: {amount} atm\n"
                      f"🏦 На вкладе: {user['deposit_balance'] + amount} atm\n"
                      f"💎 Месячная прибыль: {monthly_profit:.2f} atm\n"
                      f"📈 Процентная ставка: {settings.get('deposit_percent', 5.0)}%\n"
                      f"💳 Остаток на балансе: {user['balance'] - amount} atm",
            "monthly_profit": monthly_profit
        }
    
    @staticmethod
    def withdraw_from_deposit(user_id: int, amount: int) -> Dict:
        """Вывести средства с вклада"""
        user = UserManager.get_user(user_id)
        if not user:
            return {"success": False, "message": "❌ Пользователь не найден"}
        
        if user["deposit_balance"] < amount:
            return {"success": False, "message": f"❌ Недостаточно средств на вкладе. Доступно: {user['deposit_balance']} atm"}
        
        # Выводим средства с вклада
        if UserManager.withdraw_deposit_balance(user_id, amount):
            UserManager.add_balance(user_id, amount)
            UserManager.add_deposit_record(user_id, amount, "withdraw")
            
            return {
                "success": True,
                "message": f"✅ Средства выведены с вклада!\n\n"
                          f"💰 Выведено: {amount} atm\n"
                          f"🏦 Осталось на вкладе: {user['deposit_balance'] - amount} atm\n"
                          f"💳 Баланс: {user['balance'] + amount} atm"
            }
        
        return {"success": False, "message": "❌ Ошибка при выводе средств"}
    
    @staticmethod
    def calculate_profit_for_all_users():
        """Начислить проценты всем пользователям (вызывается раз в месяц)"""
        users = Database.load_users()
        settings = DepositManager.get_settings()
        percent = settings.get("deposit_percent", 5.0)
        
        total_profit = 0
        users_with_profit = 0
        
        for user_id_str, user_data in users.items():
            deposit_balance = user_data.get("deposit_balance", 0)
            
            if deposit_balance > 0:
                profit = deposit_balance * (percent / 100)
                user_id = int(user_id_str)
                
                # Начисляем прибыль
                UserManager.add_deposit_balance(user_id, profit)
                UserManager.add_deposit_profit(user_id, profit)
                UserManager.add_deposit_record(user_id, profit, "profit")
                
                total_profit += profit
                users_with_profit += 1
                
                # Уведомляем пользователя
                try:
                    bot = Bot.get_current()
                    asyncio.create_task(
                        bot.send_message(
                            user_id,
                            f"🏦 Начислены проценты по вкладу!\n\n"
                            f"💰 Сумма на вкладе: {deposit_balance:.2f} atm\n"
                            f"💎 Проценты: {profit:.2f} atm ({percent}%)\n"
                            f"🏦 Новый баланс вклада: {deposit_balance + profit:.2f} atm"
                        )
                    )
                except:
                    pass
        
        logger.info(f"Начислены проценты {users_with_profit} пользователям на общую сумму {total_profit:.2f} atm")
        return total_profit, users_with_profit
    
    @staticmethod
    def get_user_deposit_info(user_id: int) -> Dict:
        """Получить информацию о вкладе пользователя"""
        user = UserManager.get_user(user_id)
        if not user:
            return {}
        
        settings = DepositManager.get_settings()
        deposit_balance = user.get("deposit_balance", 0)
        monthly_profit = DepositManager.calculate_monthly_profit(deposit_balance)
        
        return {
            "deposit_balance": deposit_balance,
            "monthly_profit": monthly_profit,
            "total_deposited": user.get("total_deposited", 0),
            "total_withdrawn": user.get("total_withdrawn_from_deposit", 0),
            "deposit_profit": user.get("deposit_profit", 0),
            "percent": settings.get("deposit_percent", 5.0),
            "min_amount": settings.get("min_deposit_amount", 100),
            "enabled": settings.get("deposit_enabled", True)
        }

class WithdrawalManager:
    """Менеджер заявок на вывод"""
    
    @staticmethod
    def create_withdrawal(user_id: int, item: Dict, contact_info: str) -> Optional[str]:
        """Создать заявку на вывод"""
        withdrawals = Database.load_withdrawals()
        
        item_id = item.get("item_id", item.get("id", ""))
        if UserManager.is_item_on_withdrawal(user_id, item_id):
            logger.warning(f"Попытка повторного вывода предмета {item_id} пользователем {user_id}")
            return None
        
        withdrawal_id = generate_withdrawal_id()
        
        withdrawal_data = {
            "id": withdrawal_id,
            "user_id": user_id,
            "item": item,
            "item_id": item_id,
            "contact_info": contact_info,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "processed_at": None,
            "admin_id": None,
            "notes": ""
        }
        
        withdrawals[withdrawal_id] = withdrawal_data
        Database.save_withdrawals(withdrawals)
        
        UserManager.mark_item_on_withdrawal(user_id, item_id)
        
        user = UserManager.get_user(user_id)
        if user:
            user["withdrawals_count"] = user.get("withdrawals_count", 0) + 1
            UserManager.update_user(user_id, {"withdrawals_count": user["withdrawals_count"]})
        
        logger.info(f"Создана заявка на вывод {withdrawal_id} для предмета {item_id}")
        return withdrawal_id
    
    @staticmethod
    def get_withdrawal(withdrawal_id: str) -> Optional[Dict]:
        """Получить заявку по ID"""
        withdrawals = Database.load_withdrawals()
        return withdrawals.get(withdrawal_id)
    
    @staticmethod
    def get_pending_withdrawals() -> List[Dict]:
        """Получить все pending заявки"""
        withdrawals = Database.load_withdrawals()
        return [wd for wd in withdrawals.values() if wd["status"] == "pending"]
    
    @staticmethod
    def update_withdrawal(withdrawal_id: str, data: Dict):
        """Обновить заявку"""
        withdrawals = Database.load_withdrawals()
        if withdrawal_id in withdrawals:
            withdrawals[withdrawal_id].update(data)
            withdrawals[withdrawal_id]["processed_at"] = datetime.now().isoformat()
            Database.save_withdrawals(withdrawals)
            
            status = data.get("status")
            if status in ["approved", "rejected"]:
                withdrawal = withdrawals[withdrawal_id]
                user_id = withdrawal["user_id"]
                item_id = withdrawal.get("item_id", withdrawal["item"].get("item_id", ""))
                
                if item_id:
                    UserManager.unmark_item_on_withdrawal(user_id, item_id)
                
                if status == "approved":
                    user = UserManager.get_user(user_id)
                    if user:
                        item_value = {
                            "common": 50,
                            "uncommon": 100,
                            "rare": 500,
                            "epic": 2000,
                            "legendary": 10000
                        }.get(withdrawal["item"].get("rarity", "common"), 0)
                        
                        user["total_withdrawn"] = user.get("total_withdrawn", 0) + item_value
                        UserManager.update_user(user_id, {"total_withdrawn": user["total_withdrawn"]})
    
    @staticmethod
    def get_user_withdrawals(user_id: int) -> List[Dict]:
        """Получить заявки пользователя"""
        withdrawals = Database.load_withdrawals()
        user_wds = []
        for wd in withdrawals.values():
            if wd["user_id"] == user_id:
                user_wds.append(wd)
        return user_wds

class AdminManager:
    """Менеджер админов"""
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверить, является ли пользователь админом"""
        admins = Database.load_admins()
        return user_id in admins
    
    @staticmethod
    def add_admin(user_id: int) -> bool:
        """Добавить админа"""
        admins = Database.load_admins()
        if user_id not in admins:
            admins.append(user_id)
            Database.save_admins(admins)
            return True
        return False
    
    @staticmethod
    def remove_admin(user_id: int) -> bool:
        """Удалить админа"""
        admins = Database.load_admins()
        if user_id in admins:
            admins.remove(user_id)
            Database.save_admins(admins)
            return True
        return False

class CaseManager:
    """Менеджер кейсов"""
    
    @staticmethod
    def get_case(case_id: str) -> Optional[Dict]:
        """Получить кейс по ID"""
        cases = Database.load_cases()
        return cases.get(case_id)
    
    @staticmethod
    def get_all_cases() -> Dict:
        """Получить все кейсы"""
        return Database.load_cases()
    
    @staticmethod
    def can_open_case(case_id: str) -> Dict:
        """Проверить, можно ли открыть кейс (ограничения)"""
        case = CaseManager.get_case(case_id)
        if not case:
            return {"can_open": False, "reason": "Кейс не найден"}
        
        # Проверяем ограничение по количеству открытий
        if case.get("is_limited", False):
            opens_left = case.get("opens_left", 0)
            if opens_left <= 0:
                return {"can_open": False, "reason": "Кейс закончился"}
        
        return {"can_open": True, "reason": ""}
    
    @staticmethod
    def update_case_opens(case_id: str):
        """Обновить счетчик открытий кейса"""
        cases = Database.load_cases()
        if case_id in cases:
            case = cases[case_id]
            if case.get("is_limited", False):
                opens_left = case.get("opens_left", 0)
                if opens_left > 0:
                    case["opens_left"] = opens_left - 1
                case["total_opens"] = case.get("total_opens", 0) + 1
                Database.save_cases(cases)
    
    @staticmethod
    def open_case(case_id: str, user_id: int) -> Optional[Dict]:
        """Открыть кейс и получить предмет"""
        # Проверяем ограничения
        can_open = CaseManager.can_open_case(case_id)
        if not can_open["can_open"]:
            return {"error": can_open["reason"]}
        
        case = CaseManager.get_case(case_id)
        if not case:
            return {"error": "Кейс не найден"}
        
        user = UserManager.get_user(user_id)
        if not user:
            return {"error": "Пользователь не найден"}
        
        if user["balance"] < case["price"]:
            return {"error": "Недостаточно средств"}
        
        UserManager.add_balance(user_id, -case["price"])
        
        total_chance = sum(item["chance"] for item in case["items"])
        roll = random.uniform(0, total_chance)
        
        current_chance = 0
        selected_item = None
        
        for item in case["items"]:
            current_chance += item["chance"]
            if roll <= current_chance:
                selected_item = item.copy()
                break
        
        if selected_item:
            UserManager.add_to_inventory(user_id, selected_item)
            UserManager.add_case_opened(user_id, case_id)
            
            user["cases_opened"] = user.get("cases_opened", 0) + 1
            UserManager.update_user(user_id, {"cases_opened": user["cases_opened"]})
            
            # Обновляем счетчик открытий кейса
            CaseManager.update_case_opens(case_id)
            
            return selected_item
        
        return {"error": "Не удалось выбрать предмет"}

class PromoCodeManager:
    """Менеджер промокодов"""
    
    @staticmethod
    def generate_promocode(length: int = 8) -> str:
        """Генерация промокода"""
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(characters) for _ in range(length))
    
    @staticmethod
    def create_promocode(amount: int, max_uses: int = 1, creator_id: int = None) -> str:
        """Создать новый промокод"""
        promocodes = Database.load_promocodes()
        
        while True:
            promocode = PromoCodeManager.generate_promicode()
            if promocode not in promocodes:
                break
        
        promocodes[promocode] = {
            "code": promocode,
            "amount": amount,
            "max_uses": max_uses,
            "used_count": 0,
            "used_by": [],
            "created_at": datetime.now().isoformat(),
            "creator_id": creator_id,
            "is_active": True
        }
        
        Database.save_promocodes(promocodes)
        logger.info(f"Создан промокод {promocode} на {amount} atm, максимум использований: {max_uses}")
        return promocode
    
    @staticmethod
    def get_promocode(promocode: str) -> Optional[Dict]:
        """Получить промокод"""
        promocodes = Database.load_promocodes()
        return promocodes.get(promocode.upper())
    
    @staticmethod
    def activate_promocode(user_id: int, promocode: str) -> Dict:
        """Активировать промокод"""
        promocode = promocode.upper()
        promocodes = Database.load_promocodes()
        
        if promocode not in promocodes:
            return {"success": False, "message": "❌ Промокод не найден"}
        
        promo_data = promocodes[promocode]
        
        if not promo_data.get("is_active", True):
            return {"success": False, "message": "❌ Промокод деактивирован"}
        
        if promo_data["used_count"] >= promo_data["max_uses"]:
            return {"success": False, "message": "❌ Промокод уже использован максимальное количество раз"}
        
        if user_id in promo_data.get("used_by", []):
            return {"success": False, "message": "❌ Вы уже использовали этот промокод"}
        
        if UserManager.has_used_promocode(user_id, promocode):
            return {"success": False, "message": "❌ Вы уже использовали этот промокод"}
        
        UserManager.add_balance(user_id, promo_data["amount"])
        
        promo_data["used_count"] += 1
        if "used_by" not in promo_data:
            promo_data["used_by"] = []
        promo_data["used_by"].append(user_id)
        promo_data["last_used"] = datetime.now().isoformat()
        
        UserManager.add_used_promocode(user_id, promocode)
        
        Database.save_promocodes(promocodes)
        
        user = UserManager.get_user(user_id)
        
        return {
            "success": True,
            "message": f"✅ Промокод активирован!\n\n"
                      f"💎 Получено: {promo_data['amount']} atm\n"
                      f"💰 Ваш баланс: {user['balance']} atm\n"
                      f"📊 Промокод использован: {promo_data['used_count']}/{promo_data['max_uses']}",
            "amount": promo_data["amount"]
        }
    
    @staticmethod
    def deactivate_promocode(promocode: str) -> bool:
        """Деактивировать промокод"""
        promocodes = Database.load_promocodes()
        promocode = promocode.upper()
        
        if promocode in promocodes:
            promocodes[promocode]["is_active"] = False
            Database.save_promocodes(promocodes)
            return True
        return False
    
    @staticmethod
    def delete_promocode(promocode: str) -> bool:
        """Удалить промокод"""
        promocodes = Database.load_promocodes()
        promocode = promocode.upper()
        
        if promocode in promocodes:
            del promocodes[promocode]
            Database.save_promocodes(promocodes)
            return True
        return False
    
    @staticmethod
    def get_all_promocodes() -> Dict:
        """Получить все промокоды"""
        return Database.load_promocodes()
    
    @staticmethod
    def get_active_promocodes() -> Dict:
        """Получить активные промокоды"""
        promocodes = Database.load_promocodes()
        return {k: v for k, v in promocodes.items() if v.get("is_active", True)}

# Инициализация бота
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Клавиатуры
def get_main_keyboard():
    """Основная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎰 Кейсы"))
    builder.add(KeyboardButton(text="🎒 Инвентарь"))
    builder.add(KeyboardButton(text="💰 Баланс"))
    builder.add(KeyboardButton(text="🏦 Вклады"))
    builder.add(KeyboardButton(text="🎁 Активировать промокод"))
    builder.add(KeyboardButton(text="🏆 Топ игроков"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    """Клавиатура админа"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="👑 Админ панель"))
    builder.add(KeyboardButton(text="🎰 Кейсы"))
    builder.add(KeyboardButton(text="🎒 Инвентарь"))
    builder.add(KeyboardButton(text="💰 Баланс"))
    builder.add(KeyboardButton(text="🏦 Вклады"))
    builder.add(KeyboardButton(text="🎁 Активировать промокод"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_panel_keyboard():
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="admin_add_balance"))
    builder.add(InlineKeyboardButton(text="📊 Статистика пользователя", callback_data="admin_user_stats"))
    builder.add(InlineKeyboardButton(text="📋 Заявки на вывод", callback_data="admin_withdrawals"))
    builder.add(InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list"))
    builder.add(InlineKeyboardButton(text="🎰 Управление кейсами", callback_data="admin_cases"))
    builder.add(InlineKeyboardButton(text="🎁 Управление промокодами", callback_data="admin_promocodes"))
    builder.add(InlineKeyboardButton(text="🏦 Управление вкладами", callback_data="admin_deposits"))
    builder.add(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"))
    builder.add(InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_back_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_cases_admin_keyboard():
    """Клавиатура управления кейсами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Создать кейс", callback_data="admin_create_case"))
    builder.add(InlineKeyboardButton(text="📋 Список кейсов", callback_data="admin_list_cases"))
    builder.add(InlineKeyboardButton(text="⚙️ Настройки ограничений", callback_data="admin_case_settings"))
    builder.add(InlineKeyboardButton(text="🔧 Редактировать кейс", callback_data="admin_edit_case"))
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

def get_deposits_admin_keyboard():
    """Клавиатура управления вкладами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📈 Изменить процент", callback_data="admin_change_percent"))
    builder.add(InlineKeyboardButton(text="⚙️ Изменить мин. сумму", callback_data="admin_change_min_amount"))
    builder.add(InlineKeyboardButton(text="🔧 Включить/выключить", callback_data="admin_toggle_deposits"))
    builder.add(InlineKeyboardButton(text="💰 Начислить проценты", callback_data="admin_accrue_profit"))
    builder.add(InlineKeyboardButton(text="📊 Статистика вкладов", callback_data="admin_deposits_stats"))
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

def get_deposits_keyboard():
    """Клавиатура для вкладов"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Положить на вклад", callback_data="deposit_make"))
    builder.add(InlineKeyboardButton(text="💸 Вывести с вклада", callback_data="deposit_withdraw"))
    builder.add(InlineKeyboardButton(text="📊 Информация о вкладе", callback_data="deposit_info"))
    builder.add(InlineKeyboardButton(text="📈 История операций", callback_data="deposit_history"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_promocodes_admin_keyboard():
    """Клавиатура управления промокодами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo"))
    builder.add(InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos"))
    builder.add(InlineKeyboardButton(text="📊 Активные промокоды", callback_data="admin_active_promos"))
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

def get_cases_keyboard():
    """Клавиатура для выбора кейсов"""
    cases = CaseManager.get_all_cases()
    builder = InlineKeyboardBuilder()
    
    for case_id, case_data in cases.items():
        # Проверяем ограничения кейса
        can_open = CaseManager.can_open_case(case_id)
        if not can_open["can_open"] and case_data.get("is_limited", False):
            builder.add(InlineKeyboardButton(
                text=f"⛔ {case_data['name']} - {case_data['price']} atm (Закончился)",
                callback_data=f"case_{case_id}"
            ))
        else:
            builder.add(InlineKeyboardButton(
                text=f"{case_data['name']} - {case_data['price']} atm",
                callback_data=f"case_{case_id}"
            ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_case_detail_keyboard(case_id: str, can_open: bool = True):
    """Клавиатура для детального просмотра кейса"""
    case = CaseManager.get_case(case_id)
    builder = InlineKeyboardBuilder()
    
    if can_open:
        builder.add(InlineKeyboardButton(
            text=f"🎁 Открыть за {case['price']} atm",
            callback_data=f"open_case_{case_id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text=f"⛔ Недоступно для открытия",
            callback_data="case_info"
        ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_cases"))
    builder.adjust(1)
    return builder.as_markup()

def get_inventory_keyboard(items, page: int = 0):
    """Клавиатура для инвентаря с пагинацией"""
    builder = InlineKeyboardBuilder()
    items_per_page = 10
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = items[start_idx:end_idx]
    
    for idx, item in enumerate(page_items):
        item_name = item.get('name', 'Неизвестный предмет')[:15]
        rarity = item.get('rarity', 'common')
        is_on_withdrawal = item.get('on_withdrawal', False)
        
        emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(rarity, "⚫")
        
        if is_on_withdrawal:
            emoji = "⏳"
        
        actual_idx = start_idx + idx
        builder.add(InlineKeyboardButton(
            text=f"{emoji} {item_name}",
            callback_data=f"item_{actual_idx}"
        ))
    
    # Пагинация
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"inventory_page_{page-1}"
        ))
    
    if end_idx < len(items):
        pagination_row.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"inventory_page_{page+1}"
        ))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_item_management_keyboard(item_index: int, item_data: Dict):
    """Клавиатура управления предметом"""
    builder = InlineKeyboardBuilder()
    
    is_on_withdrawal = item_data.get('on_withdrawal', False)
    
    if not is_on_withdrawal:
        builder.add(InlineKeyboardButton(text="📤 Вывести предмет", callback_data=f"withdraw_{item_index}"))
    else:
        builder.add(InlineKeyboardButton(text="⏳ Уже на выводе", callback_data=f"info_{item_index}"))
    
    builder.add(InlineKeyboardButton(text="❌ Удалить предмет", callback_data=f"delete_{item_index}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад в инвентарь", callback_data="open_inventory"))
    builder.adjust(1)
    return builder.as_markup()

def get_withdrawal_action_keyboard(withdrawal_id: str):
    """Клавиатура действий с заявкой на вывод"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="📝 Комментарий", callback_data=f"comment_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_withdrawals"))
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_admin_keyboard():
    """Клавиатура возврата в админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

# Обработчики команд пользователя
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    user = UserManager.get_user(user_id)
    if not user:
        user = UserManager.create_user(user_id, username)
        welcome_text = (
            "🎮 Добро пожаловать в бот с кейсами!\n\n"
            f"💎 Вы получили стартовый баланс: {user['balance']} atm\n"
            "📦 Открывайте кейсы и собирайте коллекцию предметов!\n"
            "🏦 Используйте вклады для пассивного дохода!\n"
            "🎁 Активируйте промокоды для бонусов!\n"
            "🎒 Предметы можно выводить из инвентаря"
        )
    else:
        deposit_info = DepositManager.get_user_deposit_info(user_id)
        monthly_profit = deposit_info.get("monthly_profit", 0)
        
        welcome_text = (
            "🎮 С возвращением в бот с кейсами!\n\n"
            f"💰 Баланс: {user['balance']} atm\n"
            f"🏦 На вкладе: {user.get('deposit_balance', 0)} atm\n"
            f"💎 Месячная прибыль: {monthly_profit:.2f} atm\n"
            f"📦 Открыто кейсов: {user.get('cases_opened', 0)}\n"
            f"🎒 Предметов: {len(user.get('inventory', []))}\n"
            f"📤 Выведено предметов: {user.get('withdrawals_count', 0)}\n"
            f"🎁 Использовано промокодов: {len(user.get('used_promocodes', []))}\n\n"
            f"Пока идёт бета тест бота. Глав. админ бота @propepka\n"
            f"Лучше обращаться в сообщения каналу @atomopencase, так больше шансов что замечу\n\n"
            f"Мой прфиль в атоме с доказательством владения NFT https://www.atomglide.com/account/68d4457020d6eacdcdba2f34\n"
        )
    
    if AdminManager.is_admin(user_id):
        await message.answer(welcome_text, reply_markup=get_admin_keyboard())
    else:
        await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Показать баланс"""
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if user:
        withdrawals = WithdrawalManager.get_user_withdrawals(user_id)
        pending_count = sum(1 for wd in withdrawals if wd["status"] == "pending")
        deposit_info = DepositManager.get_user_deposit_info(user_id)
        
        text = (
            f"💰 Основной баланс: {user['balance']} atm\n"
            f"🏦 На вкладе: {user.get('deposit_balance', 0)} atm\n"
            f"💎 Месячная прибыль: {deposit_info.get('monthly_profit', 0):.2f} atm\n"
            f"📊 Процентная ставка: {deposit_info.get('percent', 5.0)}%\n"
            f"📦 Открыто кейсов: {user.get('cases_opened', 0)}\n"
            f"🎒 Предметов в инвентаре: {len(user.get('inventory', []))}\n"
            f"📤 Заявок на вывод: {len(withdrawals)} ({pending_count} в ожидании)\n"
            f"💎 Всего выведено: {user.get('total_withdrawn', 0)} atm\n"
            f"🏦 Всего на вкладах: {user.get('total_deposited', 0)} atm\n"
            f"💎 Прибыль с вкладов: {user.get('deposit_profit', 0):.2f} atm\n"
            f"🎁 Использовано промокодов: {len(user.get('used_promocodes', []))}"
        )
        await message.answer(text)
    else:
        await message.answer("❌ Пользователь не найден")

@dp.message(F.text == "👑 Админ панель")
async def handle_admin_panel(message: types.Message):
    """Обработчик кнопки админ-панели"""
    user_id = message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await message.answer("⛔ У вас нет прав доступа к админ-панели")
        return
    
    admin_text = (
        "👑 Админ-панель\n\n"
        "Выберите действие:"
    )
    
    await message.answer(admin_text, reply_markup=get_admin_panel_keyboard())

# Обработчики вкладов
@dp.message(F.text == "🏦 Вклады")
async def handle_deposits(message: types.Message):
    """Обработчик кнопки Вклады"""
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    deposit_info = DepositManager.get_user_deposit_info(user_id)
    
    if not deposit_info.get("enabled", True):
        await message.answer("❌ Вклады временно отключены")
        return
    
    text = (
        "🏦 Система вкладов\n\n"
        f"💰 Ваш баланс: {user['balance']} atm\n"
        f"🏦 На вкладе: {deposit_info['deposit_balance']} atm\n"
        f"💎 Месячная прибыль: {deposit_info['monthly_profit']:.2f} atm\n"
        f"📊 Процентная ставка: {deposit_info['percent']}% в месяц\n"
        f"💰 Минимальная сумма: {deposit_info['min_amount']} atm\n"
        f"💎 Всего прибыли: {deposit_info['deposit_profit']:.2f} atm\n\n"
        "Выберите действие:"
    )
    
    await message.answer(text, reply_markup=get_deposits_keyboard())

@dp.callback_query(F.data == "deposit_info")
async def handle_deposit_info(callback: CallbackQuery):
    """Информация о вкладе"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    deposit_info = DepositManager.get_user_deposit_info(user_id)
    
    text = (
        "📊 Информация о вашем вкладе:\n\n"
        f"💰 Сумма на вкладе: {deposit_info['deposit_balance']:.2f} atm\n"
        f"💎 Месячная прибыль: {deposit_info['monthly_profit']:.2f} atm\n"
        f"📊 Процентная ставка: {deposit_info['percent']}% в месяц\n"
        f"🏦 Всего внесено: {deposit_info['total_deposited']} atm\n"
        f"💸 Всего выведено: {deposit_info['total_withdrawn']} atm\n"
        f"💎 Прибыль с вкладов: {deposit_info['deposit_profit']:.2f} atm\n"
        f"💰 Минимальная сумма: {deposit_info['min_amount']} atm\n\n"
        f"💡 Проценты начисляются раз в месяц автоматически."
    )
    
    await callback.message.edit_text(text, reply_markup=get_deposits_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "deposit_make")
async def handle_deposit_make(callback: CallbackQuery, state: FSMContext):
    """Сделать вклад"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    deposit_info = DepositManager.get_user_deposit_info(user_id)
    
    if not deposit_info.get("enabled", True):
        await callback.message.edit_text(
            "❌ Вклады временно отключены",
            reply_markup=get_deposits_keyboard()
        )
        await callback.answer()
        return
    
    min_amount = deposit_info.get("min_amount", 100)
    
    text = (
        "💰 Внесение средств на вклад\n\n"
        f"💰 Ваш баланс: {user['balance']} atm\n"
        f"🏦 Текущий вклад: {deposit_info['deposit_balance']:.2f} atm\n"
        f"💎 Процентная ставка: {deposit_info['percent']}% в месяц\n"
        f"💰 Минимальная сумма: {min_amount} atm\n\n"
        "Введите сумму для внесения на вклад:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    await state.set_state(DepositStates.waiting_deposit_amount)
    await callback.answer()

@dp.message(DepositStates.waiting_deposit_amount)
async def handle_deposit_amount_input(message: types.Message, state: FSMContext):
    """Обработка суммы для вклада"""
    try:
        amount = int(message.text)
        user_id = message.from_user.id
        
        result = DepositManager.make_deposit(user_id, amount)
        
        if result["success"]:
            await message.answer(
                result["message"],
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                result["message"] + "\n\nПопробуйте другую сумму:",
                reply_markup=get_back_to_admin_keyboard()
            )
            return
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число:")

@dp.callback_query(F.data == "deposit_withdraw")
async def handle_deposit_withdraw(callback: CallbackQuery, state: FSMContext):
    """Вывести с вклада"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    deposit_balance = user.get("deposit_balance", 0)
    
    if deposit_balance <= 0:
        await callback.message.edit_text(
            "❌ У вас нет средств на вкладе",
            reply_markup=get_deposits_keyboard()
        )
        await callback.answer()
        return
    
    text = (
        "💸 Вывод средств с вклада\n\n"
        f"🏦 Доступно для вывода: {deposit_balance} atm\n"
        f"💰 Ваш баланс: {user['balance']} atm\n\n"
        "Введите сумму для вывода с вклада:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    await state.set_state(DepositStates.waiting_withdraw_deposit)
    await callback.answer()

@dp.message(DepositStates.waiting_withdraw_deposit)
async def handle_withdraw_deposit_amount(message: types.Message, state: FSMContext):
    """Обработка суммы для вывода с вклада"""
    try:
        amount = int(message.text)
        user_id = message.from_user.id
        
        result = DepositManager.withdraw_from_deposit(user_id, amount)
        
        if result["success"]:
            await message.answer(
                result["message"],
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                result["message"] + "\n\nПопробуйте другую сумму:",
                reply_markup=get_back_to_admin_keyboard()
            )
            return
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число:")

@dp.callback_query(F.data == "deposit_history")
async def handle_deposit_history(callback: CallbackQuery):
    """История операций по вкладу"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    deposits = user.get("deposits", [])
    
    if not deposits:
        await callback.message.edit_text(
            "📊 У вас еще нет операций по вкладам",
            reply_markup=get_deposits_keyboard()
        )
        await callback.answer()
        return
    
    text = "📊 История операций по вкладу:\n\n"
    
    for record in deposits[-10:]:
        amount = record["amount"]
        record_type = record["type"]
        date = datetime.fromisoformat(record["date"]).strftime("%d.%m.%Y %H:%M")
        
        type_text = {
            "deposit": "💰 Внесение",
            "withdraw": "💸 Вывод",
            "profit": "💎 Проценты"
        }.get(record_type, "📊 Операция")
        
        text += f"{type_text}: {amount} atm\n"
        text += f"📅 {date}\n"
        text += f"🏦 Баланс после: {record.get('balance_after', 0):.2f} atm\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_deposits_keyboard())
    await callback.answer()

# Обработчики админ-панели для вкладов
@dp.callback_query(F.data == "admin_deposits")
async def handle_admin_deposits(callback: CallbackQuery):
    """Управление вкладами в админ-панели"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    settings = DepositManager.get_settings()
    users = Database.load_users()
    
    total_deposits = sum(user.get("deposit_balance", 0) for user in users.values())
    total_users_with_deposits = sum(1 for user in users.values() if user.get("deposit_balance", 0) > 0)
    total_profit = sum(user.get("deposit_profit", 0) for user in users.values())
    
    monthly_profit = total_deposits * (settings.get("deposit_percent", 5.0) / 100)
    
    text = (
        "🏦 Управление вкладами\n\n"
        f"📊 Процентная ставка: {settings.get('deposit_percent', 5.0)}%\n"
        f"💰 Минимальная сумма: {settings.get('min_deposit_amount', 100)} atm\n"
        f"🔧 Статус: {'✅ Включено' if settings.get('deposit_enabled', True) else '❌ Выключено'}\n\n"
        f"📈 Статистика:\n"
        f"🏦 Всего на вкладах: {total_deposits:.2f} atm\n"
        f"👥 Пользователей с вкладами: {total_users_with_deposits}\n"
        f"💎 Общая прибыль: {total_profit:.2f} atm\n"
        f"📈 Месячная прибыль: {monthly_profit:.2f} atm\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_deposits_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_change_percent")
async def handle_admin_change_percent(callback: CallbackQuery, state: FSMContext):
    """Изменить процентную ставку"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    settings = DepositManager.get_settings()
    current_percent = settings.get("deposit_percent", 5.0)
    
    await callback.message.edit_text(
        f"📈 Изменение процентной ставки\n\n"
        f"Текущая ставка: {current_percent}%\n\n"
        "Введите новую процентную ставку (например: 5.0 для 5%):",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_deposit_percent)
    await callback.answer()

@dp.message(AdminStates.waiting_deposit_percent)
async def handle_deposit_percent_input(message: types.Message, state: FSMContext):
    """Обработка ввода новой процентной ставки"""
    try:
        percent = float(message.text)
        
        if percent <= 0:
            await message.answer("❌ Процент должен быть положительным. Попробуйте еще раз:")
            return
        
        if percent > 100:
            await message.answer("❌ Процент не может превышать 100%. Попробуйте еще раз:")
            return
        
        settings = DepositManager.get_settings()
        old_percent = settings.get("deposit_percent", 5.0)
        settings["deposit_percent"] = percent
        DepositManager.update_settings(settings)
        
        await message.answer(
            f"✅ Процентная ставка изменена!\n\n"
            f"📈 Было: {old_percent}%\n"
            f"📈 Стало: {percent}%\n\n"
            f"💡 Изменение вступит в силу с момента начисления следующих процентов.",
            reply_markup=get_admin_panel_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 5.0):")

@dp.callback_query(F.data == "admin_change_min_amount")
async def handle_admin_change_min_amount(callback: CallbackQuery, state: FSMContext):
    """Изменить минимальную сумму вклада"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    settings = DepositManager.get_settings()
    current_min = settings.get("min_deposit_amount", 100)
    
    await callback.message.edit_text(
        f"💰 Изменение минимальной суммы вклада\n\n"
        f"Текущий минимум: {current_min} atm\n\n"
        "Введите новую минимальную сумму:",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_amount)
    await state.update_data(action="change_min_deposit")
    await callback.answer()

@dp.callback_query(F.data == "admin_toggle_deposits")
async def handle_admin_toggle_deposits(callback: CallbackQuery):
    """Включить/выключить вклады"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    settings = DepositManager.get_settings()
    current_status = settings.get("deposit_enabled", True)
    new_status = not current_status
    
    settings["deposit_enabled"] = new_status
    DepositManager.update_settings(settings)
    
    status_text = "✅ включены" if new_status else "❌ выключены"
    
    await callback.answer(f"Вклады {status_text}")
    await handle_admin_deposits(callback)

@dp.callback_query(F.data == "admin_accrue_profit")
async def handle_admin_accrue_profit(callback: CallbackQuery):
    """Начислить проценты вручную"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    total_profit, users_count = DepositManager.calculate_profit_for_all_users()
    
    await callback.answer(f"✅ Начислено {total_profit:.2f} atm {users_count} пользователям")
    await handle_admin_deposits(callback)

@dp.callback_query(F.data == "admin_deposits_stats")
async def handle_admin_deposits_stats(callback: CallbackQuery):
    """Статистика вкладов"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    users = Database.load_users()
    settings = DepositManager.get_settings()
    
    users_with_deposits = []
    for user_data in users.values():
        deposit_balance = user_data.get("deposit_balance", 0)
        if deposit_balance > 0:
            users_with_deposits.append({
                "username": user_data.get("username", f"user_{user_data['user_id']}"),
                "deposit_balance": deposit_balance,
                "deposit_profit": user_data.get("deposit_profit", 0),
                "user_id": user_data["user_id"]
            })
    
    users_with_deposits.sort(key=lambda x: x["deposit_balance"], reverse=True)
    
    total_deposits = sum(user.get("deposit_balance", 0) for user in users.values())
    total_profit = sum(user.get("deposit_profit", 0) for user in users.values())
    monthly_profit = total_deposits * (settings.get("deposit_percent", 5.0) / 100)
    
    text = (
        "📊 Подробная статистика вкладов:\n\n"
        f"🏦 Всего на вкладах: {total_deposits:.2f} atm\n"
        f"💎 Общая прибыль: {total_profit:.2f} atm\n"
        f"📈 Месячная прибыль: {monthly_profit:.2f} atm\n"
        f"📊 Процентная ставка: {settings.get('deposit_percent', 5.0)}%\n\n"
        f"🏆 Топ вкладчиков ({len(users_with_deposits)} всего):\n\n"
    )
    
    for i, user in enumerate(users_with_deposits[:10], 1):
        user_profit = user["deposit_balance"] * (settings.get("deposit_percent", 5.0) / 100)
        text += (
            f"{i}. @{user['username']}\n"
            f"   🏦 На вкладе: {user['deposit_balance']:.2f} atm\n"
            f"   💎 Прибыль: {user['deposit_profit']:.2f} atm\n"
            f"   📈 Месячная: {user_profit:.2f} atm\n\n"
        )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_deposits"))
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики админ-панели (остальные)
@dp.callback_query(F.data == "admin_back_panel")
async def handle_admin_back_panel(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    await callback.message.edit_text(
        "👑 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_add_balance")
async def handle_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса пользователю"""
    await callback.message.edit_text(
        "💰 Пополнение баланса\n\n"
        "Введите ID пользователя, которому нужно пополнить баланс:",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_user_id)
    await callback.answer()

@dp.message(AdminStates.waiting_user_id)
async def handle_user_id_input(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя"""
    try:
        user_id = int(message.text)
        user = UserManager.get_user(user_id)
        
        if not user:
            await message.answer("❌ Пользователь не найден. Попробуйте еще раз:")
            return
        
        data = await state.get_data()
        action = data.get("action")
        
        if action == "change_min_deposit":
            try:
                min_amount = int(message.text)
                if min_amount <= 0:
                    await message.answer("❌ Сумма должна быть положительной. Попробуйте еще раз:")
                    return
                
                settings = DepositManager.get_settings()
                old_min = settings.get("min_deposit_amount", 100)
                settings["min_deposit_amount"] = min_amount
                DepositManager.update_settings(settings)
                
                await message.answer(
                    f"✅ Минимальная сумма вклада изменена!\n\n"
                    f"💰 Было: {old_min} atm\n"
                    f"💰 Стало: {min_amount} atm",
                    reply_markup=get_admin_panel_keyboard()
                )
                await state.clear()
            except ValueError:
                await message.answer("❌ Неверный формат суммы. Введите число:")
            return
        
        await state.update_data(user_id=user_id)
        await message.answer(
            f"Пользователь найден: @{user.get('username', 'без username')}\n"
            f"Текущий баланс: {user['balance']} atm\n"
            f"На вкладе: {user.get('deposit_balance', 0)} atm\n\n"
            "Введите сумму для пополнения (только число):"
        )
        await state.set_state(AdminStates.waiting_amount)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")

@dp.message(AdminStates.waiting_amount)
async def handle_amount_input(message: types.Message, state: FSMContext):
    """Обработка ввода суммы"""
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной. Попробуйте еще раз:")
            return
        
        data = await state.get_data()
        user_id = data['user_id']
        
        UserManager.add_balance(user_id, amount)
        user = UserManager.get_user(user_id)
        
        logger.info(f"Admin {message.from_user.id} added {amount} atm to user {user_id}")
        
        await message.answer(
            f"✅ Баланс пользователя @{user.get('username', user_id)} пополнен на {amount} atm\n"
            f"💰 Новый баланс: {user['balance']} atm",
            reply_markup=get_admin_panel_keyboard() if AdminManager.is_admin(message.from_user.id) else get_main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Введите число:")

@dp.callback_query(F.data == "admin_withdrawals")
async def handle_admin_withdrawals(callback: CallbackQuery):
    """Показать заявки на вывод"""
    withdrawals = WithdrawalManager.get_pending_withdrawals()
    
    if not withdrawals:
        await callback.message.edit_text(
            "📋 Нет pending заявок на вывод",
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
        return
    
    text = f"📋 Заявки на вывод ({len(withdrawals)} pending):\n\n"
    
    for i, wd in enumerate(withdrawals[:10], 1):
        user = UserManager.get_user(wd["user_id"])
        username = user.get("username", "без username") if user else "Пользователь не найден"
        item = wd["item"]
        
        safe_id = safe_withdrawal_id(wd['id'])
        
        text += (
            f"{i}. ID: {wd['id']}\n"
            f"👤 Пользователь: @{username} ({wd['user_id']})\n"
            f"🎁 Предмет: {item.get('name', 'Без имени')}\n"
            f"📅 Дата: {wd['created_at'][:19]}\n"
            f"📞 Контакт: {wd['contact_info'][:30]}...\n"
            f"🔗 Действие: /handlewd_{safe_id}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_admin_keyboard()
    )
    await callback.answer()

# Обработчик команды для работы с заявкой
@dp.message(Command(commands=["handlewd"]))
async def handle_withdrawal_command(message: types.Message):
    """Обработчик команды /handlewd с безопасным ID"""
    if not AdminManager.is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав доступа к этой команде")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /handlewd <ID_заявки>")
        return
    
    safe_id = args[1]
    withdrawal_id = restore_withdrawal_id(safe_id)
    
    withdrawal = WithdrawalManager.get_withdrawal(withdrawal_id)
    
    if not withdrawal:
        await message.answer("❌ Заявка не найдена")
        return
    
    user = UserManager.get_user(withdrawal["user_id"])
    username = user.get("username", "без username") if user else "Пользователь не найден"
    item = withdrawal["item"]
    
    rarity_emoji = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(item.get("rarity", "common"), "⚫")
    
    status_emoji = {
        "pending": "⏳",
        "approved": "✅",
        "rejected": "❌"
    }.get(withdrawal["status"], "❓")
    
    text = (
        f"📋 Заявка на вывод #{withdrawal_id}\n\n"
        f"{status_emoji} Статус: {withdrawal['status']}\n"
        f"👤 Пользователь: @{username} ({withdrawal['user_id']})\n"
        f"{rarity_emoji} Предмет: {item.get('name', 'Без имени')}\n"
        f"📊 Редкость: {item.get('rarity', 'common')}\n"
        f"📅 Создана: {withdrawal['created_at'][:19]}\n"
        f"📞 Контакт: {withdrawal['contact_info']}\n"
    )
    
    if withdrawal["processed_at"]:
        text += f"📅 Обработана: {withdrawal['processed_at'][:19]}\n"
    if withdrawal["admin_id"]:
        text += f"👨‍💼 Обработал: {withdrawal['admin_id']}\n"
    if withdrawal["notes"]:
        text += f"📝 Комментарий: {withdrawal['notes']}\n"
    
    await message.answer(
        text,
        reply_markup=get_withdrawal_action_keyboard(withdrawal_id)
    )

# Обработчики кейсов
@dp.message(F.text == "🎰 Кейсы")
async def handle_cases_button(message: types.Message):
    """Обработчик кнопки Кейсы"""
    await show_cases_menu(message)

async def show_cases_menu(message: types.Message):
    """Показать меню кейсов"""
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    cases = CaseManager.get_all_cases()
    
    if not cases:
        await message.answer("❌ Кейсы временно недоступны")
        return
    
    cases_text = "📦 Доступные кейсы:\n\n"
    for case_id, case_data in cases.items():
        # Проверяем ограничения
        can_open = CaseManager.can_open_case(case_id)
        if case_data.get("is_limited", False):
            if can_open["can_open"]:
                cases_text += f"🔴 {case_data['name']} - {case_data['price']} atm (Осталось: {case_data.get('opens_left', 0)})\n"
            else:
                cases_text += f"⛔ {case_data['name']} - ЗАКОНЧИЛСЯ\n"
        else:
            cases_text += f"🟢 {case_data['name']} - {case_data['price']} atm\n"
        
        cases_text += f"📝 {case_data['description']}\n\n"
    
    cases_text += f"💎 Ваш баланс: {user['balance']} atm"
    
    await message.answer(cases_text, reply_markup=get_cases_keyboard())

@dp.callback_query(F.data.startswith("case_"))
async def handle_case_selection(callback: CallbackQuery):
    """Показывает информацию о выбранном кейсе"""
    case_id = callback.data.replace("case_", "")
    case = CaseManager.get_case(case_id)
    
    if not case:
        await callback.answer("❌ Кейс не найден")
        return
    
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Проверяем можно ли открыть кейс
    can_open_check = CaseManager.can_open_case(case_id)
    can_open = can_open_check["can_open"]
    
    # Формируем текст с информацией о кейсе
    text = (
        f"{case['name']}\n"
        f"{case['description']}\n\n"
        f"💰 Цена: {case['price']} atm\n"
        f"🎁 Количество предметов: {len(case['items'])}\n"
    )
    
    # Добавляем информацию об ограничениях
    if case.get("is_limited", False):
        opens_left = case.get("opens_left", 0)
        total_opens = case.get("total_opens", 0)
        max_opens = case.get("max_opens", 0)
        
        if can_open:
            text += f"📊 Осталось открытий: {opens_left}/{max_opens}\n"
        else:
            text += f"⛔ Кейс закончился! Открыто: {total_opens}/{max_opens}\n"
    else:
        text += "♾️ Без ограничений\n"
    
    text += f"\n📊 Содержимое:\n"
    
    # Показываем предметы в кейсе с их шансами
    rarity_colors = {
        "common": "⚪ Обычный",
        "uncommon": "🟢 Необычный",
        "rare": "🔵 Редкий",
        "epic": "🟣 Эпический",
        "legendary": "🟡 Легендарный"
    }
    
    for item in case['items']:
        rarity_text = rarity_colors.get(item.get('rarity', 'common'), '⚫ Неизвестно')
        text += f"{rarity_text} {item['name']} - {item['chance']:.1f}%\n"
    
    text += f"\n💎 Ваш баланс: {user['balance']} atm"
    
    if not can_open and case.get("is_limited", False):
        text += f"\n\n❌ {can_open_check['reason']}"
    
    await callback.message.edit_text(text, reply_markup=get_case_detail_keyboard(case_id, can_open))
    await callback.answer()

@dp.callback_query(F.data.startswith("open_case_"))
async def handle_open_case(callback: CallbackQuery):
    """Открывает выбранный кейс"""
    case_id = callback.data.replace("open_case_", "")
    user_id = callback.from_user.id
    
    # Проверяем, достаточно ли средств
    user = UserManager.get_user(user_id)
    case = CaseManager.get_case(case_id)
    
    if not user or not case:
        await callback.answer("❌ Ошибка")
        return
    
    if user["balance"] < case["price"]:
        await callback.answer(f"❌ Недостаточно средств. Нужно: {case['price']} atm")
        return
    
    # Проверяем ограничения
    can_open = CaseManager.can_open_case(case_id)
    if not can_open["can_open"]:
        await callback.answer(f"❌ {can_open['reason']}")
        return
    
    # Открываем кейс
    result = CaseManager.open_case(case_id, user_id)
    
    if result and "error" not in result:
        # Успешно открыли кейс
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(result.get("rarity", "common"), "⚫")
        
        # Обновляем данные пользователя
        user = UserManager.get_user(user_id)
        
        text = (
            f"🎉 Вы открыли {case['name']}!\n\n"
            f"{rarity_emoji} Вы получили: {result['name']}\n"
            f"📊 Редкость: {result.get('rarity', 'common')}\n"
            f"🎯 Шанс выпадения: {result.get('chance', 0):.1f}%\n\n"
            f"💰 Потрачено: {case['price']} atm\n"
            f"💎 Новый баланс: {user['balance']} atm\n"
            f"🎒 Предмет добавлен в инвентарь!"
        )
        
        # Обновляем информацию об ограничениях кейса
        updated_case = CaseManager.get_case(case_id)
        opens_info = ""
        if updated_case.get("is_limited", False):
            opens_left = updated_case.get("opens_left", 0)
            total_opens = updated_case.get("total_opens", 0)
            opens_info = f"\n\n📊 Осталось открытий этого кейса: {opens_left}"
        
        text += opens_info
        
        # Клавиатура после открытия
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="🎒 Перейти в инвентарь",
            callback_data="open_inventory"
        ))
        builder.add(InlineKeyboardButton(
            text="🎁 Открыть еще",
            callback_data=f"case_{case_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="📋 К списку кейсов",
            callback_data="back_to_cases"
        ))
        builder.adjust(1)
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        # Ошибка при открытии
        error_msg = result.get("error", "Неизвестная ошибка") if result else "Неизвестная ошибка"
        await callback.message.edit_text(
            f"❌ Не удалось открыть кейс: {error_msg}\n\n"
            f"Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"case_{case_id}")
            ]])
        )
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_cases")
async def handle_back_to_cases(callback: CallbackQuery):
    """Возвращает к списку кейсов"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    cases = CaseManager.get_all_cases()
    
    if not cases:
        await callback.message.edit_text("❌ Кейсы временно недоступны")
        await callback.answer()
        return
    
    cases_text = "📦 Доступные кейсы:\n\n"
    for case_id, case_data in cases.items():
        # Проверяем ограничения
        can_open = CaseManager.can_open_case(case_id)
        if case_data.get("is_limited", False):
            if can_open["can_open"]:
                cases_text += f"🔴 {case_data['name']} - {case_data['price']} atm (Осталось: {case_data.get('opens_left', 0)})\n"
            else:
                cases_text += f"⛔ {case_data['name']} - ЗАКОНЧИЛСЯ\n"
        else:
            cases_text += f"🟢 {case_data['name']} - {case_data['price']} atm\n"
        
        cases_text += f"📝 {case_data['description']}\n\n"
    
    cases_text += f"💎 Ваш баланс: {user['balance']} atm"
    
    await callback.message.edit_text(cases_text, reply_markup=get_cases_keyboard())
    await callback.answer()

# Обработчики инвентаря
@dp.message(F.text == "🎒 Инвентарь")
async def handle_inventory_button(message: types.Message):
    """Обработчик кнопки Инвентарь"""
    await show_inventory(message)

async def show_inventory(message: types.Message, page: int = 0):
    """Показать инвентарь"""
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    inventory = user.get("inventory", [])
    
    if not inventory:
        await message.answer(
            "🎒 Ваш инвентарь пуст\n"
            "📦 Откройте кейсы, чтобы получить предметы!",
            reply_markup=get_main_keyboard()
        )
        return
    
    rarity_count = {}
    items_on_withdrawal = 0
    
    for item in inventory:
        if isinstance(item, dict):
            rarity = item.get("rarity", "unknown")
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            if item.get('on_withdrawal', False):
                items_on_withdrawal += 1
    
    items_per_page = 10
    total_pages = (len(inventory) + items_per_page - 1) // items_per_page
    
    inventory_text = f"🎒 Ваш инвентарь ({len(inventory)} предметов)"
    
    if total_pages > 1:
        inventory_text += f" (Страница {page + 1}/{total_pages})"
    
    inventory_text += ":\n\n"
    
    if items_on_withdrawal > 0:
        inventory_text += f"⏳ На выводе: {items_on_withdrawal} предметов\n\n"
    
    for rarity, count in rarity_count.items():
        emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(rarity, "⚫")
        inventory_text += f"{emoji} {rarity}: {count} шт.\n"
    
    inventory_text += "\n📦 Предметы:\n"
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    valid_items = [item for item in inventory if isinstance(item, dict)]
    
    for idx, item in enumerate(valid_items[start_idx:end_idx], start=start_idx):
        item_name = item.get('name', 'Неизвестный предмет')
        item_rarity = item.get('rarity', 'common')
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(item_rarity, "⚫")
        
        if item.get('on_withdrawal', False):
            inventory_text += f"{idx+1}. {rarity_emoji} {item_name} ({item_rarity}) ⏳\n"
        else:
            inventory_text += f"{idx+1}. {rarity_emoji} {item_name} ({item_rarity})\n"
    
    await message.answer(inventory_text, reply_markup=get_inventory_keyboard(valid_items, page))

@dp.callback_query(F.data.startswith("inventory_page_"))
async def handle_inventory_page(callback: CallbackQuery):
    """Обработчик переключения страниц инвентаря"""
    page = int(callback.data.replace("inventory_page_", ""))
    user_id = callback.from_user.id
    
    if page < 0:
        await callback.answer("❌ Это первая страница")
        return
    
    user = UserManager.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    inventory = user.get("inventory", [])
    items_per_page = 10
    total_pages = (len(inventory) + items_per_page - 1) // items_per_page
    
    if page >= total_pages:
        await callback.answer("❌ Это последняя страница")
        return
    
    await show_inventory_callback(callback, page)

async def show_inventory_callback(callback: CallbackQuery, page: int = 0):
    """Показать инвентарь через callback"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    inventory = user.get("inventory", [])
    
    if not inventory:
        await callback.message.edit_text(
            "🎒 Ваш инвентарь пуст\n"
            "📦 Откройте кейсы, чтобы получить предметы!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎰 К кейсам", callback_data="back_to_cases"),
                InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_main")
            ]])
        )
        await callback.answer()
        return
    
    rarity_count = {}
    items_on_withdrawal = 0
    
    for item in inventory:
        if isinstance(item, dict):
            rarity = item.get("rarity", "unknown")
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            if item.get('on_withdrawal', False):
                items_on_withdrawal += 1
    
    items_per_page = 10
    total_pages = (len(inventory) + items_per_page - 1) // items_per_page
    
    inventory_text = f"🎒 Ваш инвентарь ({len(inventory)} предметов)"
    
    if total_pages > 1:
        inventory_text += f" (Страница {page + 1}/{total_pages})"
    
    inventory_text += ":\n\n"
    
    if items_on_withdrawal > 0:
        inventory_text += f"⏳ На выводе: {items_on_withdrawal} предметов\n\n"
    
    for rarity, count in rarity_count.items():
        emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(rarity, "⚫")
        inventory_text += f"{emoji} {rarity}: {count} шт.\n"
    
    inventory_text += "\n📦 Предметы:\n"
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    valid_items = [item for item in inventory if isinstance(item, dict)]
    
    for idx, item in enumerate(valid_items[start_idx:end_idx], start=start_idx):
        item_name = item.get('name', 'Неизвестный предмет')
        item_rarity = item.get('rarity', 'common')
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }.get(item_rarity, "⚫")
        
        if item.get('on_withdrawal', False):
            inventory_text += f"{idx+1}. {rarity_emoji} {item_name} ({item_rarity}) ⏳\n"
        else:
            inventory_text += f"{idx+1}. {rarity_emoji} {item_name} ({item_rarity})\n"
    
    await callback.message.edit_text(inventory_text, reply_markup=get_inventory_keyboard(valid_items, page))
    await callback.answer()

@dp.callback_query(F.data.startswith("item_"))
async def handle_select_item(callback: CallbackQuery):
    """Обработчик выбора предмета из инвентаря"""
    item_index = int(callback.data.replace("item_", ""))
    user_id = callback.from_user.id
    
    item = UserManager.get_item_by_index(user_id, item_index)
    
    if not item:
        await callback.answer("❌ Предмет не найден")
        return
    
    item_name = item.get('name', 'Неизвестный предмет')
    rarity = item.get('rarity', 'common')
    received_at = item.get('received_at', '')
    
    rarity_emoji = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡"
    }.get(rarity, "⚫")
    
    rarity_text = {
        "common": "Обычный",
        "uncommon": "Необычный",
        "rare": "Редкий",
        "epic": "Эпический",
        "legendary": "Легендарный"
    }.get(rarity, "Неизвестно")
    
    text = (
        f"{rarity_emoji} {item_name}\n"
        f"📊 Редкость: {rarity_text}\n"
        f"📅 Получен: {received_at[:10] if received_at else 'Неизвестно'}\n"
    )
    
    if item.get('chance'):
        text += f"🎯 Шанс выпадения: {item['chance']:.1f}%\n"
    
    if item.get('on_withdrawal', False):
        text += "⏳ Статус: На выводе\n"
    
    text += f"\n🆔 ID: {item.get('item_id', 'Без ID')}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_item_management_keyboard(item_index, item)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("withdraw_"))
async def handle_withdraw_item(callback: CallbackQuery, state: FSMContext):
    """Обработчик вывода предмета"""
    item_index = int(callback.data.replace("withdraw_", ""))
    user_id = callback.from_user.id
    
    item = UserManager.get_item_by_index(user_id, item_index)
    
    if not item:
        await callback.answer("❌ Предмет не найден")
        return
    
    # Проверяем, не на выводе ли уже предмет
    if UserManager.is_item_on_withdrawal(user_id, item.get('item_id', '')):
        await callback.answer("❌ Этот предмет уже на выводе")
        return
    
    await state.update_data(item_index=item_index, item_id=item.get('item_id'))
    
    text = (
        "📤 Вывод предмета\n\n"
        f"🎁 Предмет: {item.get('name', 'Неизвестный предмет')}\n"
        f"📊 Редкость: {item.get('rarity', 'common')}\n\n"
        "Для вывода предмета необходимо указать контактную информацию "
        "(например, ссылку на телеграм, номер кошелька и т.д.):\n\n"
        "Введите ваши контактные данные:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data=f"item_{item_index}"))
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(UserWithdrawStates.waiting_contact_info)
    await callback.answer()

@dp.message(UserWithdrawStates.waiting_contact_info)
async def handle_withdraw_contact_info(message: types.Message, state: FSMContext):
    """Обработка контактной информации для вывода"""
    contact_info = message.text.strip()
    data = await state.get_data()
    item_index = data.get('item_index')
    user_id = message.from_user.id
    
    item = UserManager.get_item_by_index(user_id, item_index)
    
    if not item:
        await message.answer("❌ Предмет не найден")
        await state.clear()
        return
    
    if not contact_info:
        await message.answer("❌ Контактная информация не может быть пустой. Попробуйте еще раз:")
        return
    
    # Создаем заявку на вывод
    withdrawal_id = WithdrawalManager.create_withdrawal(user_id, item, contact_info)
    
    if withdrawal_id:
        text = (
            "✅ Заявка на вывод создана!\n\n"
            f"🎁 Предмет: {item.get('name', 'Неизвестный предмет')}\n"
            f"📞 Контакты: {contact_info}\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📋 ID заявки: {withdrawal_id}\n\n"
            "Администратор рассмотрит вашу заявку в ближайшее время. "
            "Статус заявки можно отслеживать."
        )
    else:
        text = "❌ Не удалось создать заявку на вывод. Предмет уже на выводе."
    
    await message.answer(text, reply_markup=get_main_keyboard())
    await state.clear()

@dp.callback_query(F.data.startswith("delete_"))
async def handle_delete_item(callback: CallbackQuery):
    """Обработчик удаления предмета"""
    item_index = int(callback.data.replace("delete_", ""))
    user_id = callback.from_user.id
    
    item = UserManager.get_item_by_index(user_id, item_index)
    
    if not item:
        await callback.answer("❌ Предмет не найден")
        return
    
    # Проверяем, не на выводе ли предмет
    if UserManager.is_item_on_withdrawal(user_id, item.get('item_id', '')):
        await callback.answer("❌ Нельзя удалить предмет, который на выводе")
        return
    
    # Удаляем предмет
    removed_item = UserManager.remove_from_inventory(user_id, item.get('item_id', str(item_index)))
    
    if removed_item:
        text = f"🗑️ Предмет '{removed_item.get('name', 'Неизвестный предмет')}' удален из инвентаря."
    else:
        text = "❌ Не удалось удалить предмет."
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎒 В инвентарь", callback_data="open_inventory"),
            InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_main")
        ]])
    )
    await callback.answer()

@dp.callback_query(F.data == "open_inventory")
async def handle_open_inventory(callback: CallbackQuery):
    """Открывает инвентарь"""
    await show_inventory_callback(callback, 0)

# Промокоды
@dp.message(F.text == "🎁 Активировать промокод")
async def handle_activate_promo(message: types.Message, state: FSMContext):
    """Обработчик кнопки активации промокода"""
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    await message.answer(
        "🎁 Активация промокода\n\n"
        "Введите промокод:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]])
    )
    await state.set_state(PromoStates.waiting_promo_code)

@dp.message(PromoStates.waiting_promo_code)
async def handle_promo_code_input(message: types.Message, state: FSMContext):
    """Обработка ввода промокода"""
    promocode = message.text.strip()
    user_id = message.from_user.id
    
    if not promocode:
        await message.answer("❌ Промокод не может быть пустым. Попробуйте еще раз:")
        return
    
    result = PromoCodeManager.activate_promocode(user_id, promocode)
    
    if result["success"]:
        await message.answer(
            result["message"],
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            result["message"] + "\n\nПопробуйте другой промокод:"
        )
        return
    
    await state.clear()

# Обработчики для админ-управления кейсами
@dp.callback_query(F.data == "admin_cases")
async def handle_admin_cases(callback: CallbackQuery):
    """Управление кейсами в админ-панели"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    cases = CaseManager.get_all_cases()
    
    total_cases = len(cases)
    limited_cases = sum(1 for case in cases.values() if case.get("is_limited", False))
    total_opens = sum(case.get("total_opens", 0) for case in cases.values())
    
    text = (
        "🎰 Управление кейсами\n\n"
        f"📦 Всего кейсов: {total_cases}\n"
        f"🔴 Ограниченных: {limited_cases}\n"
        f"📊 Всего открытий: {total_opens}\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_cases_admin_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_case_settings")
async def handle_admin_case_settings(callback: CallbackQuery, state: FSMContext):
    """Настройки ограничений кейсов"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    cases = CaseManager.get_all_cases()
    
    text = "⚙️ Настройки ограничений кейсов\n\n"
    text += "Введите ID кейса для изменения ограничений:\n\n"
    
    for case_id, case_data in cases.items():
        if case_data.get("is_limited", False):
            opens_left = case_data.get("opens_left", 0)
            total_opens = case_data.get("total_opens", 0)
            max_opens = case_data.get("max_opens", 0)
            text += f"🔴 {case_id} - {case_data['name']} (Осталось: {opens_left}/{max_opens}, Открыто: {total_opens})\n"
        else:
            text += f"🟢 {case_id} - {case_data['name']} (Без ограничений)\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    await state.set_state(AdminStates.waiting_case_data)
    await state.update_data(action="case_quantity")
    await callback.answer()

@dp.message(AdminStates.waiting_case_data)
async def handle_case_data_input(message: types.Message, state: FSMContext):
    """Обработка ввода данных для кейса"""
    data = await state.get_data()
    action = data.get("action")
    
    if action == "case_quantity":
        # Изменение ограничений кейса
        case_id = message.text.strip()
        case = CaseManager.get_case(case_id)
        
        if not case:
            await message.answer("❌ Кейс не найден. Попробуйте еще раз:")
            return
        
        await state.update_data(case_id=case_id)
        
        if case.get("is_limited", False):
            opens_left = case.get("opens_left", 0)
            max_opens = case.get("max_opens", 0)
            await message.answer(
                f"🔴 Кейс: {case['name']}\n"
                f"Текущие ограничения: {opens_left}/{max_opens}\n\n"
                "Введите новое максимальное количество открытий (0 для снятия ограничений):"
            )
        else:
            await message.answer(
                f"🟢 Кейс: {case['name']}\n"
                "Текущие ограничения: Без ограничений\n\n"
                "Введите максимальное количество открытий (0 для сохранения без ограничений):"
            )
        
        await state.set_state(AdminStates.waiting_case_quantity)
    elif action == "edit_case":
        # Редактирование кейса (можно расширить)
        await message.answer("Функция редактирования кейса в разработке")
        await state.clear()

@dp.message(AdminStates.waiting_case_quantity)
async def handle_case_quantity_input(message: types.Message, state: FSMContext):
    """Обработка ввода количества открытий для кейса"""
    try:
        max_opens = int(message.text)
        data = await state.get_data()
        case_id = data.get("case_id")
        
        cases = Database.load_cases()
        if case_id not in cases:
            await message.answer("❌ Кейс не найден")
            await state.clear()
            return
        
        case = cases[case_id]
        
        if max_opens <= 0:
            # Снимаем ограничения
            case["is_limited"] = False
            case["max_opens"] = None
            case["opens_left"] = None
            await message.answer(f"✅ Ограничения сняты с кейса {case['name']}")
        else:
            # Устанавливаем новые ограничения
            current_total_opens = case.get("total_opens", 0)
            opens_left = max_opens - current_total_opens
            
            if opens_left < 0:
                opens_left = 0
            
            case["is_limited"] = True
            case["max_opens"] = max_opens
            case["opens_left"] = opens_left
            
            await message.answer(
                f"✅ Ограничения установлены для кейса {case['name']}\n\n"
                f"📊 Максимум открытий: {max_opens}\n"
                f"📈 Осталось открытий: {opens_left}\n"
                f"📊 Уже открыто: {current_total_opens}"
            )
        
        Database.save_cases(cases)
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")

# Основные обработчики callback
@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    if AdminManager.is_admin(user_id):
        await callback.message.edit_text(
            "🎮 Главное меню\n\nВыберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "🎮 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data == "admin_back_main")
async def handle_admin_back_main(callback: CallbackQuery):
    """Возврат из админ-панели в главное меню"""
    user_id = callback.from_user.id
    
    if AdminManager.is_admin(user_id):
        await callback.message.edit_text(
            "👑 Админ-панель\n\nВыберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "🎮 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@dp.message(F.text == "🏆 Топ игроков")
async def handle_top_players(message: types.Message):
    """Показать топ игроков"""
    users = Database.load_users()
    
    if not users:
        await message.answer("🏆 Пока нет игроков. Будьте первым!")
        return
    
    # Сортируем по общему капиталу (баланс + вклады)
    sorted_users = []
    for user_data in users.values():
        total_capital = user_data.get("balance", 0) + user_data.get("deposit_balance", 0)
        sorted_users.append({
            "username": user_data.get("username", f"user_{user_data['user_id']}"),
            "balance": user_data.get("balance", 0),
            "deposit_balance": user_data.get("deposit_balance", 0),
            "total_capital": total_capital,
            "cases_opened": user_data.get("cases_opened", 0)
        })
    
    sorted_users.sort(key=lambda x: x["total_capital"], reverse=True)
    
    text = "🏆 Топ игроков по капиталу:\n\n"
    
    for i, user in enumerate(sorted_users[:10], 1):
        text += f"{i}. @{user['username']}\n"
        text += f"   💰 Баланс: {user['balance']} atm\n"
        text += f"   🏦 На вкладе: {user['deposit_balance']} atm\n"
        text += f"   📊 Всего: {user['total_capital']} atm\n"
        text += f"   📦 Кейсов: {user['cases_opened']}\n\n"
    
    await message.answer(text)

@dp.message(F.text == "📊 Статистика")
async def handle_stats(message: types.Message):
    """Показать статистику бота"""
    if not AdminManager.is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав доступа к статистике")
        return
    
    users = Database.load_users()
    cases = Database.load_cases()
    withdrawals = Database.load_withdrawals()
    promocodes = Database.load_promocodes()
    settings = DepositManager.get_settings()
    
    total_users = len(users)
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_deposits = sum(user.get("deposit_balance", 0) for user in users.values())
    total_capital = total_balance + total_deposits
    total_cases_opened = sum(user.get("cases_opened", 0) for user in users.values())
    total_items = sum(len(user.get("inventory", [])) for user in users.values())
    
    pending_withdrawals = sum(1 for w in withdrawals.values() if w.get("status") == "pending")
    approved_withdrawals = sum(1 for w in withdrawals.values() if w.get("status") == "approved")
    rejected_withdrawals = sum(1 for w in withdrawals.values() if w.get("status") == "rejected")
    
    total_promocodes = len(promocodes)
    active_promocodes = sum(1 for p in promocodes.values() if p.get("is_active", True))
    total_promo_amount = sum(p.get("amount", 0) for p in promocodes.values())
    total_promo_used = sum(p.get("used_count", 0) for p in promocodes.values())
    
    users_with_deposits = sum(1 for user in users.values() if user.get("deposit_balance", 0) > 0)
    total_deposit_profit = sum(user.get("deposit_profit", 0) for user in users.values())
    monthly_deposit_profit = total_deposits * (settings.get("deposit_percent", 5.0) / 100)
    
    text = (
        "📊 Статистика бота:\n\n"
        f"👥 Пользователи: {total_users}\n"
        f"💰 Общий баланс: {total_balance} atm\n"
        f"🏦 На вкладах: {total_deposits:.2f} atm\n"
        f"📊 Общий капитал: {total_capital:.2f} atm\n"
        f"📦 Открыто кейсов: {total_cases_opened}\n"
        f"🎒 Всего предметов: {total_items}\n\n"
        f"📤 Заявки на вывод:\n"
        f"⏳ Ожидают: {pending_withdrawals}\n"
        f"✅ Одобрено: {approved_withdrawals}\n"
        f"❌ Отклонено: {rejected_withdrawals}\n\n"
        f"🎁 Промокоды:\n"
        f"📋 Всего: {total_promocodes}\n"
        f"✅ Активных: {active_promocodes}\n"
        f"💰 Общая сумма: {total_promo_amount} atm\n"
        f"👥 Активировано раз: {total_promo_used}\n\n"
        f"🏦 Вклады:\n"
        f"👥 Вкладчиков: {users_with_deposits}\n"
        f"💰 Процентная ставка: {settings.get('deposit_percent', 5.0)}%\n"
        f"💎 Общая прибыль: {total_deposit_profit:.2f} atm\n"
        f"📈 Месячная прибыль: {monthly_deposit_profit:.2f} atm\n\n"
        f"📦 Доступно кейсов: {len(cases)}"
    )
    
    await message.answer(text)

# Команды для тестирования
@dp.message(Command("add_money"))
async def cmd_add_money(message: types.Message):
    """Добавить деньги для тестирования"""
    user_id = message.from_user.id
    UserManager.add_balance(user_id, 1000)
    user = UserManager.get_user(user_id)
    await message.answer(f"✅ Добавлено 1000 atm. Новый баланс: {user['balance']}")

@dp.message(Command("accrue_profit"))
async def cmd_accrue_profit(message: types.Message):
    """Начислить проценты по вкладам (для тестирования)"""
    if not AdminManager.is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав доступа к этой команде")
        return
    
    total_profit, users_count = DepositManager.calculate_profit_for_all_users()
    await message.answer(f"✅ Начислено {total_profit:.2f} atm {users_count} пользователям")

async def main():
    """Основная функция"""
    if not os.path.exists(CASES_DB_FILE):
        init_default_cases()
        logger.info("Создана база данных кейсов")
    
    # Проверяем, что файлы базы данных существуют
    for file in [USERS_DB_FILE, WITHDRAWALS_DB_FILE, ADMINS_FILE, PROMOCODES_FILE, DEPOSITS_FILE, SETTINGS_FILE]:
        if not os.path.exists(file):
            if file == ADMINS_FILE:
                Database.save_admins([ADMIN_ID])
            elif file == SETTINGS_FILE:
                Database.load_settings()
                logger.info("Созданы настройки по умолчанию")
            elif file == DEPOSITS_FILE:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                logger.info("Создан файл вкладов")
            else:
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump({} if file != ADMINS_FILE else [], f, ensure_ascii=False, indent=2)
            logger.info(f"Создан файл: {file}")
    
    cleanup_inventory()
    
    logger.info("Бот запускается...")
    logger.info(f"Основной админ: {ADMIN_ID}")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    BOT_TOKEN = "8148376386:AAHVVNm3Jt4Iqp16ZIAXDzOAI-jV_Ne_hlQ"
    ADMIN_ID = 6539341659
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or ADMIN_ID == 123456789:
        print("⚠️  ВНИМАНИЕ: Необходимо настроить бота!")
        print("\n1. Получите токен бота у @BotFather")
        print("2. Узнайте свой Telegram ID через @userinfobot")
        print("3. Замените значения в коде:")
        print(f"   BOT_TOKEN = \"{BOT_TOKEN}\"")
        print(f"   ADMIN_ID = {ADMIN_ID}")
    else:
        asyncio.run(main())

