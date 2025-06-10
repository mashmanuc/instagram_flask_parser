import os
import sqlite3
import logging
import json
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
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
logger = logging.getLogger("InstagramParser")

# Функція для створення бази даних
def init_db():
    logger.info("Ініціалізація бази даних...")
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
        is_video BOOLEAN,
        parsed_date TEXT
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
    if not items:
        logger.warning("Немає даних для збереження в базу")
        return
    
    cursor = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved_count = 0
    skipped_count = 0
    
    # Створюємо індекс для швидшого пошуку
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_url ON posts(media_url)")
        conn.commit()
    except Exception as e:
        logger.warning(f"Не вдалося створити індекс: {str(e)}")
    
    for item in items:
        try:
            media_url = item.get('media_url', '')
            if not media_url:
                logger.warning("Пропускаємо запис без URL")
                continue
            
            # Ефективна перевірка по індексу
            cursor.execute("SELECT 1 FROM posts WHERE media_url = ? LIMIT 1", (media_url,))
            if cursor.fetchone():
                logger.info(f"URL вже існує в базі: {media_url[:30]}...")
                skipped_count += 1
                continue
                
            cursor.execute('''
            INSERT INTO posts (post_type, media_url, description, timestamp, username, is_video, parsed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('post_type', ''),
                media_url,
                item.get('description', ''),
                item.get('timestamp', ''),
                item.get('username', ''),
                item.get('is_video', False),
                current_date
            ))
            
            saved_count += 1
            logger.info(f"Збережено допис у базу: {media_url[:30]}...")
            
        except Exception as e:
            logger.error(f"Помилка при збереженні в базу: {str(e)}")
    
    conn.commit()
    logger.info(f"Збережено {saved_count} нових елементів у базу даних, пропущено {skipped_count} дублікатів")

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
    
    # Парсимо пости
    posts_file = "instagram_posts.html"
    if os.path.exists(posts_file):
        posts = parse_posts()
        save_to_db(posts, conn)
        # Видаляємо HTML файл після парсингу
        remove_html_file(posts_file)
    else:
        logger.warning(f"Файл {posts_file} не знайдено")
    
    # Парсимо reels
    reels_file = "instagram_reels.html"
    if os.path.exists(reels_file):
        reels = parse_reels()
        save_to_db(reels, conn)
        # Видаляємо HTML файл після парсингу
        remove_html_file(reels_file)
    else:
        logger.warning(f"Файл {reels_file} не знайдено")
    
    # Виводимо статистику
    print_stats(conn)
    
    # Закриваємо з'єднання з БД
    conn.close()
    logger.info("Парсинг завершено")

# Запускаємо парсер, якщо скрипт запущений напряму
if __name__ == "__main__":
    main_parser()