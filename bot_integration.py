#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для інтеграції Instagram скрапера з ботом
Цей скрипт можна запускати за розкладом для автоматичного оновлення контенту
"""

import os
import sys
import time
import logging
import sqlite3
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Імпортуємо функції з наших модулів
from selen import get_page_with_pagination
from parser import main_parser, init_db

# Завантажуємо змінні середовища
load_dotenv()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_integration.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("InstagramBot")

# Отримуємо налаштування з .env
WEBSITE_API_URL = os.getenv("WEBSITE_API_URL")
API_KEY = os.getenv("API_KEY")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "3600"))  # За замовчуванням 1 година
DB_PATH = os.getenv("DB_PATH", "instagram_data.db")

def get_last_update_time():
    """Отримує час останнього оновлення з файлу"""
    try:
        if os.path.exists("last_update.txt"):
            with open("last_update.txt", "r") as f:
                timestamp = f.read().strip()
                return datetime.fromisoformat(timestamp)
        return datetime.now() - timedelta(days=7)  # За замовчуванням - тиждень тому
    except Exception as e:
        logger.error(f"Помилка при отриманні часу останнього оновлення: {e}")
        return datetime.now() - timedelta(days=7)

def save_last_update_time():
    """Зберігає поточний час як час останнього оновлення"""
    try:
        with open("last_update.txt", "w") as f:
            f.write(datetime.now().isoformat())
        logger.info("Час останнього оновлення збережено")
    except Exception as e:
        logger.error(f"Помилка при збереженні часу останнього оновлення: {e}")

def get_new_content():
    """Отримує новий контент з Instagram"""
    try:
        # Запускаємо скрапінг
        logger.info("Запуск скрапінгу Instagram...")
        get_page_with_pagination()
        
        # Запускаємо парсинг
        logger.info("Запуск парсингу HTML...")
        main_parser()
        
        logger.info("Отримання контенту завершено успішно")
        return True
    except Exception as e:
        logger.error(f"Помилка при отриманні контенту: {e}")
        return False

def get_new_posts_from_db(last_update):
    """Отримує нові пости з бази даних, які з'явились після останнього оновлення"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Перетворюємо datetime у string формат для SQL запиту
        last_update_str = last_update.strftime("%Y-%m-%d %H:%M:%S")
        
        # Отримуємо нові пости
        cursor.execute("""
            SELECT id, post_type, media_url, description, timestamp, username, is_video, parsed_date
            FROM posts
            WHERE parsed_date > ?
            ORDER BY parsed_date DESC
        """, (last_update_str,))
        
        # Отримуємо назви стовпців
        column_names = [description[0] for description in cursor.description]
        
        # Формуємо список словників
        posts = []
        for row in cursor.fetchall():
            post = {}
            for i, column in enumerate(column_names):
                post[column] = row[i]
            posts.append(post)
        
        conn.close()
        logger.info(f"Отримано {len(posts)} нових постів з бази даних")
        return posts
    except Exception as e:
        logger.error(f"Помилка при отриманні постів з бази даних: {e}")
        return []

def upload_to_website(posts):
    """Завантажує нові пости на веб-сайт через API"""
    if not posts:
        logger.info("Немає нових постів для завантаження на сайт")
        return True
    
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Підготовка даних для відправки
        payload = {
            "posts": posts,
            "timestamp": datetime.now().isoformat()
        }
        
        # Відправка запиту до API
        response = requests.post(
            WEBSITE_API_URL,
            headers=headers,
            data=json.dumps(payload)
        )
        
        # Перевірка відповіді
        if response.status_code == 200:
            logger.info(f"Успішно завантажено {len(posts)} постів на сайт")
            return True
        else:
            logger.error(f"Помилка при завантаженні на сайт. Код: {response.status_code}, Відповідь: {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Помилка при завантаженні на сайт: {e}")
        return False

def main():
    """Головна функція для інтеграції з ботом"""
    logger.info("Запуск процесу оновлення контенту...")
    
    # Отримуємо час останнього оновлення
    last_update = get_last_update_time()
    logger.info(f"Останнє оновлення: {last_update.isoformat()}")
    
    # Отримуємо новий контент
    if get_new_content():
        # Отримуємо нові пости з бази даних
        new_posts = get_new_posts_from_db(last_update)
        
        # Завантажуємо нові пости на сайт
        if upload_to_website(new_posts):
            # Зберігаємо час останнього оновлення
            save_last_update_time()
            logger.info("Процес оновлення контенту завершено успішно")
        else:
            logger.error("Не вдалося завантажити контент на сайт")
    else:
        logger.error("Не вдалося отримати новий контент")

if __name__ == "__main__":
    main()
