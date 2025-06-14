#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging

from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from func.f_auch import init_selenium, login_to_instagram,save_page
# from func.f_time import random_sleep

# Завантаження змінних середовища з .env файлу
load_dotenv()

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("parser.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("InstagramBot")



# Ці змінні будуть оновлені перед кожним скрапінгом
HEADLESS = False

# Ініціалізація файлу для зберігання ID надісланих оголошень
SENT_IDS_FILE = "sent_ids.txt"

def get_page_with_pagination(account_username="default"):
    """Отримуємо сторінку Instagram для конкретного акаунту
    
    Args:
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
    """
    from accounts_config import get_account_config
    from url_manager import get_urls
    
    driver = None
    try:
        # Отримуємо конфігурацію акаунту (для імені в базі та місця зберігання зображень)
        account_config = get_account_config(account_username)
        
        # Отримуємо URL з JSON файлу
        url_dopys, url_reels = get_urls()
        
        # Детальне логування URL для діагностики
        logger.info(f"[ДЕБАГ] Отримано URL з JSON: url_posts='{url_dopys}', url_reels='{url_reels}'")
        
        # Перевіряємо URL на коректність
        if not url_dopys or not url_reels:
            logger.error(f"URL не налаштовано в JSON файлі. Перевірте налаштування.")
            return None
        
        # Логуємо інформацію про URL, які будемо використовувати
        logger.info(f"Використовуємо URL з налаштувань: Posts={url_dopys}, Reels={url_reels}")
        logger.info(f"Скрапінг виконується для акаунту: {account_username} (зберігання в базу {account_config['database']})")
        
        # Ініціалізуємо драйвер
        driver = init_selenium()
        
        # Спочатку авторизуємось
        auth_success = login_to_instagram(driver)
        
        if not auth_success:
            logger.error("Не вдалося авторизуватися в Instagram. Припиняємо виконання.")
            return None
            
        # Зберігаємо сторінку з дописами
        logger.info(f"Зберігаємо сторінку з дописами для акаунту {account_username}...")
        save_page(driver, url_dopys, is_posts=True, is_reels=False)
        
        # Додатковий час між завантаженнями
        time.sleep(5)
        
        # Зберігаємо сторінку з reels
        logger.info(f"Зберігаємо сторінку з reels для акаунту {account_username}...")
        save_page(driver, url_reels, is_posts=False, is_reels=True)
        
        logger.info("Усі сторінки успішно збережено")
        
    except Exception as e:
        logger.error(f"Помилка під час отримання сторінки: {e}")
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    get_page_with_pagination()