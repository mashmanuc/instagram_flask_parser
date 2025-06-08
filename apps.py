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
from func.f_auch import init_selenium, login_to_instagram
from func.f_time import random_sleep
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

driver = init_selenium()
auth_success = login_to_instagram(driver)




if __name__ == "__main__":
    get_page_with_pagination(URL_DOPYS)  