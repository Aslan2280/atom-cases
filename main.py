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
DEPOSITS_FILE = 'deposits.json'  # Новый файл для вкладов
SETTINGS_FILE = 'settings.json'  # Новый файл для настроек

# Токен бота (замените на свой)
BOT_TOKEN = "8148376386:AAHVVNm3Jt4Iqp16ZIAXDzOAI-jV_Ne_hlQ"

# ID админа (замените на свой)
ADMIN_ID = 6539341659  # Ваш Telegram ID

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
    waiting_deposit_percent = State()  # Новое состояние для изменения процента
    waiting_deposit_amount = State()  # Новое состояние для вклада

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
        return [ADMIN_ID]  # По умолчанию основной админ
    
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
        # Настройки по умолчанию
        default_settings = {
            "deposit_percent": 5.0,  # 5% в месяц по умолчанию
            "min_deposit_amount": 50,  # Минимальная сумма вклада
            "deposit_enabled": True  # Включены ли вклады
        }
        Database.save_settings(default_settings)
        return default_settings
    
    @staticmethod
    def save_settings(settings: Dict) -> None:
        """Сохранить настройки"""
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

def init_default_cases():
    """Инициализировать кейсы по умолчанию"""
    cases = {
        "common_case": {
            "name": "📦 Обычный кейс",
            "description": "Содержит обычные предметы",
            "price": 100,
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
            "items": [
                {"id": "sword_rare", "name": "⚔️ Редкий меч", "rarity": "rare", "chance": 40.0},
                {"id": "shield_epic", "name": "🛡️ Эпический щит", "rarity": "epic", "chance": 30.0},
                {"id": "armor_epic", "name": "🥋 Эпическая броня", "rarity": "epic", "chance": 20.0},
                {"id": "artifact_legendary", "name": "💎 Легендарный артефакт", "rarity": "legendary", "chance": 8.0},
                {"id": "sword_legendary", "name": "🗡️ Легендарный меч", "rarity": "legendary", "chance": 2.0}
            ]
        }
    }
    
    # Сохраняем кейсы в файл
    with open(CASES_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    
    logger.info("База данных кейсов инициализирована")

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
            "balance": 1000,  # Начальный баланс
            "deposit_balance": 0,  # Новое поле: баланс на вкладе
            "total_deposited": 0,  # Новое поле: всего внесено на вклады
            "total_withdrawn_from_deposit": 0,  # Новое поле: всего выведено с вкладов
            "deposit_profit": 0,  # Новое поле: прибыль с вкладов
            "inventory": [],
            "created_at": datetime.now().isoformat(),
            "cases_opened": 0,
            "withdrawals_count": 0,
            "total_withdrawn": 0,
            "used_promocodes": [],
            "items_on_withdrawal": [],
            "deposits": []  # Новое поле: история вкладов
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
                "type": deposit_type,  # deposit, withdraw, profit
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
    def open_case(case_id: str, user_id: int) -> Optional[Dict]:
        """Открыть кейс и получить предмет"""
        case = CaseManager.get_case(case_id)
        if not case:
            return None
        
        user = UserManager.get_user(user_id)
        if not user:
            return None
        
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
            
            user["cases_opened"] = user.get("cases_opened", 0) + 1
            UserManager.update_user(user_id, {"cases_opened": user["cases_opened"]})
            
            return selected_item
        
        return None

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
            promocode = PromoCodeManager.generate_promocode()
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
    builder.add(KeyboardButton(text="🏦 Вклады"))  # Новая кнопка
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
    builder.add(InlineKeyboardButton(text="🏦 Управление вкладами", callback_data="admin_deposits"))  # Новая кнопка
    builder.add(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"))
    builder.add(InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_back_main"))
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
        builder.add(InlineKeyboardButton(
            text=f"{case_data['name']} - {case_data['price']} atm",
            callback_data=f"case_{case_id}"
        ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_inventory_keyboard(items):
    """Клавиатура для инвентаря"""
    builder = InlineKeyboardBuilder()
    
    for idx, item in enumerate(items[:10]):
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
        
        builder.add(InlineKeyboardButton(
            text=f"{emoji} {item_name}",
            callback_data=f"item_{idx}"
        ))
    
    if len(items) > 10:
        builder.add(InlineKeyboardButton(
            text="📄 Следующая страница",
            callback_data="inventory_next"
        ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_item_management_keyboard(item_index: str, item_data: Dict):
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
        return
    
    text = (
        "💸 Вывод средств с вклада\n\n"
        f"🏦 Доступно для вывода: {deposit_balance} atm\n"
        f"💰 Ваш баланс: {user['balance']} atm\n\n"
        "Введите сумму для вывода с вклада:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    await state.set_state(DepositStates.waiting_withdraw_deposit)

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
        return
    
    text = "📊 История операций по вкладу:\n\n"
    
    # Показываем последние 10 операций
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

# Обработчики админ-панели для вкладов
@dp.callback_query(F.data == "admin_deposits")
async def handle_admin_deposits(callback: CallbackQuery):
    """Управление вкладами в админ-панели"""
    if not AdminManager.is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав доступа")
        return
    
    settings = DepositManager.get_settings()
    users = Database.load_users()
    
    # Статистика по вкладам
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
    
    # Сортируем пользователей по сумме на вкладе
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

# Обработчики админ-панели (остальные)
@dp.callback_query(F.data == "admin_back_panel")
async def handle_admin_back_panel(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    await callback.message.edit_text(
        "👑 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )

@dp.callback_query(F.data == "admin_add_balance")
async def handle_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса пользователю"""
    await callback.message.edit_text(
        "💰 Пополнение баланса\n\n"
        "Введите ID пользователя, которому нужно пополнить баланс:",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_user_id)

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
            # Это для изменения минимальной суммы вклада
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

# Остальные обработчики (промокоды, кейсы, инвентарь и т.д.)
@dp.message(F.text == "🎰 Кейсы")
async def handle_cases_button(message: types.Message):
    """Обработчик кнопки Кейсы"""
    await show_cases_menu(message)

@dp.message(F.text == "💰 Баланс")
async def handle_balance_button(message: types.Message):
    """Обработчик кнопки Баланс"""
    await cmd_balance(message)

@dp.message(F.text == "🎒 Инвентарь")
async def handle_inventory_button(message: types.Message):
    """Обработчик кнопки Инвентарь"""
    await show_inventory(message)

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
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await state.set_state(PromoStates.waiting_promo_code)

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
        cases_text += (
            f"{case_data['name']}\n"
            f"📝 {case_data['description']}\n"
            f"💰 Цена: {case_data['price']} atm\n"
            f"🎁 Предметов: {len(case_data['items'])}\n\n"
        )
    
    cases_text += f"💎 Ваш баланс: {user['balance']} atm"
    
    await message.answer(cases_text, reply_markup=get_cases_keyboard())

async def show_inventory(message: types.Message):
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
    
    inventory_text = f"🎒 Ваш инвентарь ({len(inventory)} предметов):\n\n"
    
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
    
    inventory_text += "\n📦 Последние предметы:\n"
    valid_items = [item for item in inventory if isinstance(item, dict)]
    for item in valid_items[-5:]:
        item_name = item.get('name', 'Неизвестный предмет')
        item_rarity = item.get('rarity', 'common')
        if item.get('on_withdrawal', False):
            inventory_text += f"• {item_name} ({item_rarity}) ⏳\n"
        else:
            inventory_text += f"• {item_name} ({item_rarity})\n"
    
    await message.answer(inventory_text, reply_markup=get_inventory_keyboard(valid_items))

# ... (остальные обработчики остаются без изменений, как в предыдущем коде)

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

# Команда для тестирования
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
                # Создаем настройки по умолчанию
                Database.load_settings()
                logger.info("Созданы настройки по умолчанию")
            elif file == DEPOSITS_FILE:
                # Создаем пустой файл вкладов
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













































        