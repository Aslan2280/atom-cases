import asyncio
import json
import os
import random
import logging
from typing import Dict, List, Optional
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Файлы базы данных
USERS_DB_FILE = 'users.json'
CASES_DB_FILE = 'cases.json'
WITHDRAWALS_DB_FILE = 'withdrawals.json'
ADMINS_FILE = 'admins.json'
PROMOCODES_FILE = 'promocodes.json'
DEPOSITS_FILE = 'deposits.json'
SETTINGS_FILE = 'settings.json'
STOCKS_FILE = 'stocks.json'
USER_STOCKS_FILE = 'user_stocks.json'

# Токен бота и ID админа - ЗАМЕНИТЕ НА СВОИ!
BOT_TOKEN = "8148376386:AAHVVNm3Jt4Iqp16ZIAXDzOAI-jV_Ne_hlQ"  # Ваш токен
ADMIN_ID = 6539341659  # Ваш ID

# Классы состояний
class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_withdrawal_action = State()
    waiting_case_data = State()
    waiting_promo_code = State()
    waiting_promo_amount = State()
    waiting_promo_uses = State()
    waiting_deposit_percent = State()
    waiting_deposit_amount = State()
    waiting_case_quantity = State()
    waiting_new_stock = State()
    waiting_stock_name = State()
    waiting_stock_price = State()
    waiting_stock_shares = State()
    waiting_price_adjust = State()

class UserWithdrawStates(StatesGroup):
    waiting_contact_info = State()

class PromoStates(StatesGroup):
    waiting_promo_code = State()

class DepositStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_withdraw_deposit = State()

class StockStates(StatesGroup):
    waiting_buy_quantity = State()
    waiting_sell_quantity = State()

class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class Database:
    @staticmethod
    def load_users() -> Dict:
        if os.path.exists(USERS_DB_FILE):
            try:
                with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки users.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_users(users: Dict) -> None:
        try:
            with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения users.json: {e}")
    
    @staticmethod
    def load_cases() -> Dict:
        if os.path.exists(CASES_DB_FILE):
            try:
                with open(CASES_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки cases.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_cases(cases: Dict) -> None:
        try:
            with open(CASES_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(cases, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения cases.json: {e}")
    
    @staticmethod
    def load_withdrawals() -> Dict:
        if os.path.exists(WITHDRAWALS_DB_FILE):
            try:
                with open(WITHDRAWALS_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки withdrawals.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_withdrawals(withdrawals: Dict) -> None:
        try:
            with open(WITHDRAWALS_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(withdrawals, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения withdrawals.json: {e}")
    
    @staticmethod
    def load_admins() -> List[int]:
        if os.path.exists(ADMINS_FILE):
            try:
                with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки admins.json, возвращаю список с админом по умолчанию")
                return [ADMIN_ID]
        return [ADMIN_ID]
    
    @staticmethod
    def save_admins(admins: List[int]) -> None:
        try:
            with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
                json.dump(admins, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения admins.json: {e}")
    
    @staticmethod
    def load_promocodes() -> Dict:
        if os.path.exists(PROMOCODES_FILE):
            try:
                with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки promocodes.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_promocodes(promocodes: Dict) -> None:
        try:
            with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(promocodes, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения promocodes.json: {e}")
    
    @staticmethod
    def load_deposits() -> Dict:
        if os.path.exists(DEPOSITS_FILE):
            try:
                with open(DEPOSITS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки deposits.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_deposits(deposits: Dict) -> None:
        try:
            with open(DEPOSITS_FILE, 'w', encoding='utf-8') as f:
                json.dump(deposits, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения deposits.json: {e}")
    
    @staticmethod
    def load_settings() -> Dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки settings.json, создаю настройки по умолчанию")
        default_settings = {
            "deposit_percent": 5.0,
            "min_deposit_amount": 50,
            "deposit_enabled": True
        }
        Database.save_settings(default_settings)
        return default_settings
    
    @staticmethod
    def save_settings(settings: Dict) -> None:
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения settings.json: {e}")
    
    @staticmethod
    def load_stocks() -> Dict:
        if os.path.exists(STOCKS_FILE):
            try:
                with open(STOCKS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки stocks.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_stocks(stocks: Dict) -> None:
        try:
            with open(STOCKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(stocks, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения stocks.json: {e}")
    
    @staticmethod
    def load_user_stocks() -> Dict:
        if os.path.exists(USER_STOCKS_FILE):
            try:
                with open(USER_STOCKS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.error("Ошибка загрузки user_stocks.json, возвращаю пустой словарь")
                return {}
        return {}
    
    @staticmethod
    def save_user_stocks(user_stocks: Dict) -> None:
        try:
            with open(USER_STOCKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(user_stocks, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка сохранения user_stocks.json: {e}")

def init_default_cases():
    cases = {
        "adobe_animate_case": {
            "name": "🎨 Adobe Animate Case",
            "description": "Шанс выиграть Adobe Animate NFT!",
            "price": 10,
            "max_opens": 25,
            "opens_left": 24,
            "total_opens": 1,
            "is_limited": True,
            "items": [
                {"id": "5_atm", "name": "5 ATM", "rarity": "common", "chance": 45.0},
                {"id": "8_atm", "name": "8 ATM", "rarity": "common", "chance": 30.0},
                {"id": "12_atm", "name": "12 ATM", "rarity": "uncommon", "chance": 13.0},
                {"id": "18_atm", "name": "18 ATM", "rarity": "rare", "chance": 7.0},
                {"id": "adobe_animate_nft", "name": "Adobe Animate NFT", "rarity": "legendary", "chance": 5.0}
            ]
        },
        "cpp_new_case": {
            "name": "💻 C++ Новый",
            "description": "Шанс получить легендарный C++ NFT",
            "price": 30,
            "max_opens": 10,
            "opens_left": 9,
            "total_opens": 1,
            "is_limited": True,
            "items": [
                {"id": "10_atm", "name": "10 ATM", "rarity": "common", "chance": 35.0},
                {"id": "20_atm", "name": "20 ATM", "rarity": "common", "chance": 30.0},
                {"id": "30_atm", "name": "30 ATM", "rarity": "uncommon", "chance": 15.0},
                {"id": "50_atm", "name": "50 ATM", "rarity": "rare", "chance": 10.0},
                {"id": "80_atm", "name": "80 ATM", "rarity": "epic", "chance": 7.0},
                {"id": "cpp_nft", "name": "C++ NFT", "rarity": "legendary", "chance": 3.0}
            ]
        },
        "shiba_old_case": {
            "name": "🐕 Shiba Inu",
            "description": "Старые добрые NFT из ранних коллекций",
            "price": 7,
            "max_opens": 50,
            "opens_left": 50,
            "total_opens": 0,
            "is_limited": True,
            "items": [
                {"id": "3_atm", "name": "3 ATM", "rarity": "common", "chance": 40.0},
                {"id": "5_atm", "name": "5 ATM", "rarity": "common", "chance": 25.0},
                {"id": "7_atm", "name": "7 ATM", "rarity": "uncommon", "chance": 15.0},
                {"id": "pixel_shiba_nft", "name": "Pixel Shiba NFT", "rarity": "rare", "chance": 10.0},
                {"id": "atom64_nft", "name": "Atom64 NFT", "rarity": "rare", "chance": 7.0},
                {"id": "atomglide_belarus_nft", "name": "AtomGlide Belarus NFT", "rarity": "legendary", "chance": 3.0}
            ]
        },
        "durov_case": {
            "name": "👨‍💼 Павел Дуров кейс",
            "description": "Шанс выиграть легендарные NFT Дурова",
            "price": 60,
            "max_opens": 20,
            "opens_left": 19,
            "total_opens": 1,
            "is_limited": True,
            "items": [
                {"id": "20_atm", "name": "20 ATM", "rarity": "common", "chance": 35.0},
                {"id": "40_atm", "name": "40 ATM", "rarity": "common", "chance": 25.0},
                {"id": "60_atm", "name": "60 ATM", "rarity": "uncommon", "chance": 15.0},
                {"id": "80_atm", "name": "80 ATM", "rarity": "rare", "chance": 10.0},
                {"id": "100_atm", "name": "100 ATM", "rarity": "epic", "chance": 5.0},
                {"id": "pixel_durov_nft", "name": "Pixel Durov NFT", "rarity": "legendary", "chance": 6.0},
                {"id": "pavel_durov_nft", "name": "Pavel Durov NFT", "rarity": "mythical", "chance": 4.0}
            ]
        }
    }
    
    try:
        with open(CASES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
        logger.info("База данных кейсов инициализирована")
    except IOError as e:
        logger.error(f"Ошибка создания cases.json: {e}")

class StockManager:
    @staticmethod
    def init_default_stocks():
        stocks = {
            "AAPL": {
                "name": "Apple Inc.",
                "price": 150.50,
                "change": 1.2,
                "shares": 10000,
                "sector": "Технологии",
                "volatility": 2.0
            },
            "TSLA": {
                "name": "Tesla Inc.",
                "price": 250.30,
                "change": -0.8,
                "shares": 8000,
                "sector": "Автомобили",
                "volatility": 3.0
            },
            "GOOGL": {
                "name": "Alphabet Inc.",
                "price": 135.75,
                "change": 0.5,
                "shares": 12000,
                "sector": "Технологии",
                "volatility": 1.5
            }
        }
        Database.save_stocks(stocks)
        logger.info("Созданы акции по умолчанию")
        return stocks
    
    @staticmethod
    def update_prices():
        stocks = Database.load_stocks()
        
        if not stocks:
            return stocks
        
        for stock_id, data in stocks.items():
            volatility = data.get("volatility", 2.0)
            change = random.uniform(-volatility, volatility)
            data["price"] = round(data["price"] * (1 + change/100), 2)
            data["change"] = round(change, 2)
        
        Database.save_stocks(stocks)
        logger.info("Цены акций обновлены")
        return stocks
    
    @staticmethod
    def buy_stock(user_id: int, stock_id: str, quantity: int) -> Dict:
        user = UserManager.get_user(user_id)
        stocks = Database.load_stocks()
        user_stocks = Database.load_user_stocks()
        
        if not user or stock_id not in stocks:
            return {"success": False, "message": "❌ Ошибка: акция не найдена"}
        
        stock = stocks[stock_id]
        cost = stock["price"] * quantity
        
        if user["balance"] < cost:
            return {"success": False, "message": f"❌ Недостаточно средств. Нужно: {cost:.2f} atm"}
        
        if stock["shares"] < quantity:
            return {"success": False, "message": f"❌ Недостаточно акций. Доступно: {stock['shares']}"}
        
        UserManager.add_balance(user_id, -cost)
        
        stock["shares"] -= quantity
        stocks[stock_id] = stock
        Database.save_stocks(stocks)
        
        user_id_str = str(user_id)
        if user_id_str not in user_stocks:
            user_stocks[user_id_str] = {}
        
        if stock_id not in user_stocks[user_id_str]:
            user_stocks[user_id_str][stock_id] = 0
        
        user_stocks[user_id_str][stock_id] += quantity
        Database.save_user_stocks(user_stocks)
        
        # Увеличиваем цену при покупке
        stock["price"] = round(stock["price"] * 1.001, 2)
        stocks[stock_id] = stock
        Database.save_stocks(stocks)
        
        return {
            "success": True,
            "message": f"✅ Куплено {quantity} акций {stock_id}\n💵 Стоимость: {cost:.2f} atm\n💰 Новый баланс: {user['balance'] - cost:.2f} atm"
        }
    
    @staticmethod
    def sell_stock(user_id: int, stock_id: str, quantity: int) -> Dict:
        user_stocks = Database.load_user_stocks()
        stocks = Database.load_stocks()
        
        user_id_str = str(user_id)
        
        if user_id_str not in user_stocks or stock_id not in user_stocks[user_id_str]:
            return {"success": False, "message": "❌ У вас нет этих акций"}
        
        if user_stocks[user_id_str][stock_id] < quantity:
            return {"success": False, "message": f"❌ Недостаточно акций. У вас: {user_stocks[user_id_str][stock_id]}"}
        
        stock = stocks[stock_id]
        revenue = stock["price"] * quantity
        
        UserManager.add_balance(user_id, revenue)
        
        user_stocks[user_id_str][stock_id] -= quantity
        if user_stocks[user_id_str][stock_id] == 0:
            del user_stocks[user_id_str][stock_id]
        
        stock["shares"] += quantity
        stocks[stock_id] = stock
        Database.save_stocks(stocks)
        Database.save_user_stocks(user_stocks)
        
        # Уменьшаем цену при продаже
        stock["price"] = round(stock["price"] * 0.999, 2)
        stocks[stock_id] = stock
        Database.save_stocks(stocks)
        
        return {
            "success": True,
            "message": f"✅ Продано {quantity} акций {stock_id}\n💵 Выручка: {revenue:.2f} atm"
        }
    
    @staticmethod
    def get_portfolio(user_id: int) -> Dict:
        user_stocks = Database.load_user_stocks()
        stocks = Database.load_stocks()
        
        user_id_str = str(user_id)
        portfolio = {}
        total_value = 0
        
        if user_id_str in user_stocks:
            for stock_id, quantity in user_stocks[user_id_str].items():
                if stock_id in stocks:
                    stock = stocks[stock_id]
                    value = stock["price"] * quantity
                    portfolio[stock_id] = {
                        "name": stock["name"],
                        "quantity": quantity,
                        "price": stock["price"],
                        "value": value,
                        "change": stock.get("change", 0)
                    }
                    total_value += value
        
        return {"stocks": portfolio, "total_value": total_value}
    
    @staticmethod
    def create_stock(stock_id: str, name: str, price: float, shares: int = 10000):
        stocks = Database.load_stocks()
        
        stocks[stock_id] = {
            "name": name,
            "price": price,
            "change": 0.0,
            "shares": shares,
            "sector": "Общее",
            "volatility": random.uniform(1.0, 3.0)
        }
        
        Database.save_stocks(stocks)
        logger.info(f"Создана акция {stock_id}: {name} по цене {price}")
        return True

def generate_withdrawal_id() -> str:
    timestamp_ms = int(datetime.now().timestamp() * 1000)
    withdrawal_id = f"wd{timestamp_ms}{random.randint(100, 999)}"
    return withdrawal_id

def safe_withdrawal_id(withdrawal_id: str) -> str:
    safe_id = withdrawal_id.replace('.', '_')
    return safe_id

def restore_withdrawal_id(safe_id: str) -> str:
    original_id = safe_id.replace('_', '.')
    return original_id

def cleanup_inventory():
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
                        item["item_id"] = f"item_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
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
    @staticmethod
    def get_user(user_id: int) -> Optional[Dict]:
        users = Database.load_users()
        return users.get(str(user_id))
    
    @staticmethod
    def create_user(user_id: int, username: str = "") -> Dict:
        users = Database.load_users()
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "balance": 0.0,
            "deposit_balance": 0.0,
            "total_deposited": 0.0,
            "total_withdrawn_from_deposit": 0.0,
            "deposit_profit": 0.0,
            "inventory": [],
            "created_at": datetime.now().isoformat(),
            "cases_opened": 0,
            "withdrawals_count": 0,
            "total_withdrawn": 0.0,
            "used_promocodes": [],
            "items_on_withdrawal": [],
            "deposits": [],
            "opened_cases": {}
        }
        
        users[str(user_id)] = user_data
        Database.save_users(users)
        return user_data
    
    @staticmethod
    def update_user(user_id: int, data: Dict):
        users = Database.load_users()
        user_id_str = str(user_id)
        
        if user_id_str in users:
            users[user_id_str].update(data)
            Database.save_users(users)
    
    @staticmethod
    def add_balance(user_id: int, amount: float):
        user = UserManager.get_user(user_id)
        if user:
            user["balance"] = round(user.get("balance", 0) + amount, 2)
            UserManager.update_user(user_id, {"balance": user["balance"]})
    
    @staticmethod
    def add_deposit_balance(user_id: int, amount: float):
        user = UserManager.get_user(user_id)
        if user:
            user["deposit_balance"] = round(user.get("deposit_balance", 0) + amount, 2)
            user["total_deposited"] = round(user.get("total_deposited", 0) + amount, 2)
            UserManager.update_user(user_id, {
                "deposit_balance": user["deposit_balance"],
                "total_deposited": user["total_deposited"]
            })
    
    @staticmethod
    def withdraw_deposit_balance(user_id: int, amount: float) -> bool:
        user = UserManager.get_user(user_id)
        if user and user["deposit_balance"] >= amount:
            user["deposit_balance"] = round(user["deposit_balance"] - amount, 2)
            user["total_withdrawn_from_deposit"] = round(user.get("total_withdrawn_from_deposit", 0) + amount, 2)
            UserManager.update_user(user_id, {
                "deposit_balance": user["deposit_balance"],
                "total_withdrawn_from_deposit": user["total_withdrawn_from_deposit"]
            })
            return True
        return False
    
    @staticmethod
    def add_deposit_profit(user_id: int, amount: float):
        user = UserManager.get_user(user_id)
        if user:
            user["deposit_profit"] = round(user.get("deposit_profit", 0) + amount, 2)
            UserManager.update_user(user_id, {"deposit_profit": user["deposit_profit"]})
    
    @staticmethod
    def add_deposit_record(user_id: int, amount: float, deposit_type: str = "deposit"):
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
        user = UserManager.get_user(user_id)
        if user:
            item_with_date = {
                "name": item.get("name", "Неизвестный предмет"),
                "rarity": item.get("rarity", "common"),
                "id": item.get("id", f"item_{random.randint(10000, 99999)}"),
                "item_id": f"item_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}",
                "received_at": datetime.now().isoformat(),
                "chance": item.get("chance", 0),
                "original_id": item.get("id", ""),
                "on_withdrawal": False
            }
            
            for key, value in item.items():
                if key not in item_with_date:
                    item_with_date[key] = value
            
            if "inventory" not in user:
                user["inventory"] = []
            
            user["inventory"].append(item_with_date)
            UserManager.update_user(user_id, {"inventory": user["inventory"]})
            
            logger.info(f"Добавлен предмет в инвентарь пользователя {user_id}: {item_with_date['name']}")
    
    @staticmethod
    def remove_from_inventory(user_id: int, item_id: str) -> Optional[Dict]:
        user = UserManager.get_user(user_id)
        if user and "inventory" in user:
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
        user = UserManager.get_user(user_id)
        if not user:
            return None
        
        inventory = user.get("inventory", [])
        if 0 <= index < len(inventory):
            return inventory[index]
        return None
    
    @staticmethod
    def mark_item_on_withdrawal(user_id: int, item_id: str):
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "items_on_withdrawal" not in user:
            user["items_on_withdrawal"] = []
        
        if item_id not in user["items_on_withdrawal"]:
            user["items_on_withdrawal"].append(item_id)
            UserManager.update_user(user_id, {"items_on_withdrawal": user["items_on_withdrawal"]})
            
            if "inventory" in user:
                for item in user["inventory"]:
                    if item.get("item_id") == item_id or item.get("id") == item_id:
                        item["on_withdrawal"] = True
                        UserManager.update_user(user_id, {"inventory": user["inventory"]})
                        break
    
    @staticmethod
    def unmark_item_on_withdrawal(user_id: int, item_id: str):
        user = UserManager.get_user(user_id)
        if not user:
            return
        
        if "items_on_withdrawal" in user and item_id in user["items_on_withdrawal"]:
            user["items_on_withdrawal"].remove(item_id)
            UserManager.update_user(user_id, {"items_on_withdrawal": user["items_on_withdrawal"]})
            
            if "inventory" in user:
                for item in user["inventory"]:
                    if item.get("item_id") == item_id or item.get("id") == item_id:
                        item["on_withdrawal"] = False
                        UserManager.update_user(user_id, {"inventory": user["inventory"]})
                        break
    
    @staticmethod
    def is_item_on_withdrawal(user_id: int, item_id: str) -> bool:
        user = UserManager.get_user(user_id)
        if not user:
            return False
        
        if item_id in user.get("items_on_withdrawal", []):
            return True
        
        if "inventory" in user:
            for item in user["inventory"]:
                if (item.get("item_id") == item_id or item.get("id") == item_id):
                    return item.get("on_withdrawal", False)
        
        return False
    
    @staticmethod
    def add_used_promocode(user_id: int, promocode: str):
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
        user = UserManager.get_user(user_id)
        if not user:
            return False
        
        return promocode in user.get("used_promocodes", [])
    
    @staticmethod
    def add_case_opened(user_id: int, case_id: str):
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
    @staticmethod
    def get_settings() -> Dict:
        return Database.load_settings()
    
    @staticmethod
    def update_settings(settings: Dict):
        Database.save_settings(settings)
    
    @staticmethod
    def calculate_monthly_profit(deposit_amount: float) -> float:
        settings = DepositManager.get_settings()
        percent = settings.get("deposit_percent", 5.0)
        return round(deposit_amount * (percent / 100), 2)
    
    @staticmethod
    def make_deposit(user_id: int, amount: float) -> Dict:
        user = UserManager.get_user(user_id)
        if not user:
            return {"success": False, "message": "❌ Пользователь не найден"}
        
        settings = DepositManager.get_settings()
        
        if not settings.get("deposit_enabled", True):
            return {"success": False, "message": "❌ Вклады временно отключены"}
        
        min_amount = settings.get("min_deposit_amount", 50)
        
        if amount < min_amount:
            return {"success": False, "message": f"❌ Минимальная сумма вклада: {min_amount} atm"}
        
        if user["balance"] < amount:
            return {"success": False, "message": f"❌ Недостаточно средств. На балансе: {user['balance']:.2f} atm"}
        
        UserManager.add_balance(user_id, -amount)
        UserManager.add_deposit_balance(user_id, amount)
        UserManager.add_deposit_record(user_id, amount, "deposit")
        
        monthly_profit = DepositManager.calculate_monthly_profit(amount)
        
        return {
            "success": True,
            "message": f"✅ Вклад оформлен!\n\n"
                      f"💰 Сумма вклада: {amount:.2f} atm\n"
                      f"🏦 На вкладе: {user['deposit_balance']:.2f} atm\n"
                      f"💎 Месячная прибыль: {monthly_profit:.2f} atm\n"
                      f"📈 Процентная ставка: {settings.get('deposit_percent', 5.0)}%\n"
                      f"💳 Остаток на балансе: {user['balance']:.2f} atm",
            "monthly_profit": monthly_profit
        }
    
    @staticmethod
    def withdraw_from_deposit(user_id: int, amount: float) -> Dict:
        user = UserManager.get_user(user_id)
        if not user:
            return {"success": False, "message": "❌ Пользователь не найден"}
        
        if user["deposit_balance"] < amount:
            return {"success": False, "message": f"❌ Недостаточно средств на вкладе. Доступно: {user['deposit_balance']:.2f} atm"}
        
        if UserManager.withdraw_deposit_balance(user_id, amount):
            UserManager.add_balance(user_id, amount)
            UserManager.add_deposit_record(user_id, amount, "withdraw")
            
            return {
                "success": True,
                "message": f"✅ Средства выведены с вклада!\n\n"
                          f"💰 Выведено: {amount:.2f} atm\n"
                          f"🏦 Осталось на вкладе: {user['deposit_balance']:.2f} atm\n"
                          f"💳 Баланс: {user['balance']:.2f} atm"
            }
        
        return {"success": False, "message": "❌ Ошибка при выводе средств"}
    
    @staticmethod
    def calculate_profit_for_all_users():
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
                
                UserManager.add_deposit_balance(user_id, profit)
                UserManager.add_deposit_profit(user_id, profit)
                UserManager.add_deposit_record(user_id, profit, "profit")
                
                total_profit += profit
                users_with_profit += 1
        
        logger.info(f"Начислены проценты {users_with_profit} пользователям на общую сумму {total_profit:.2f} atm")
        return total_profit, users_with_profit
    
    @staticmethod
    def get_user_deposit_info(user_id: int) -> Dict:
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
            "min_amount": settings.get("min_deposit_amount", 50),
            "enabled": settings.get("deposit_enabled", True)
        }

class WithdrawalManager:
    @staticmethod
    def create_withdrawal(user_id: int, item: Dict, contact_info: str) -> Optional[str]:
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
        withdrawals = Database.load_withdrawals()
        return withdrawals.get(withdrawal_id)
    
    @staticmethod
    def get_pending_withdrawals() -> List[Dict]:
        withdrawals = Database.load_withdrawals()
        return [wd for wd in withdrawals.values() if wd.get("status") == "pending"]
    
    @staticmethod
    def update_withdrawal(withdrawal_id: str, data: Dict):
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
    
    @staticmethod
    def get_user_withdrawals(user_id: int) -> List[Dict]:
        withdrawals = Database.load_withdrawals()
        user_wds = []
        for wd in withdrawals.values():
            if wd.get("user_id") == user_id:
                user_wds.append(wd)
        return user_wds

class AdminManager:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        admins = Database.load_admins()
        return user_id in admins
    
    @staticmethod
    def add_admin(user_id: int) -> bool:
        admins = Database.load_admins()
        if user_id not in admins:
            admins.append(user_id)
            Database.save_admins(admins)
            return True
        return False
    
    @staticmethod
    def remove_admin(user_id: int) -> bool:
        admins = Database.load_admins()
        if user_id in admins:
            admins.remove(user_id)
            Database.save_admins(admins)
            return True
        return False

class CaseManager:
    @staticmethod
    def get_case(case_id: str) -> Optional[Dict]:
        cases = Database.load_cases()
        return cases.get(case_id)
    
    @staticmethod
    def get_all_cases() -> Dict:
        return Database.load_cases()
    
    @staticmethod
    def can_open_case(case_id: str) -> Dict:
        case = CaseManager.get_case(case_id)
        if not case:
            return {"can_open": False, "reason": "Кейс не найден"}
        
        if case.get("is_limited", False):
            opens_left = case.get("opens_left", 0)
            if opens_left <= 0:
                return {"can_open": False, "reason": "Кейс закончился"}
        
        return {"can_open": True, "reason": ""}
    
    @staticmethod
    def update_case_opens(case_id: str):
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
            
            CaseManager.update_case_opens(case_id)
            
            return selected_item
        
        return {"error": "Не удалось выбрать предмет"}

class PromoCodeManager:
    @staticmethod
    def generate_promocode(length: int = 8) -> str:
        characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(characters) for _ in range(length))
    
    @staticmethod
    def create_promocode(amount: int, max_uses: int = 1, creator_id: int = None) -> str:
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
        promocodes = Database.load_promocodes()
        return promocodes.get(promocode.upper())
    
    @staticmethod
    def activate_promocode(user_id: int, promocode: str) -> Dict:
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
                      f"💰 Ваш баланс: {user['balance']:.2f} atm\n"
                      f"📊 Промокод использован: {promo_data['used_count']}/{promo_data['max_uses']}",
            "amount": promo_data["amount"]
        }
    
    @staticmethod
    def deactivate_promocode(promocode: str) -> bool:
        promocodes = Database.load_promocodes()
        promocode = promocode.upper()
        
        if promocode in promocodes:
            promocodes[promocode]["is_active"] = False
            Database.save_promocodes(promocodes)
            return True
        return False
    
    @staticmethod
    def delete_promocode(promocode: str) -> bool:
        promocodes = Database.load_promocodes()
        promocode = promocode.upper()
        
        if promocode in promocodes:
            del promocodes[promocode]
            Database.save_promocodes(promocodes)
            return True
        return False
    
    @staticmethod
    def get_all_promocodes() -> Dict:
        return Database.load_promocodes()
    
    @staticmethod
    def get_active_promocodes() -> Dict:
        promocodes = Database.load_promocodes()
        return {k: v for k, v in promocodes.items() if v.get("is_active", True)}

# Инициализация бота
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Клавиатуры
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎰 Кейсы"))
    builder.add(KeyboardButton(text="📈 Акции"))
    builder.add(KeyboardButton(text="🎒 Инвентарь"))
    builder.add(KeyboardButton(text="💰 Баланс"))
    builder.add(KeyboardButton(text="🏦 Вклады"))
    builder.add(KeyboardButton(text="🎁 Активировать промокод"))
    builder.add(KeyboardButton(text="🏆 Топ игроков"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="👑 Админ панель"))
    builder.add(KeyboardButton(text="🎰 Кейсы"))
    builder.add(KeyboardButton(text="📈 Акции"))
    builder.add(KeyboardButton(text="🎒 Инвентарь"))
    builder.add(KeyboardButton(text="💰 Баланс"))
    builder.add(KeyboardButton(text="🏦 Вклады"))
    builder.add(KeyboardButton(text="🎁 Активировать промокод"))
    builder.add(KeyboardButton(text="📊 Статистика"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="admin_add_balance"))
    builder.add(InlineKeyboardButton(text="📊 Статистика пользователя", callback_data="admin_user_stats"))
    builder.add(InlineKeyboardButton(text="📋 Заявки на вывод", callback_data="admin_withdrawals"))
    builder.add(InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list"))
    builder.add(InlineKeyboardButton(text="🎰 Управление кейсами", callback_data="admin_cases"))
    builder.add(InlineKeyboardButton(text="📈 Управление акциями", callback_data="admin_stocks"))
    builder.add(InlineKeyboardButton(text="🎁 Управление промокодами", callback_data="admin_promocodes"))
    builder.add(InlineKeyboardButton(text="🏦 Управление вкладами", callback_data="admin_deposits"))
    builder.add(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"))
    builder.add(InlineKeyboardButton(text="🔙 В главное меню", callback_data="admin_back_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_deposits_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Положить на вклад", callback_data="deposit_make"))
    builder.add(InlineKeyboardButton(text="💸 Вывести с вклада", callback_data="deposit_withdraw"))
    builder.add(InlineKeyboardButton(text="📊 Информация о вкладе", callback_data="deposit_info"))
    builder.add(InlineKeyboardButton(text="📈 История операций", callback_data="deposit_history"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_stocks_keyboard():
    stocks = Database.load_stocks()
    builder = InlineKeyboardBuilder()
    
    for stock_id, data in stocks.items():
        change_emoji = "📈" if data.get("change", 0) >= 0 else "📉"
        change_text = f"+{data.get('change', 0)}%" if data.get("change", 0) >= 0 else f"{data.get('change', 0)}%"
        builder.add(InlineKeyboardButton(
            text=f"{change_emoji} {stock_id}: {data['price']} atm ({change_text})",
            callback_data=f"stock_{stock_id}"
        ))
    
    builder.add(InlineKeyboardButton(text="📊 Мой портфель", callback_data="my_portfolio"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить цены", callback_data="refresh_stocks"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def get_stock_detail_keyboard(stock_id: str):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Купить", callback_data=f"buy_{stock_id}"))
    builder.add(InlineKeyboardButton(text="💸 Продать", callback_data=f"sell_{stock_id}"))
    builder.add(InlineKeyboardButton(text="📊 Информация", callback_data=f"info_{stock_id}"))
    builder.add(InlineKeyboardButton(text="🔙 К списку акций", callback_data="back_to_stocks"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_stocks_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Создать акцию", callback_data="admin_create_stock"))
    builder.add(InlineKeyboardButton(text="📋 Список акций", callback_data="admin_list_stocks"))
    builder.add(InlineKeyboardButton(text="💰 Изменить цену", callback_data="admin_change_stock_price"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить цены", callback_data="admin_update_prices"))
    builder.add(InlineKeyboardButton(text="📊 Статистика рынка", callback_data="admin_stocks_stats"))
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

def get_cases_keyboard():
    cases = CaseManager.get_all_cases()
    builder = InlineKeyboardBuilder()
    
    for case_id, case_data in cases.items():
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
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="📝 Комментарий", callback_data=f"comment_wd_{safe_withdrawal_id(withdrawal_id)}"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_withdrawals"))
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_back_panel"))
    builder.adjust(1)
    return builder.as_markup()

# ОБРАБОТЧИКИ

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    user = UserManager.get_user(user_id)
    if not user:
        user = UserManager.create_user(user_id, username)
        welcome_text = (
            "🎮 Добро пожаловать в бот с кейсами и акциями!\n\n"
            f"💎 Ваш баланс: {user['balance']} atm\n"
            "📦 Открывайте кейсы и собирайте коллекцию предметов!\n"
            "📈 Торгуйте акциями на виртуальной бирже!\n"
            "🏦 Используйте вклады для пассивного дохода!\n"
            "🎁 Активируйте промокоды для бонусов!\n"
            "🎒 Предметы можно выводить из инвентаря"
        )
    else:
        deposit_info = DepositManager.get_user_deposit_info(user_id)
        monthly_profit = deposit_info.get("monthly_profit", 0)
        portfolio = StockManager.get_portfolio(user_id)
        
        welcome_text = (
            "🎮 С возвращением в бот с кейсами и акциями!\n\n"
            f"💰 Баланс: {user['balance']:.2f} atm\n"
            f"📈 Стоимость портфеля: {portfolio['total_value']:.2f} atm\n"
            f"🏦 На вкладе: {user.get('deposit_balance', 0):.2f} atm\n"
            f"💎 Месячная прибыль: {monthly_profit:.2f} atm\n"
            f"📦 Открыто кейсов: {user.get('cases_opened', 0)}\n"
            f"🎒 Предметов: {len(user.get('inventory', []))}\n"
            f"📤 Выведено предметов: {user.get('withdrawals_count', 0)}\n"
            f"🎁 Использовано промокодов: {len(user.get('used_promocodes', []))}\n\n"
            f"Пока идёт бета тест бота. Глав. админ бота @propepka\n"
            f"Лучше обращаться в сообщения каналу @atomopencase, так больше шансов что замечу\n\n"
            f"Мой профиль в атоме с доказательством владения NFT https://www.atomglide.com/account/68d4457020d6eacdcdba2f34"
        )
    
    if AdminManager.is_admin(user_id):
        await message.answer(welcome_text, reply_markup=get_admin_keyboard())
    else:
        await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(F.text == "🏦 Вклады")
async def handle_deposits(message: types.Message):
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
        f"💰 Ваш баланс: {user['balance']:.2f} atm\n"
        f"🏦 На вкладе: {deposit_info['deposit_balance']:.2f} atm\n"
        f"💎 Месячная прибыль: {deposit_info['monthly_profit']:.2f} atm\n"
        f"📊 Процентная ставка: {deposit_info['percent']}% в месяц\n"
        f"💰 Минимальная сумма: {deposit_info['min_amount']} atm\n"
        f"💎 Всего прибыли: {deposit_info['deposit_profit']:.2f} atm\n\n"
        "Выберите действие:"
    )
    
    await message.answer(text, reply_markup=get_deposits_keyboard())

@dp.callback_query(F.data == "deposit_info")
async def handle_deposit_info(callback: CallbackQuery):
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
        f"🏦 Всего внесено: {deposit_info['total_deposited']:.2f} atm\n"
        f"💸 Всего выведено: {deposit_info['total_withdrawn']:.2f} atm\n"
        f"💎 Прибыль с вкладов: {deposit_info['deposit_profit']:.2f} atm\n"
        f"💰 Минимальная сумма: {deposit_info['min_amount']} atm\n\n"
        f"💡 Проценты начисляются раз в месяц автоматически."
    )
    
    await callback.message.edit_text(text, reply_markup=get_deposits_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "deposit_make")
async def handle_deposit_make(callback: CallbackQuery, state: FSMContext):
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
    
    min_amount = deposit_info.get("min_amount", 50)
    
    text = (
        "💰 Внесение средств на вклад\n\n"
        f"💰 Ваш баланс: {user['balance']:.2f} atm\n"
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
    try:
        amount = float(message.text)
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
        f"🏦 Доступно для вывода: {deposit_balance:.2f} atm\n"
        f"💰 Ваш баланс: {user['balance']:.2f} atm\n\n"
        "Введите сумму для вывода с вклада:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_to_admin_keyboard())
    await state.set_state(DepositStates.waiting_withdraw_deposit)
    await callback.answer()

@dp.message(DepositStates.waiting_withdraw_deposit)
async def handle_withdraw_deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
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
        
        text += f"{type_text}: {amount:.2f} atm\n"
        text += f"📅 {date}\n"
        text += f"🏦 Баланс после: {record.get('balance_after', 0):.2f} atm\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_deposits_keyboard())
    await callback.answer()

@dp.message(F.text == "📈 Акции")
async def handle_stocks(message: types.Message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    StockManager.update_prices()
    
    stocks = Database.load_stocks()
    
    if not stocks:
        StockManager.init_default_stocks()
        stocks = Database.load_stocks()
    
    text = "📈 Фондовый рынок\n\n"
    text += f"💰 Ваш баланс: {user['balance']:.2f} atm\n\n"
    text += "Доступные акции:\n\n"
    
    for stock_id, data in stocks.items():
        change_emoji = "🟢" if data.get("change", 0) >= 0 else "🔴"
        change_text = f"+{data.get('change', 0)}%" if data.get("change", 0) >= 0 else f"{data.get('change', 0)}%"
        text += f"{change_emoji} {stock_id} - {data['name']}\n"
        text += f"   Цена: {data['price']} atm ({change_text})\n"
        text += f"   В наличии: {data.get('shares', 0)} акций\n\n"
    
    portfolio = StockManager.get_portfolio(user_id)
    if portfolio["stocks"]:
        text += f"\n📊 Ваш портфель: {portfolio['total_value']:.2f} atm"
    
    await message.answer(text, reply_markup=get_stocks_keyboard())

@dp.message(F.text == "🎰 Кейсы")
async def handle_cases_button(message: types.Message):
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
        can_open = CaseManager.can_open_case(case_id)
        if case_data.get("is_limited", False):
            if can_open["can_open"]:
                cases_text += f"🔴 {case_data['name']} - {case_data['price']} atm (Осталось: {case_data.get('opens_left', 0)})\n"
            else:
                cases_text += f"⛔ {case_data['name']} - ЗАКОНЧИЛСЯ\n"
        else:
            cases_text += f"🟢 {case_data['name']} - {case_data['price']} atm\n"
        
        cases_text += f"📝 {case_data['description']}\n\n"
    
    cases_text += f"💎 Ваш баланс: {user['balance']:.2f} atm"
    
    await message.answer(cases_text, reply_markup=get_cases_keyboard())

@dp.message(F.text == "🎒 Инвентарь")
async def handle_inventory_button(message: types.Message):
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
    
    page = 0
    
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

@dp.message(F.text == "🏆 Топ игроков")
async def handle_top_players(message: types.Message):
    users = Database.load_users()
    user_stocks = Database.load_user_stocks()
    stocks = Database.load_stocks()
    
    if not users:
        await message.answer("🏆 Пока нет игроков. Будьте первым!")
        return
    
    sorted_users = []
    for user_data in users.values():
        total_capital = user_data.get("balance", 0) + user_data.get("deposit_balance", 0)
        user_id_str = str(user_data["user_id"])
        
        if user_id_str in user_stocks:
            stock_value = 0
            for stock_id, quantity in user_stocks[user_id_str].items():
                if stock_id in stocks:
                    stock_value += stocks[stock_id]["price"] * quantity
            total_capital += stock_value
        
        sorted_users.append({
            "username": user_data.get("username", f"user_{user_data['user_id']}"),
            "balance": user_data.get("balance", 0),
            "deposit_balance": user_data.get("deposit_balance", 0),
            "stock_value": total_capital - (user_data.get("balance", 0) + user_data.get("deposit_balance", 0)),
            "total_capital": total_capital,
            "cases_opened": user_data.get("cases_opened", 0)
        })
    
    sorted_users.sort(key=lambda x: x["total_capital"], reverse=True)
    
    text = "🏆 Топ игроков по капиталу:\n\n"
    
    for i, user in enumerate(sorted_users[:10], 1):
        text += f"{i}. @{user['username']}\n"
        text += f"   💰 Баланс: {user['balance']:.2f} atm\n"
        text += f"   🏦 На вкладе: {user['deposit_balance']:.2f} atm\n"
        text += f"   📈 Акции: {user['stock_value']:.2f} atm\n"
        text += f"   📊 Всего: {user['total_capital']:.2f} atm\n"
        text += f"   📦 Кейсов: {user['cases_opened']}\n\n"
    
    await message.answer(text)

# Обработчики колбэков для акций
@dp.callback_query(F.data.startswith("stock_"))
async def handle_stock_detail(callback: CallbackQuery):
    stock_id = callback.data.replace("stock_", "")
    stocks = Database.load_stocks()
    
    if stock_id not in stocks:
        await callback.answer("❌ Акция не найдена")
        return
    
    stock = stocks[stock_id]
    
    text = (
        f"📊 {stock_id} - {stock['name']}\n\n"
        f"💰 Цена: {stock['price']} atm\n"
        f"📈 Изменение: {stock['change']}%\n"
        f"📊 Сектор: {stock['sector']}\n"
        f"📈 Волатильность: {stock['volatility']}%\n"
        f"📦 Доступно акций: {stock['shares']}\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_stock_detail_keyboard(stock_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def handle_buy_stock(callback: CallbackQuery, state: FSMContext):
    stock_id = callback.data.replace("buy_", "")
    
    await callback.message.edit_text(
        f"💰 Покупка акций {stock_id}\nВведите количество для покупки:",
        reply_markup=get_back_to_admin_keyboard()
    )
    
    await state.set_state(StockStates.waiting_buy_quantity)
    await state.update_data(stock_id=stock_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_"))
async def handle_sell_stock(callback: CallbackQuery, state: FSMContext):
    stock_id = callback.data.replace("sell_", "")
    user_id = callback.from_user.id
    
    user_stocks = Database.load_user_stocks()
    user_id_str = str(user_id)
    
    if user_id_str not in user_stocks or stock_id not in user_stocks[user_id_str]:
        await callback.answer("❌ У вас нет этих акций")
        return
    
    available = user_stocks[user_id_str][stock_id]
    
    await callback.message.edit_text(
        f"💸 Продажа акций {stock_id}\nУ вас есть: {available} акций\nВведите количество для продажи:",
        reply_markup=get_back_to_admin_keyboard()
    )
    
    await state.set_state(StockStates.waiting_sell_quantity)
    await state.update_data(stock_id=stock_id)
    await callback.answer()

@dp.message(StockStates.waiting_buy_quantity)
async def handle_buy_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
        
        data = await state.get_data()
        stock_id = data.get("stock_id")
        
        if not stock_id:
            await message.answer("❌ Ошибка: не найдена акция")
            await state.clear()
            return
        
        result = StockManager.buy_stock(message.from_user.id, stock_id, quantity)
        
        await message.answer(
            result["message"],
            reply_markup=get_main_keyboard()
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")

@dp.message(StockStates.waiting_sell_quantity)
async def handle_sell_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
        
        data = await state.get_data()
        stock_id = data.get("stock_id")
        
        if not stock_id:
            await message.answer("❌ Ошибка: не найдена акция")
            await state.clear()
            return
        
        result = StockManager.sell_stock(message.from_user.id, stock_id, quantity)
        
        await message.answer(
            result["message"],
            reply_markup=get_main_keyboard()
        )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")

@dp.callback_query(F.data == "my_portfolio")
async def handle_my_portfolio(callback: CallbackQuery):
    user_id = callback.from_user.id
    portfolio = StockManager.get_portfolio(user_id)
    
    if not portfolio["stocks"]:
        await callback.message.edit_text(
            "📊 Ваш портфель пуст\nКупите акции, чтобы начать инвестировать!",
            reply_markup=get_stocks_keyboard()
        )
        await callback.answer()
        return
    
    text = "📊 Ваш инвестиционный портфель:\n\n"
    total_invested = 0
    
    for stock_id, data in portfolio["stocks"].items():
        text += f"📈 {stock_id} - {data['name']}\n"
        text += f"   Количество: {data['quantity']} акций\n"
        text += f"   Цена: {data['price']} atm\n"
        text += f"   Стоимость: {data['value']:.2f} atm\n"
        change_emoji = "🟢" if data.get("change", 0) >= 0 else "🔴"
        text += f"   Изменение: {change_emoji} {data.get('change', 0)}%\n\n"
        total_invested += data['value']
    
    text += f"💰 Общая стоимость: {portfolio['total_value']:.2f} atm"
    
    await callback.message.edit_text(text, reply_markup=get_stocks_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "refresh_stocks")
async def handle_refresh_stocks(callback: CallbackQuery):
    StockManager.update_prices()
    await callback.answer("✅ Цены акций обновлены!")

# Обработчики для кейсов
@dp.callback_query(F.data.startswith("case_"))
async def handle_case_detail(callback: CallbackQuery):
    case_id = callback.data.replace("case_", "")
    case = CaseManager.get_case(case_id)
    
    if not case:
        await callback.answer("❌ Кейс не найден")
        return
    
    can_open = CaseManager.can_open_case(case_id)
    
    text = (
        f"📦 {case['name']}\n\n"
        f"📝 {case['description']}\n\n"
        f"💰 Цена: {case['price']} atm\n"
    )
    
    if case.get("is_limited", False):
        text += f"📊 Осталось открытий: {case.get('opens_left', 0)}\n"
        text += f"📈 Всего открыто: {case.get('total_opens', 0)}\n\n"
    
    if not can_open["can_open"]:
        text += f"❌ {can_open['reason']}\n\n"
    
    text += "Содержимое кейса:\n"
    
    for item in case["items"]:
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡",
            "mythical": "🔴"
        }.get(item.get("rarity", "common"), "⚫")
        
        text += f"{rarity_emoji} {item['name']} - {item['chance']}%\n"
    
    await callback.message.edit_text(text, reply_markup=get_case_detail_keyboard(case_id, can_open["can_open"]))
    await callback.answer()

@dp.callback_query(F.data.startswith("open_case_"))
async def handle_open_case(callback: CallbackQuery):
    case_id = callback.data.replace("open_case_", "")
    user_id = callback.from_user.id
    
    user = UserManager.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    case = CaseManager.get_case(case_id)
    if not case:
        await callback.answer("❌ Кейс не найден")
        return
    
    if user["balance"] < case["price"]:
        await callback.answer("❌ Недостаточно средств")
        return
    
    result = CaseManager.open_case(case_id, user_id)
    
    if "error" in result:
        await callback.answer(f"❌ {result['error']}")
        return
    
    # Анимация открытия
    await callback.message.edit_text("🎰 Открываем кейс...")
    await asyncio.sleep(1)
    
    item = result
    rarity_emoji = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "mythical": "🔴"
    }.get(item.get("rarity", "common"), "⚫")
    
    text = (
        f"🎉 Поздравляем! Вы открыли кейс {case['name']}!\n\n"
        f"🎁 Выпал предмет:\n"
        f"{rarity_emoji} {item['name']}\n"
        f"📊 Редкость: {item.get('rarity', 'common')}\n"
        f"🎯 Шанс выпадения: {item.get('chance', 0)}%\n\n"
        f"💰 Ваш баланс: {user['balance'] - case['price']:.2f} atm\n"
        f"📦 Предмет добавлен в инвентарь!"
    )
    
    await callback.message.edit_text(text, reply_markup=get_cases_keyboard())
    await callback.answer()

# Обработчики для инвентаря
@dp.callback_query(F.data.startswith("item_"))
async def handle_item_detail(callback: CallbackQuery):
    try:
        item_index = int(callback.data.replace("item_", ""))
        user_id = callback.from_user.id
        
        item = UserManager.get_item_by_index(user_id, item_index)
        
        if not item:
            await callback.answer("❌ Предмет не найден")
            return
        
        rarity_emoji = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡",
            "mythical": "🔴"
        }.get(item.get("rarity", "common"), "⚫")
        
        received_date = datetime.fromisoformat(item.get("received_at", datetime.now().isoformat())).strftime("%d.%m.%Y %H:%M")
        
        text = (
            f"🎁 {item['name']}\n\n"
            f"📊 Редкость: {rarity_emoji} {item.get('rarity', 'common')}\n"
            f"🎯 Шанс выпадения: {item.get('chance', 0)}%\n"
            f"📅 Получен: {received_date}\n"
        )
        
        if item.get('on_withdrawal', False):
            text += f"\n⏳ Статус: На выводе"
        
        await callback.message.edit_text(text, reply_markup=get_item_management_keyboard(item_index, item))
        await callback.answer()
    except ValueError:
        await callback.answer("❌ Ошибка")

@dp.callback_query(F.data.startswith("withdraw_"))
async def handle_withdraw_item(callback: CallbackQuery, state: FSMContext):
    try:
        item_index = int(callback.data.replace("withdraw_", ""))
        user_id = callback.from_user.id
        
        item = UserManager.get_item_by_index(user_id, item_index)
        
        if not item:
            await callback.answer("❌ Предмет не найден")
            return
        
        if item.get('on_withdrawal', False):
            await callback.answer("❌ Предмет уже на выводе")
            return
        
        await state.set_state(UserWithdrawStates.waiting_contact_info)
        await state.update_data(item_index=item_index, item_id=item.get("item_id"))
        
        await callback.message.edit_text(
            "📤 Вывод предмета\n\n"
            f"🎁 Предмет: {item['name']}\n"
            f"📊 Редкость: {item.get('rarity', 'common')}\n\n"
            "Введите контактную информацию для связи (AtomGlide username или AtomGlide ID):",
            reply_markup=get_back_to_admin_keyboard()
        )
        await callback.answer()
    except ValueError:
        await callback.answer("❌ Ошибка")

@dp.message(UserWithdrawStates.waiting_contact_info)
async def handle_withdraw_contact_info(message: types.Message, state: FSMContext):
    contact_info = message.text.strip()
    data = await state.get_data()
    item_index = data.get("item_index")
    item_id = data.get("item_id")
    user_id = message.from_user.id
    
    if not item_index:
        await message.answer("❌ Ошибка: предмет не найден")
        await state.clear()
        return
    
    item = UserManager.get_item_by_index(user_id, item_index)
    if not item:
        await message.answer("❌ Предмет не найден")
        await state.clear()
        return
    
    withdrawal_id = WithdrawalManager.create_withdrawal(user_id, item, contact_info)
    
    if withdrawal_id:
        await message.answer(
            f"✅ Заявка на вывод создана!\n\n"
            f"🎁 Предмет: {item['name']}\n"
            f"📞 Контакт: {contact_info}\n"
            f"📋 ID заявки: {withdrawal_id}\n\n"
            "⏳ Ожидайте рассмотрения заявки администратором.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❌ Не удалось создать заявку на вывод",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("delete_"))
async def handle_delete_item(callback: CallbackQuery):
    try:
        item_index = int(callback.data.replace("delete_", ""))
        user_id = callback.from_user.id
        
        item = UserManager.get_item_by_index(user_id, item_index)
        
        if not item:
            await callback.answer("❌ Предмет не найден")
            return
        
        if item.get('on_withdrawal', False):
            await callback.answer("❌ Нельзя удалить предмет на выводе")
            return
        
        removed = UserManager.remove_from_inventory(user_id, item.get("item_id"))
        
        if removed:
            await callback.message.edit_text(
                f"✅ Предмет удален из инвентаря:\n{removed.get('name', 'Неизвестный предмет')}",
                reply_markup=get_inventory_keyboard(UserManager.get_user(user_id).get("inventory", []), 0)
            )
        else:
            await callback.answer("❌ Ошибка при удалении предмета")
    except ValueError:
        await callback.answer("❌ Ошибка")

@dp.callback_query(F.data.startswith("inventory_page_"))
async def handle_inventory_page(callback: CallbackQuery):
    try:
        page = int(callback.data.replace("inventory_page_", ""))
        user_id = callback.from_user.id
        
        user = UserManager.get_user(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        inventory = user.get("inventory", [])
        valid_items = [item for item in inventory if isinstance(item, dict)]
        
        items_per_page = 10
        total_pages = (len(valid_items) + items_per_page - 1) // items_per_page
        
        if page < 0 or page >= total_pages:
            await callback.answer("❌ Неверная страница")
            return
        
        rarity_count = {}
        items_on_withdrawal = 0
        
        for item in valid_items:
            rarity = item.get("rarity", "unknown")
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            if item.get('on_withdrawal', False):
                items_on_withdrawal += 1
        
        inventory_text = f"🎒 Ваш инвентарь ({len(valid_items)} предметов)"
        
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
    except ValueError:
        await callback.answer("❌ Ошибка")

# Обработчики для админ-панели
@dp.message(F.text == "👑 Админ панель")
async def handle_admin_panel(message: types.Message):
    user_id = message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    await message.answer(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )

@dp.callback_query(F.data == "admin_back_panel")
async def handle_admin_back_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await callback.answer("❌ У вас нет прав администратора")
        return
    
    await callback.message.edit_text(
        "👑 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_withdrawals")
async def handle_admin_withdrawals(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await callback.answer("❌ У вас нет прав администратора")
        return
    
    pending_withdrawals = WithdrawalManager.get_pending_withdrawals()
    
    if not pending_withdrawals:
        await callback.message.edit_text(
            "📋 Нет ожидающих заявок на вывод",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        return
    
    text = f"📋 Ожидающие заявки на вывод ({len(pending_withdrawals)}):\n\n"
    
    for i, wd in enumerate(pending_withdrawals, 1):
        user = UserManager.get_user(wd["user_id"])
        username = user.get("username", f"user_{wd['user_id']}") if user else f"user_{wd['user_id']}"
        item_name = wd["item"].get("name", "Неизвестный предмет")
        rarity = wd["item"].get("rarity", "common")
        created = datetime.fromisoformat(wd["created_at"]).strftime("%d.%m.%Y %H:%M")
        
        text += f"{i}. 🆔 {wd['id']}\n"
        text += f"   👤 Пользователь: @{username}\n"
        text += f"   🎁 Предмет: {item_name} ({rarity})\n"
        text += f"   📞 Контакт: {wd['contact_info']}\n"
        text += f"   📅 Дата: {created}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_panel_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_wd_"))
async def handle_approve_withdrawal(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await callback.answer("❌ У вас нет прав администратора")
        return
    
    safe_id = callback.data.replace("approve_wd_", "")
    withdrawal_id = restore_withdrawal_id(safe_id)
    
    WithdrawalManager.update_withdrawal(withdrawal_id, {
        "status": "approved",
        "admin_id": user_id,
        "notes": "Заявка одобрена"
    })
    
    withdrawal = WithdrawalManager.get_withdrawal(withdrawal_id)
    if withdrawal:
        wd_user_id = withdrawal["user_id"]
        item_name = withdrawal["item"].get("name", "Неизвестный предмет")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                wd_user_id,
                f"✅ Ваша заявка на вывод одобрена!\n\n"
                f"🎁 Предмет: {item_name}\n"
                f"🆔 ID заявки: {withdrawal_id}\n\n"
                f"📞 Свяжитесь с администратором для получения предмета."
            )
        except:
            pass
    
    await callback.answer("✅ Заявка одобрена")
    await handle_admin_withdrawals(callback)

@dp.callback_query(F.data.startswith("reject_wd_"))
async def handle_reject_withdrawal(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await callback.answer("❌ У вас нет прав администратора")
        return
    
    safe_id = callback.data.replace("reject_wd_", "")
    withdrawal_id = restore_withdrawal_id(safe_id)
    
    WithdrawalManager.update_withdrawal(withdrawal_id, {
        "status": "rejected",
        "admin_id": user_id,
        "notes": "Заявка отклонена"
    })
    
    withdrawal = WithdrawalManager.get_withdrawal(withdrawal_id)
    if withdrawal:
        wd_user_id = withdrawal["user_id"]
        item_name = withdrawal["item"].get("name", "Неизвестный предмет")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                wd_user_id,
                f"❌ Ваша заявка на вывод отклонена.\n\n"
                f"🎁 Предмет: {item_name}\n"
                f"🆔 ID заявки: {withdrawal_id}\n\n"
                f"ℹ️ Предмет возвращен в инвентарь."
            )
        except:
            pass
    
    await callback.answer("❌ Заявка отклонена")
    await handle_admin_withdrawals(callback)

# Обработчики для баланса
@dp.message(F.text == "💰 Баланс")
async def handle_balance(message: types.Message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    deposit_info = DepositManager.get_user_deposit_info(user_id)
    portfolio = StockManager.get_portfolio(user_id)
    
    text = (
        f"💰 Ваш баланс: {user['balance']:.2f} atm\n"
        f"🏦 На вкладе: {deposit_info['deposit_balance']:.2f} atm\n"
        f"📈 Стоимость портфеля: {portfolio['total_value']:.2f} atm\n"
        f"💎 Месячная прибыль: {deposit_info['monthly_profit']:.2f} atm\n\n"
        f"📊 Общий капитал: {user['balance'] + deposit_info['deposit_balance'] + portfolio['total_value']:.2f} atm\n\n"
        f"📦 Открыто кейсов: {user.get('cases_opened', 0)}\n"
        f"🎒 Предметов: {len(user.get('inventory', []))}\n"
        f"📤 Выведено предметов: {user.get('withdrawals_count', 0)}\n"
        f"🎁 Использовано промокодов: {len(user.get('used_promocodes', []))}"
    )
    
    await message.answer(text)

# Обработчики для промокодов
@dp.message(F.text == "🎁 Активировать промокод")
async def handle_activate_promo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    await message.answer(
        "🎁 Активация промокода\n\n"
        "Введите промокод для активации:",
        reply_markup=get_back_to_admin_keyboard()
    )
    
    await state.set_state(PromoStates.waiting_promo_code)

@dp.message(PromoStates.waiting_promo_code)
async def handle_promo_code_input(message: types.Message, state: FSMContext):
    promocode = message.text.strip()
    user_id = message.from_user.id
    
    result = PromoCodeManager.activate_promocode(user_id, promocode)
    
    if result["success"]:
        await message.answer(
            result["message"],
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            result["message"] + "\n\nПопробуйте другой промокод:",
            reply_markup=get_back_to_admin_keyboard()
        )
        return
    
    await state.clear()

# Обработчики для статистики
@dp.message(F.text == "📊 Статистика")
async def handle_stats(message: types.Message):
    user_id = message.from_user.id
    
    if not AdminManager.is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    users = Database.load_users()
    withdrawals = Database.load_withdrawals()
    cases = Database.load_cases()
    promocodes = PromoCodeManager.get_all_promocodes()
    
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_deposits = sum(user.get("deposit_balance", 0) for user in users.values())
    total_cases_opened = sum(user.get("cases_opened", 0) for user in users.values())
    
    pending_withdrawals = len([w for w in withdrawals.values() if w.get("status") == "pending"])
    approved_withdrawals = len([w for w in withdrawals.values() if w.get("status") == "approved"])
    
    active_promocodes = len([p for p in promocodes.values() if p.get("is_active", True)])
    used_promocodes = sum(p.get("used_count", 0) for p in promocodes.values())
    
    text = (
        "📊 Статистика бота:\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"💰 Общий баланс: {total_balance:.2f} atm\n"
        f"🏦 Общая сумма вкладов: {total_deposits:.2f} atm\n"
        f"📦 Открыто кейсов: {total_cases_opened}\n\n"
        f"📤 Заявки на вывод:\n"
        f"   ⏳ Ожидает: {pending_withdrawals}\n"
        f"   ✅ Одобрено: {approved_withdrawals}\n"
        f"   📊 Всего: {len(withdrawals)}\n\n"
        f"🎁 Промокоды:\n"
        f"   📊 Всего: {len(promocodes)}\n"
        f"   🟢 Активных: {active_promocodes}\n"
        f"   💎 Использовано: {used_promocodes} раз\n\n"
        f"🎰 Кейсы:\n"
    )
    
    for case_id, case_data in cases.items():
        text += f"   📦 {case_data['name']}: {case_data.get('total_opens', 0)} открытий\n"
    
    await message.answer(text)

@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if AdminManager.is_admin(user_id):
        await callback.message.edit_text(
            "Главное меню",
            reply_markup=get_admin_keyboard()
        )
    else:
        await callback.message.edit_text(
            "Главное меню",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@dp.callback_query(F.data == "back_to_stocks")
async def handle_back_to_stocks(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    stocks = Database.load_stocks()
    
    text = "📈 Фондовый рынок\n\n"
    text += f"💰 Ваш баланс: {user['balance']:.2f} atm\n\n"
    text += "Доступные акции:\n\n"
    
    for stock_id, data in stocks.items():
        change_emoji = "🟢" if data.get("change", 0) >= 0 else "🔴"
        change_text = f"+{data.get('change', 0)}%" if data.get("change", 0) >= 0 else f"{data.get('change', 0)}%"
        text += f"{change_emoji} {stock_id} - {data['name']}\n"
        text += f"   Цена: {data['price']} atm ({change_text})\n"
        text += f"   В наличии: {data.get('shares', 0)} акций\n\n"
    
    portfolio = StockManager.get_portfolio(user_id)
    if portfolio["stocks"]:
        text += f"\n📊 Ваш портфель: {portfolio['total_value']:.2f} atm"
    
    await callback.message.edit_text(text, reply_markup=get_stocks_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "back_to_cases")
async def handle_back_to_cases(callback: CallbackQuery):
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
        can_open = CaseManager.can_open_case(case_id)
        if case_data.get("is_limited", False):
            if can_open["can_open"]:
                cases_text += f"🔴 {case_data['name']} - {case_data['price']} atm (Осталось: {case_data.get('opens_left', 0)})\n"
            else:
                cases_text += f"⛔ {case_data['name']} - ЗАКОНЧИЛСЯ\n"
        else:
            cases_text += f"🟢 {case_data['name']} - {case_data['price']} atm\n"
        
        cases_text += f"📝 {case_data['description']}\n\n"
    
    cases_text += f"💎 Ваш баланс: {user['balance']:.2f} atm"
    
    await callback.message.edit_text(cases_text, reply_markup=get_cases_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "open_inventory")
async def handle_open_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Сначала используйте /start")
        return
    
    inventory = user.get("inventory", [])
    
    if not inventory:
        await callback.message.edit_text(
            "🎒 Ваш инвентарь пуст\n"
            "📦 Откройте кейсы, чтобы получить предметы!",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    
    page = 0
    
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

async def main():
    # Создаем необходимые файлы если их нет
    if not os.path.exists(CASES_DB_FILE):
        init_default_cases()
        logger.info("Создана база данных кейсов")
    
    required_files = [
        (USERS_DB_FILE, {}),
        (WITHDRAWALS_DB_FILE, {}),
        (ADMINS_FILE, [ADMIN_ID]),
        (PROMOCODES_FILE, {}),
        (DEPOSITS_FILE, {}),
        (SETTINGS_FILE, Database.load_settings()),  # Это создаст файл с настройками по умолчанию
        (STOCKS_FILE, {}),
        (USER_STOCKS_FILE, {})
    ]
    
    for file_path, default_data in required_files:
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Создан файл: {file_path}")
            except IOError as e:
                logger.error(f"Ошибка создания файла {file_path}: {e}")
    
    # Проверяем наличие акций и создаем по умолчанию если их нет
    stocks = Database.load_stocks()
    if not stocks:
        StockManager.init_default_stocks()
        logger.info("Созданы акции по умолчанию")
    
    cleanup_inventory()
    
    logger.info("Бот запускается...")
    logger.info(f"Основной админ: {ADMIN_ID}")
    
    # Удаляем вебхук если был установлен ранее
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Проверка токена
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or ADMIN_ID == 123456789:
        print("⚠️  ВНИМАНИЕ: Необходимо настроить бота!")
        print("\n1. Получите токен бота у @BotFather")
        print("2. Узнайте свой Telegram ID через @userinfobot")
        print("3. Замените значения в начале файла:")
        print(f"   BOT_TOKEN = \"ВАШ_ТОКЕН\"")
        print(f"   ADMIN_ID = ВАШ_ID")
    else:
        asyncio.run(main())
