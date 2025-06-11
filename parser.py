import os
import sqlite3
import json
import logging
import time
import requests
import hashlib
import urllib.parse
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

# Імпортуємо конфігурацію акаунтів
from accounts_config import get_account_config, get_all_accounts

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flask_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('InstagramParser')

# Створюємо базову директорію для зображень
BASE_IMAGE_DIR = Path('static/img')
BASE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Створюємо директорії для зображень для кожного акаунту
def ensure_account_directories():
    """Створює директорії для зображень для кожного акаунту"""
    for account in get_all_accounts():
        img_dir = BASE_IMAGE_DIR / account["images_folder"]
        img_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Створено директорію для зображень акаунту {account['username']}: {img_dir}")

# Створюємо директорії при запуску
ensure_account_directories()

def download_and_save_image(url, post_type, post_id=None, account_username="default"):
    """
    Завантажує зображення за URL та зберігає його локально
    
    Args:
        url (str): URL зображення для завантаження
        post_type (str): Тип посту (post, reel)
        post_id (str, optional): Ідентифікатор посту. Defaults to None.
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
        
    Returns:
        str: Шлях до збереженого зображення або None у разі помилки
    """
    if not url:
        logger.warning("Порожній URL для завантаження зображення")
        return None
        
    try:
        # Отримуємо конфігурацію акаунту
        account_config = get_account_config(account_username)
        images_folder = account_config["images_folder"]
        
        # Генеруємо унікальне ім'я файлу на основі URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        file_ext = '.jpg'  # За замовчуванням
        
        # Спробуємо отримати розширення з URL
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        if '.' in path:
            file_ext = os.path.splitext(path)[1].lower()
            if not file_ext or len(file_ext) > 5:  # Якщо розширення відсутнє або занадто довге
                file_ext = '.jpg'
        
        # Формуємо шлях для збереження
        if post_id:
            filename = f"{post_type}_{post_id}_{url_hash[:8]}{file_ext}"
        else:
            filename = f"{post_type}_{url_hash}{file_ext}"
        
        # Використовуємо папку для зображень конкретного акаунту
        local_path = BASE_IMAGE_DIR / images_folder / filename
        
        # Перевіряємо, чи файл вже існує
        if local_path.exists():
            logger.info(f"Зображення вже існує локально: {local_path}")
            return str(local_path).replace('\\', '/')
            
        # Завантажуємо зображення
        logger.info(f"Завантажуємо зображення з URL: {url[:50]}... для акаунту {account_username}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Перевіряємо на помилки HTTP
        
        # Зберігаємо зображення
        with open(local_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Зображення успішно збережено: {local_path}")
        return str(local_path).replace('\\', '/')
        
    except Exception as e:
        logger.error(f"Помилка при завантаженні зображення: {str(e)}")
        return None

# Функція для створення бази даних
def init_db(database_name='instagram_data.db'):
    """Створює базу даних, якщо вона не існує
    
    Args:
        database_name (str): Назва файлу бази даних
    
    Returns:
        sqlite3.Connection: З'єднання з базою даних
    """
    conn = sqlite3.connect(database_name)
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
    logger.info(f"Таблицю постів створено успішно в базі даних {database_name}")
    return conn

# Функція для парсингу HTML сторінки з дописами
def parse_posts():
    logger.info("Починаємо парсинг постів...")
    try:
        with open("instagram_posts.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Знаходимо всі дописи на сторінці
        all_posts = []
        
        # Знаходимо всі зображення
        images = soup.find_all("img")
        logger.info(f"Знайдено {len(images)} зображень на сторінці")
        
        for img in images:
            if img.get('src') and not img.get('src').endswith('.ico'):
                # Це потенційно допис
                post = {
                    'post_type': 'post',
                    'media_url': img.get('src'),
                    'description': img.get('alt', '') if img.get('alt') else '',
                    'timestamp': '',
                    'username': '',
                    'is_video': False
                }
                all_posts.append(post)
                logger.info(f"Знайдено зображення: {post['media_url'][:50]}...")
        
        # Знаходимо всі блоки з дописами
        post_containers = soup.find_all("div", class_="x1lliihq x1n2onr6 xh8yej3") 
        logger.info(f"Знайдено {len(post_containers)} контейнерів з дописами")
        
        # Якщо знайшли контейнери, додаткова обробка
        for i, container in enumerate(post_containers):
            # Шукаємо опис
            caption = container.find("span", class_="_aacl _aaco _aacu _aacx _aad7 _aade")
            if caption and i < len(all_posts):
                all_posts[i]['description'] = caption.text.strip()
                logger.info(f"Додано опис до посту {i+1}: {caption.text[:30]}...")
        
        logger.info(f"Всього знайдено {len(all_posts)} постів")
        return all_posts
    
    except Exception as e:
        logger.error(f"Помилка під час парсингу постів: {str(e)}")
        return []

# Функція для парсингу HTML сторінки з reels
def parse_reels():
    logger.info("Починаємо парсинг reels...")
    try:
        with open("instagram_reels.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Знаходимо всі reels на сторінці
        all_reels = []
        
        # Шукаємо відео або превью відео
        videos = soup.find_all("video")
        logger.info(f"Знайдено {len(videos)} відео")
        
        for video in videos:
            if video.get('src'):
                reel = {
                    'post_type': 'reel',
                    'media_url': video.get('src'),
                    'description': '',
                    'timestamp': '',
                    'username': '',
                    'is_video': True
                }
                all_reels.append(reel)
                logger.info(f"Знайдено відео: {reel['media_url'][:50]}...")
        
        # Якщо відео не знайшли, шукаємо превью зображення
        if not all_reels:
            images = soup.find_all("img")
            logger.info(f"Знайдено {len(images)} зображень (превью reels)")
            
            for img in images:
                if img.get('src') and not img.get('src').endswith('.ico'):
                    reel = {
                        'post_type': 'reel',
                        'media_url': img.get('src'),
                        'description': img.get('alt', '') if img.get('alt') else '',
                        'timestamp': '',
                        'username': '',
                        'is_video': True
                    }
                    all_reels.append(reel)
        
        # Знаходимо заголовки і описи
        titles = soup.find_all("h1", class_="_ap3a _aaco _aacu _aacx _aad7 _aade")
        logger.info(f"Знайдено {len(titles)} заголовків")
        
        for i, title in enumerate(titles):
            if i < len(all_reels):
                all_reels[i]['description'] = title.text.strip()
                logger.info(f"Додано опис до reel {i+1}: {title.text[:30]}...")
        
        logger.info(f"Всього знайдено {len(all_reels)} reels")
        return all_reels
    
    except Exception as e:
        logger.error(f"Помилка під час парсингу reels: {str(e)}")
        return []

# Функція для збереження даних у базу
def save_to_db(items, conn=None, account_username="default"):
    """Зберігає дані у базу
    
    Args:
        items (list): Список постів для збереження
        conn (sqlite3.Connection, optional): З'єднання з базою даних. Defaults to None.
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
        
    Returns:
        tuple: Кількість доданих та пропущених записів
    """
    if not items:
        logger.warning("Немає даних для збереження в базу")
        return 0, 0
    
    # Отримуємо конфігурацію акаунту
    account_config = get_account_config(account_username)
    database_name = account_config["database"]
    
    # Якщо з'єднання не передано, створюємо нове
    if conn is None:
        conn = init_db(database_name)
    
    cursor = conn.cursor()
    added_count = 0
    skipped_count = 0
    
    for item in items:
        try:
            post_type = item.get('post_type')
            media_url = item.get('media_url')
            description = item.get('description')
            timestamp = item.get('timestamp')
            username = item.get('username')
            is_video = item.get('is_video', False)
            parsed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if not media_url:
                logger.warning("Пропускаємо запис без URL медіа")
                continue
            
            # Ефективна перевірка по індексу
            cursor.execute("SELECT id FROM posts WHERE media_url = ? LIMIT 1", (media_url,))
            existing_post = cursor.fetchone()
            if existing_post:
                logger.info(f"URL вже існує в базі: {media_url[:30]}...")
                skipped_count += 1
                
                # Спробуємо завантажити зображення для існуючого запису, якщо воно ще не завантажено
                post_id = existing_post[0]
                cursor.execute("SELECT local_path FROM posts WHERE id = ?", (post_id,))
                local_path_result = cursor.fetchone()
                local_path = local_path_result[0] if local_path_result and local_path_result[0] else None
                
                if not local_path or not os.path.exists(local_path):
                    logger.info(f"Завантажуємо зображення для існуючого запису ID: {post_id}")
                    local_path = download_and_save_image(media_url, post_type, post_id, account_username)
                    if local_path:
                        cursor.execute("UPDATE posts SET local_path = ?, account = ? WHERE id = ?", (local_path, account_username, post_id))
                        conn.commit()
                        logger.info(f"Оновлено локальний шлях для запису ID: {post_id}")
                
                continue
            
            # Завантажуємо зображення
            local_path = download_and_save_image(media_url, post_type, None, account_username)
            
            # Додаємо запис у базу даних
            cursor.execute('''
            INSERT INTO posts (post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path, account)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path, account_username))
            
            added_count += 1
            
        except Exception as e:
            logger.error(f"Помилка при збереженні в базу: {str(e)}")
    
    conn.commit()
    logger.info(f"Збережено {added_count} нових елементів у базу даних {database_name}, пропущено {skipped_count} дублікатів")
    return added_count, skipped_count

# Функція для виведення статистики
def print_stats(conn, account_username="default"):
    """Виводить статистику бази даних
    
    Args:
        conn (sqlite3.Connection): З'єднання з базою даних
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
    """
    cursor = conn.cursor()
    
    # Отримуємо конфігурацію акаунту
    account_config = get_account_config(account_username)
    
    # Статистика для конкретного акаунту
    cursor.execute("SELECT COUNT(*) FROM posts WHERE account = ?", (account_username,))
    account_total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'post' AND account = ?", (account_username,))
    post_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'reel' AND account = ?", (account_username,))
    reel_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE local_path IS NOT NULL AND local_path != '' AND account = ?", (account_username,))
    local_images_count = cursor.fetchone()[0]
    
    # Загальна статистика
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_count = cursor.fetchone()[0]
    
    logger.info(f"=== Статистика бази даних для акаунту {account_username} ===")
    logger.info(f"Всього записів для акаунту: {account_total}")
    logger.info(f"Дописів: {post_count}")
    logger.info(f"Reels: {reel_count}")
    logger.info(f"Локальних зображень: {local_images_count}")
    logger.info(f"Всього записів в базі: {total_count}")
    logger.info("===========================")

# Функція для видалення HTML файлів
def remove_html_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл {file_path} успішно видалено")
        else:
            logger.warning(f"Файл {file_path} не знайдено для видалення")
    except Exception as e:
        logger.error(f"Помилка при видаленні файлу {file_path}: {str(e)}")

# Головна функція
def main_parser(account_username="default"):
    """Головна функція парсера
    
    Args:
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
        
    Returns:
        tuple: Кількість доданих та пропущених записів
    """
    logger.info(f"Починаємо роботу парсера для акаунту {account_username}...")
    
    # Отримуємо конфігурацію акаунту
    account_config = get_account_config(account_username)
    database_name = account_config["database"]
    
    # Ініціалізація БД
    conn = init_db(database_name)
    
    # Лічильники для відстеження дублікатів
    total_added = 0
    total_skipped = 0
    
    # Парсимо пости
    posts_file = "instagram_posts.html"
    if os.path.exists(posts_file):
        posts = parse_posts()
        added, skipped = save_to_db(posts, conn, account_username)
        total_added += added
        total_skipped += skipped
        # Видаляємо HTML файл після парсингу
        remove_html_file(posts_file)
    else:
        logger.warning(f"Файл {posts_file} не знайдено")
    
    # Парсимо reels
    reels_file = "instagram_reels.html"
    if os.path.exists(reels_file):
        reels = parse_reels()
        added, skipped = save_to_db(reels, conn, account_username)
        total_added += added
        total_skipped += skipped
        # Видаляємо HTML файл після парсингу
        remove_html_file(reels_file)
    
    # Виводимо статистику
    print_stats(conn, account_username)
    
    # Закриваємо з'єднання з базою даних
    conn.close()
    
    logger.info(f"Парсер завершив роботу для акаунту {account_username}. Додано: {total_added}, пропущено дублікатів: {total_skipped}")
    return total_added, total_skipped  # Повертаємо кількість пропущених дублікатів

# Запускаємо парсер, якщо скрипт запущений напряму
if __name__ == "__main__":
    main_parser()