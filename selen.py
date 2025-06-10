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



HEADLESS = False
URL_DOPYS = os.getenv("URL_DOPYS")
URL_REELS = os.getenv("URL_REELS")

# Ініціалізація файлу для зберігання ID надісланих оголошень
SENT_IDS_FILE = "sent_ids.txt"

def get_page_with_pagination():
    """Отримуємо сторінку Instagram"""
    driver = None
    try:
        # Ініціалізуємо драйвер
        driver = init_selenium()
        
        # Спочатку авторизуємось
        auth_success = login_to_instagram(driver)
        
        if not auth_success:
            logger.error("Не вдалося авторизуватися в Instagram. Припиняємо виконання.")
            return None
            
        # Зберігаємо сторінку з дописами
        logger.info("Зберігаємо сторінку з дописами...")
        save_page(driver, URL_DOPYS, is_posts=True, is_reels=False)
        
        # Додатковий час між завантаженнями
        time.sleep(5)
        
        # Зберігаємо сторінку з reels
        logger.info("Зберігаємо сторінку з reels...")
        save_page(driver, URL_REELS, is_posts=False, is_reels=True)
        
        logger.info("Усі сторінки успішно збережено")
        
    except Exception as e:
        logger.error(f"Помилка під час отримання сторінки: {e}")
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    get_page_with_pagination()