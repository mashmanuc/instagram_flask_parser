import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
# Абсолютний імпорт з пакету func
from func.f_time import random_sleep
import logging
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

# Ініціалізуємо логер
logger = logging.getLogger(__name__)

def init_selenium():
    """
    Ініціалізує драйвер Selenium
    """
    options = Options()
    
    # Отримуємо налаштування з .env файлу
    HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'true'
    
    if HEADLESS:
        logger.info("Запуск в фоновому режимі (headless)")
        options.add_argument("--headless")
    else:
        logger.info("Запуск в графічному режимі (з відображенням браузера)")
    
    # Додаємо необхідні опції
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    logger.info("Ініціалізація драйвера Chrome...")
    driver = webdriver.Chrome(options=options)
    logger.info("Драйвер Chrome успішно ініціалізовано")
    return driver


def login_to_instagram(driver):
    """Авторизація в Instagram"""
    try:
        # Отримуємо облікові дані з .env файлу
        username = os.getenv('INSTAGRAM_USERNAME')
        password = os.getenv('INSTAGRAM_PASSWORD')
        
        if not username or not password:
            logger.error("Не знайдено облікові дані Instagram в .env файлі")
            return False
            
        logger.info(f"Спроба входу в Instagram з логіном: {username[:3]}{'*' * (len(username) - 5)}{username[-2:]}")
        logger.info("Пароль знайдено в налаштуваннях")
        
        # Переходимо на сторінку входу Instagram
        logger.info("Переходимо на сторінку входу Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)  # Даємо сторінці час завантажитись
        
        # Очікуємо завантаження сторінки
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
        except Exception as e:
            logger.error(f"Не вдалося завантажити сторінку входу: {str(e)}")
            return False
            
        # Обробляємо cookie
        try:
            cookie_buttons = driver.find_elements(By.XPATH, 
                "//button[contains(., 'Accept All') or contains(., 'Прийняти все') or contains(., 'Allow')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                logger.info("Прийнято cookie")
                time.sleep(2)
        except Exception as e:
            logger.info(f"Не вдалося знайти або натиснути кнопку прийняття cookie: {str(e)}")
        
        # Вводимо логін та пароль
        try:
            # Знаходимо поля форми
            logger.info("Пошук полів форми входу...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username")))
            password_field = driver.find_element(By.NAME, "password")
            
            # Очищаємо поля та вводимо дані
            username_field.clear()
            username_field.send_keys(username)
            logger.info("Введено логін")
            
            password_field.clear()
            password_field.send_keys(password)
            logger.info("Введено пароль")
            
            
            # Знаходимо та натискаємо кнопку входу
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            login_button.click()
            logger.info("Натиснуто кнопку входу")
            
            # Чекаємо завершення авторизації
            logger.info("Очікування завершення авторизації...")
            time.sleep(10)  # Даємо більше часу для авторизації
            
            # Перевіряємо чи успішно авторизувались
            current_url = driver.current_url.lower()
            logger.info(f"Поточний URL після спроби входу: {current_url}")
            
            if "accounts/login" in current_url:
                # Перевіряємо наявність повідомлень про помилку
                error_selectors = [
                    "//div[contains(@class, 'error')]",
                    "//div[contains(text(), 'Sorry')]",
                    "//div[contains(text(), 'Вибачте')]",
                    "//div[contains(text(), 'неправильні')]",
                    "//div[contains(text(), 'incorrect')]"
                ]
                
                for selector in error_selectors:
                    try:
                        error_msg = driver.find_element(By.XPATH, selector)
                        if error_msg and error_msg.is_displayed():
                            logger.error(f"Помилка авторизації: {error_msg.text}")
                            save_screenshot(driver, "error_login_failed.png")
                            return False
                    except:
                        continue
                
                logger.error("Невідома помилка авторизації. Див. скріншоти для деталей.")
                return False
            
            # Якщо дійшли сюди - авторизація ймовірно успішна
            logger.info("Успішна авторизація в Instagram")
            return driver
            
        except Exception as auth_error:
            logger.error(f"Помилка при введенні даних або натисканні кнопки: {str(auth_error)}")
            return False
            
    except Exception as e:
        logger.error(f"Загальна помилка при авторизації: {str(e)}")
        return False
def save_page(driver, url, is_posts=False, is_reels=False):
    """
    Зберігає HTML сторінки Instagram після скролу
    :param driver: Selenium WebDriver
    :param url: URL сторінки для збереження
    :param is_posts: Чи це сторінка з дописами
    :param is_reels: Чи це сторінка з reels
    :return: driver
    """
    try:
        logger.info(f"Початок обробки сторінки: {url}")
        
        # Переходимо на цільову сторінку
        logger.info("Завантаження сторінки...")
        driver.get(url)
        time.sleep(5)  # Чекаємо завантаження сторінки
        
        # Очікуємо завантаження тіла сторінки
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Визначаємо кількість скролів залежно від типу сторінки
        scroll_count = 10 if is_posts else 11 if is_reels else 3
        scroll_pause_time = 2  # Час очікування між скролами
        
        logger.info(f"Виконуємо {scroll_count} скролів...")
        
        # Виконуємо скрол сторінки
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        for i in range(scroll_count):
            # Прокручуємо до низу
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Очікуємо завантаження нових елементів
            time.sleep(scroll_pause_time)
            
            # Оновлюємо висоту сторінки після скролу
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # Якщо висота не змінилася, дочекаємося ще трохи
            if new_height == last_height:
                time.sleep(1)
                
            last_height = new_height
            logger.info(f"Виконано скрол {i+1}/{scroll_count}")
        
        # Отримуємо HTML після всіх скролів
        html_content = driver.page_source
        
        # Визначаємо ім'я файлу на основі типу контенту
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if is_posts:
            filename = f"instagram_posts.html"
        elif is_reels:
            filename = f"instagram_reels.html"
        else:
            filename = f"instagram_other.html"
        
        # Зберігаємо HTML у файл
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML сторінки збережено у файл: {filename}")
        return driver
        
    except Exception as e:
        logger.error(f"Помилка при збереженні сторінки {url}: {str(e)}")
        return driver
        
    