#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging
from pathlib import Path
from accounts_config import get_all_accounts, get_account_config

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def migrate_database(db_path, account_username):
    """Додає стовпець account до таблиці posts, якщо він відсутній"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Перевіряємо, чи існує таблиця posts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if not cursor.fetchone():
            logger.warning(f"Таблиця posts не існує в базі {db_path}")
            
            # Створюємо таблицю posts, якщо вона не існує
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
            logger.info(f"Створено таблицю posts в базі {db_path}")
            conn.close()
            return True
        
        # Перевіряємо, чи існує стовпець account
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'account' not in columns:
            logger.info(f"Додаємо стовпець 'account' до таблиці posts в базі {db_path}")
            
            try:
                # Спробуємо додати стовпець account
                cursor.execute("ALTER TABLE posts ADD COLUMN account TEXT")
                
                # Заповнюємо стовпець account значенням за замовчуванням
                cursor.execute("UPDATE posts SET account = ?", (account_username,))
                
                conn.commit()
                logger.info(f"Міграцію для бази {db_path} успішно завершено")
            except sqlite3.OperationalError as e:
                logger.error(f"Помилка при додаванні стовпця: {str(e)}")
                
                # Створюємо нову таблицю з потрібною структурою
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts_new (
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
                
                # Копіюємо дані зі старої таблиці в нову
                cursor.execute('''
                INSERT INTO posts_new (id, post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path, account)
                SELECT id, post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path, ? FROM posts
                ''', (account_username,))
                
                # Видаляємо стару таблицю і перейменовуємо нову
                cursor.execute("DROP TABLE posts")
                cursor.execute("ALTER TABLE posts_new RENAME TO posts")
                
                conn.commit()
                logger.info(f"Міграцію для бази {db_path} успішно завершено через створення нової таблиці")
        else:
            logger.info(f"Стовпець 'account' вже існує в таблиці posts бази {db_path}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Помилка при міграції бази {db_path}: {str(e)}")
        return False

def main():
    """Головна функція міграції"""
    logger.info("Початок міграції баз даних...")
    
    # Отримуємо список всіх акаунтів
    accounts = get_all_accounts()
    
    for account in accounts:
        username = account["username"]
        db_path = account["database"]
        
        # Перевіряємо, чи це повний шлях
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        
        logger.info(f"Міграція бази даних для акаунту {username}: {db_path}")
        
        # Перевіряємо, чи існує файл бази даних
        if not os.path.exists(db_path):
            logger.warning(f"База даних {db_path} не існує")
            continue
        
        # Виконуємо міграцію
        success = migrate_database(db_path, username)
        if success:
            logger.info(f"Міграцію для акаунту {username} успішно завершено")
        else:
            logger.error(f"Помилка при міграції для акаунту {username}")
    
    logger.info("Міграцію всіх баз даних завершено")

if __name__ == "__main__":
    main()
