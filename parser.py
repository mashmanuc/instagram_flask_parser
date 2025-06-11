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

# Створюємо директорію для зображень, якщо вона не існує
IMAGE_DIR = Path('static/img/instagram')
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

def download_and_save_image(url, post_type, post_id=None):
    """
    Завантажує зображення за URL та зберігає його локально
    Повертає шлях до збереженого зображення або None у разі помилки
    """
    if not url:
        logger.warning("Порожній URL для завантаження зображення")
        return None
        
    try:
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
            
        local_path = IMAGE_DIR / filename
        
        # Перевіряємо, чи файл вже існує
        if local_path.exists():
            logger.info(f"Зображення вже існує локально: {local_path}")
            return str(local_path).replace('\\', '/')
            
        # Завантажуємо зображення
        logger.info(f"Завантажуємо зображення з URL: {url[:50]}...")
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
def init_db():
    """Створює базу даних, якщо вона не існує"""
    conn = sqlite3.connect('instagram_data.db')
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
        local_path TEXT
    )
    ''')
    
    conn.commit()
    logger.info("Таблицю постів створено успішно")
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
def save_to_db(items, conn):
    """Зберігає дані у базу"""
    if not items:
        logger.warning("Немає даних для збереження в базу")
        return 0, 0
    
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
                local_path = cursor.fetchone()[0]
                
                if not local_path or not os.path.exists(local_path):
                    logger.info(f"Завантажуємо зображення для існуючого запису ID: {post_id}")
                    local_path = download_and_save_image(media_url, post_type, post_id)
                    if local_path:
                        cursor.execute("UPDATE posts SET local_path = ? WHERE id = ?", (local_path, post_id))
                        conn.commit()
                        logger.info(f"Оновлено локальний шлях для запису ID: {post_id}")
                
                continue
            
            # Завантажуємо зображення
            local_path = download_and_save_image(media_url, post_type)
            
            # Додаємо запис у базу даних
            cursor.execute('''
            INSERT INTO posts (post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post_type, media_url, description, timestamp, username, is_video, parsed_date, local_path))
            
            added_count += 1
            
        except Exception as e:
            logger.error(f"Помилка при збереженні в базу: {str(e)}")
    
    conn.commit()
    logger.info(f"Збережено {added_count} нових елементів у базу даних, пропущено {skipped_count} дублікатів")
    return added_count, skipped_count

# Функція для виведення статистики
def print_stats(conn):
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'post'")
    post_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'reel'")
    reel_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_count = cursor.fetchone()[0]
    
    logger.info("=== Статистика бази даних ===")
    logger.info(f"Всього записів: {total_count}")
    logger.info(f"Дописів: {post_count}")
    logger.info(f"Reels: {reel_count}")
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
def main_parser():
    logger.info("Починаємо роботу парсера...")
    
    # Ініціалізація БД
    conn = init_db()
    
    # Лічильники для відстеження дублікатів
    total_added = 0
    total_skipped = 0
    
    # Парсимо пости
    posts_file = "instagram_posts.html"
    if os.path.exists(posts_file):
        posts = parse_posts()
        added, skipped = save_to_db(posts, conn)
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
        added, skipped = save_to_db(reels, conn)
        total_added += added
        total_skipped += skipped
        # Видаляємо HTML файл після парсингу
        remove_html_file(reels_file)
    else:
        logger.warning(f"Файл {reels_file} не знайдено")
    
    # Виводимо статистику
    print_stats(conn)
    
    # Закриваємо з'єднання з БД
    conn.close()
    logger.info(f"Парсинг завершено. Додано: {total_added}, пропущено дублікатів: {total_skipped}")
    
    # Повертаємо кількість пропущених дублікатів
    return total_skipped

# Запускаємо парсер, якщо скрипт запущений напряму
if __name__ == "__main__":
    main_parser()