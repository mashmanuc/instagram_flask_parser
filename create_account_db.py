#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging
from pathlib import Path
from accounts_config import get_all_accounts

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_creation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_database(db_path, account_username):
    """Створює базу даних для акаунту, якщо вона не існує"""
    try:
        # Переконуємося, що директорія існує
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Створюємо таблицю для постів
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_type TEXT,
            media_url TEXT,
            description TEXT,
            timestamp TEXT,
            username TEXT,
            is_video INTEGER,
            parsed_date TEXT,
            local_path TEXT,
            account TEXT
        )
        ''')
        
        conn.commit()
        logger.info(f"Базу даних {db_path} для акаунту {account_username} успішно створено")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Помилка при створенні бази даних {db_path}: {str(e)}")
        return False

def main():
    """Головна функція створення баз даних"""
    logger.info("Початок створення баз даних...")
    
    # Отримуємо список всіх акаунтів
    accounts = get_all_accounts()
    
    for account in accounts:
        username = account["username"]
        db_path = account["database"]
        
        # Перевіряємо, чи це повний шлях
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        
        logger.info(f"Перевірка бази даних для акаунту {username}: {db_path}")
        
        # Перевіряємо, чи існує файл бази даних
        if not os.path.exists(db_path):
            logger.info(f"База даних {db_path} не існує, створюємо...")
            create_database(db_path, username)
        else:
            logger.info(f"База даних {db_path} вже існує")
    
    logger.info("Перевірку всіх баз даних завершено")

if __name__ == "__main__":
    main()
