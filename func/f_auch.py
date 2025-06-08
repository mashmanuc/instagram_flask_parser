import os
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from func.f_time import random_sleep


def init_selenium():
    """
    Ініціалізує драйвер Selenium
    """
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
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
            
        # Переходимо на сторінку входу Instagram
        logger.info("Переходимо на сторінку входу Instagram")
        driver.get("https://www.instagram.com/accounts/login/")
        random_sleep()  # Даємо сторінці час завантажитись
        
        # Шукаємо поля для введення логіну та паролю
        try:
            # Спочатку спробуємо знайти і прийняти cookie якщо вони є
            try:
                cookie_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All') or contains(text(), 'Прийняти все')]")))                
                cookie_button.click()
                logger.info("Прийнято cookie")
                random_sleep()
            except Exception as e:
                logger.info(f"Немає вікна з cookie або помилка: {str(e)}")
            
            # Вводимо логін
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username")))
            username_field.clear()
            username_field.send_keys(username)
            logger.info(f"Введено логін: {username}")
            
            # Вводимо пароль
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password")))
            password_field.clear()
            password_field.send_keys(password)
            logger.info("Введено пароль")
            random_sleep()
            # Натискаємо кнопку входу
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
            login_button.click()
            logger.info("Натиснуто кнопку входу")
            
            # Чекаємо завершення авторизації
            random_sleep()
            
            # Перевіряємо чи успішно авторизувались
            if "login" in driver.current_url:
                logger.error("Помилка авторизації: залишились на сторінці входу")
                return False
                
            logger.info("Успішна авторизація в Instagram")
            return driver
            
        except Exception as auth_error:
            logger.error(f"Помилка при авторизації: {str(auth_error)}")
            return False
            
    except Exception as e:
        logger.error(f"Загальна помилка при авторизації: {str(e)}")
        return False
def get_page_with_pagination(driver,url):
    """Отримуємо сторінку Instagram"""
    try:
              
        # Переходимо на цільову сторінку
        logger.info(f"Переходимо на сторінку: {url}")
        driver.get(url)
        random_sleep()  # Зменшимо час очікування з 1000 до 5 секунд
        
        logger.info(f"Отримую сторінку instagram URL: {url}")
        
       
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        
        # Прокручуємо сторінку вниз для завантаження всіх елементів
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        
        # Отримуємо HTML сторінки
        html_content = driver.page_source
        
        # Зберігаємо сторінку у тимчасовий файл для подальшого аналізу
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_html_path = f"instagram_page_{timestamp}.html"
        
        try:
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Сторінка збережена у файл: {temp_html_path}")
        except Exception as e:
            logger.error(f"Помилка при збереженні HTML: {e}")
        
        return html_content
    except Exception as e:
        logger.error(f"Помилка при отриманні сторінки: {e}")
        return None
    finally:
        if driver:
            driver.quit()