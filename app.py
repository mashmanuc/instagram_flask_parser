#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Веб-інтерфейс на Flask для Instagram скрапера та парсера
"""

import os
import time
import sqlite3
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Імпортуємо функції з наших модулів
from selen import get_page_with_pagination
from parser import main_parser, init_db, print_stats
from func.f_auch import init_selenium, login_to_instagram, save_page
from accounts_config import get_account_config, get_all_accounts

# Завантажуємо змінні середовища
load_dotenv()

# Налаштування Flask
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "instagram_scraper_secret")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["DB_PATH"] = os.getenv("DB_PATH", "instagram_data.db")

# Створюємо директорію для завантажень, якщо вона не існує
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flask_app.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("FlaskApp")

# Глобальні змінні для відстеження стану
scraping_status = {
    "is_running": False,
    "start_time": None,
    "end_time": None,
    "status": "idle",
    "message": "Очікування запуску",
    "progress": 0,
    "duplicates_skipped": 0
}

def get_db_connection(account_username="default"):
    """Створює з'єднання з базою даних
    
    Args:
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
        
    Returns:
        sqlite3.Connection: З'єднання з базою даних
    """
    # Отримуємо конфігурацію акаунту
    account_config = get_account_config(account_username)
    database_name = account_config["database"]
    
    conn = sqlite3.connect(database_name)
    conn.row_factory = sqlite3.Row
    return conn

def get_stats(account_username="default"):
    """Отримує статистику з бази даних
    
    Args:
        account_username (str, optional): Ім'я акаунту Instagram. Defaults to "default".
        
    Returns:
        dict: Статистика постів
    """
    try:
        conn = get_db_connection(account_username)
        cursor = conn.cursor()
        
        stats = {}
        stats["account"] = account_username
        
        # Перевіряємо, чи існує таблиця posts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if not cursor.fetchone():
            logger.warning(f"Таблиця posts не існує для акаунту {account_username}. База даних порожня.")
            return {"account": account_username, "total_posts": 0, "regular_posts": 0, "reels": 0, "local_images": 0, "last_update": ""}
        
        # Загальна кількість постів для акаунту
        cursor.execute("SELECT COUNT(*) FROM posts WHERE account = ?", (account_username,))
        stats["total_posts"] = cursor.fetchone()[0]
        
        # Кількість звичайних постів для акаунту
        cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'post' AND account = ?", (account_username,))
        stats["regular_posts"] = cursor.fetchone()[0]
        
        # Кількість reels для акаунту
        cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'reel' AND account = ?", (account_username,))
        stats["reels"] = cursor.fetchone()[0]
        
        # Кількість локальних зображень для акаунту
        cursor.execute("SELECT COUNT(*) FROM posts WHERE local_path IS NOT NULL AND local_path != '' AND account = ?", (account_username,))
        stats["local_images"] = cursor.fetchone()[0]
        
        # Останнє оновлення для акаунту
        cursor.execute("SELECT MAX(parsed_date) FROM posts WHERE account = ?", (account_username,))
        last_update = cursor.fetchone()[0]
        stats["last_update"] = last_update if last_update else ""
        
        # Отримуємо список всіх доступних акаунтів
        stats["available_accounts"] = get_all_accounts()
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Помилка при отриманні статистики для акаунту {account_username}: {str(e)}")
        return {"account": account_username, "total_posts": 0, "regular_posts": 0, "reels": 0, "local_images": 0, "last_update": "", "available_accounts": get_all_accounts()}


def run_scraper():
    """Запускає процес скрапінгу в окремому потоці"""
    global scraping_status
    
    try:
        scraping_status["is_running"] = True
        scraping_status["start_time"] = datetime.now()
        scraping_status["status"] = "running"
        scraping_status["message"] = "Запуск скрапінгу..."
        scraping_status["progress"] = 10
        scraping_status["duplicates_skipped"] = 0
        
        # Запускаємо скрапінг
        logger.info("Запуск скрапінгу Instagram...")
        scraping_status["message"] = "Скрапінг Instagram..."
        scraping_status["progress"] = 30
        get_page_with_pagination()
        
        # Запускаємо парсинг
        logger.info("Запуск парсингу HTML...")
        scraping_status["message"] = "Парсинг HTML..."
        scraping_status["progress"] = 60
        
        # Модифікуємо парсер для відстеження дублікатів
        conn = sqlite3.connect(app.config["DB_PATH"])
        skipped_count = main_parser()
        
        # Оновлюємо статус з інформацією про дублікати
        if isinstance(skipped_count, int):
            scraping_status["duplicates_skipped"] = skipped_count
            logger.info(f"Пропущено {skipped_count} дублікатів контенту")
        
        # Завершуємо процес
        scraping_status["status"] = "completed"
        scraping_status["message"] = f"Скрапінг та парсинг успішно завершено. Пропущено {scraping_status['duplicates_skipped']} дублікатів."
        scraping_status["progress"] = 100
        scraping_status["end_time"] = datetime.now()
        logger.info("Процес скрапінгу та парсингу завершено успішно")
        
    except Exception as e:
        logger.error(f"Помилка при скрапінгу: {e}")
        scraping_status["status"] = "error"
        scraping_status["message"] = f"Помилка: {str(e)}"
        scraping_status["progress"] = 0
    
    finally:
        scraping_status["is_running"] = False

@app.route('/')
def index():
    """Головна сторінка"""
    account = request.args.get('account', 'default')
    stats = get_stats(account)
    return render_template('index.html', stats=stats, status=scraping_status)

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Запускає процес скрапінгу"""
    global scraping_status
    
    if scraping_status["is_running"]:
        flash("Процес скрапінгу вже запущено!", "warning")
        return redirect(url_for('index'))
    
    # Запускаємо скрапінг у окремому потоці
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    flash("Процес скрапінгу запущено!", "success")
    return redirect(url_for('index'))

@app.route('/status')
def status():
    """Повертає поточний статус скрапінгу у форматі JSON"""
    return jsonify(scraping_status)

@app.route('/get_logs')
def get_logs():
    """Повертає останні записи з лог-файлу"""
    try:
        # Читаємо останні 50 рядків з лог-файлу
        log_file = "flask_app.log"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
                # Залишаємо тільки останні 50 рядків
                logs = logs[-50:] if len(logs) > 50 else logs
                # Видаляємо зайві переноси рядків
                logs = [log.strip() for log in logs if log.strip()]
                return jsonify({"logs": logs})
        else:
            return jsonify({"logs": ["Log file not found"]})
    except Exception as e:
        logger.error(f"Помилка при читанні логів: {e}")
        return jsonify({"logs": [f"Помилка при читанні логів: {e}"]}), 500

@app.route('/posts')
def posts():
    """Сторінка з постами"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    post_type = request.args.get('type', 'all')
    account = request.args.get('account', 'default')
    
    conn = get_db_connection(account)
    cursor = conn.cursor()
    
    # Отримуємо список всіх доступних акаунтів
    available_accounts = get_all_accounts()
    
    # Перевіряємо, чи існує таблиця posts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
    if not cursor.fetchone():
        logger.warning(f"Таблиця posts не існує для акаунту {account}. База даних порожня.")
        return render_template('posts.html', posts=[], page=page, per_page=per_page, 
                           total_posts=0, post_type=post_type, account=account, 
                           available_accounts=available_accounts)
    
    # Формуємо SQL запит залежно від типу постів та акаунту
    if post_type == 'post':
        cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'post' AND account = ?", (account,))
        query = "SELECT * FROM posts WHERE post_type = 'post' AND account = ? ORDER BY parsed_date DESC LIMIT ? OFFSET ?"
        params = (account, per_page, offset)
    elif post_type == 'reel':
        cursor.execute("SELECT COUNT(*) FROM posts WHERE post_type = 'reel' AND account = ?", (account,))
        query = "SELECT * FROM posts WHERE post_type = 'reel' AND account = ? ORDER BY parsed_date DESC LIMIT ? OFFSET ?"
        params = (account, per_page, offset)
    else:
        cursor.execute("SELECT COUNT(*) FROM posts WHERE account = ?", (account,))
        query = "SELECT * FROM posts WHERE account = ? ORDER BY parsed_date DESC LIMIT ? OFFSET ?"
        params = (account, per_page, offset)
    
    # Загальна кількість постів
    total_posts = cursor.fetchone()[0]
    
    # Пагінація
    cursor.execute(query, params)
    posts = cursor.fetchall()
    
    # Діагностика: виводимо інформацію про пости
    logger.info(f"Знайдено {len(posts)} постів типу '{post_type}'")
    if posts:
        sample_post = dict(posts[0])
        logger.info(f"Приклад посту: {sample_post}")
        logger.info(f"Ключі в пості: {list(sample_post.keys())}")
    
    # Загальна кількість сторінок
    total_pages = (total_posts + per_page - 1) // per_page
    
    conn.close()
    
    return render_template(
        'posts.html', 
        posts=posts, 
        page=page, 
        total_pages=total_pages, 
        per_page=per_page,
        post_type=post_type,
        total_posts=total_posts,
        account=account,
        available_accounts=available_accounts
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Сторінка налаштувань"""
    if request.method == 'POST':
        # Зберігаємо налаштування
        instagram_username = request.form.get('instagram_username')
        instagram_password = request.form.get('instagram_password')
        url_dopys = request.form.get('url_dopys')
        url_reels = request.form.get('url_reels')
        headless = request.form.get('headless') == 'on'
        
        # Оновлюємо .env файл
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        updated = {
            'INSTAGRAM_USERNAME': False,
            'INSTAGRAM_PASSWORD': False,
            'URL_DOPYS': False,
            'URL_REELS': False,
            'HEADLESS': False
        }
        
        for line in lines:
            if line.startswith('INSTAGRAM_USERNAME='):
                new_lines.append(f'INSTAGRAM_USERNAME={instagram_username}\n')
                updated['INSTAGRAM_USERNAME'] = True
            elif line.startswith('INSTAGRAM_PASSWORD='):
                new_lines.append(f'INSTAGRAM_PASSWORD={instagram_password}\n')
                updated['INSTAGRAM_PASSWORD'] = True
            elif line.startswith('URL_DOPYS='):
                new_lines.append(f'URL_DOPYS={url_dopys}\n')
                updated['URL_DOPYS'] = True
            elif line.startswith('URL_REELS='):
                new_lines.append(f'URL_REELS={url_reels}\n')
                updated['URL_REELS'] = True
            elif line.startswith('HEADLESS='):
                new_lines.append(f'HEADLESS={"True" if headless else "False"}\n')
                updated['HEADLESS'] = True
            else:
                new_lines.append(line)
        
        # Додаємо відсутні налаштування
        for key, value in updated.items():
            if not value:
                if key == 'HEADLESS':
                    new_lines.append(f'{key}={"True" if headless else "False"}\n')
                elif key == 'INSTAGRAM_USERNAME':
                    new_lines.append(f'{key}={instagram_username}\n')
                elif key == 'INSTAGRAM_PASSWORD':
                    new_lines.append(f'{key}={instagram_password}\n')
                elif key == 'URL_DOPYS':
                    new_lines.append(f'{key}={url_dopys}\n')
                elif key == 'URL_REELS':
                    new_lines.append(f'{key}={url_reels}\n')
        
        # Записуємо оновлений .env файл
        with open('.env', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        flash("Налаштування успішно збережено!", "success")
        return redirect(url_for('settings'))
    
    # Отримуємо поточні налаштування
    instagram_username = os.getenv('INSTAGRAM_USERNAME', '')
    instagram_password = os.getenv('INSTAGRAM_PASSWORD', '')
    url_dopys = os.getenv('URL_DOPYS', '')
    url_reels = os.getenv('URL_REELS', '')
    headless = os.getenv('HEADLESS', 'False').lower() == 'true'
    
    return render_template(
        'settings.html',
        instagram_username=instagram_username,
        instagram_password=instagram_password,
        url_dopys=url_dopys,
        url_reels=url_reels,
        headless=headless
    )

@app.route('/export', methods=['GET'])
def export():
    """Сторінка експорту даних"""
    return render_template('export.html')

@app.route('/export/json', methods=['GET'])
def export_json():
    """Експортує дані у форматі JSON"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM posts")
    posts = cursor.fetchall()
    
    # Конвертуємо результати у список словників
    result = []
    for post in posts:
        post_dict = {}
        for key in post.keys():
            post_dict[key] = post[key]
        result.append(post_dict)
    
    conn.close()
    
    # Створюємо тимчасовий файл
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"instagram_export_{timestamp}.json"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        import json
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )

@app.route('/export/csv', methods=['GET'])
def export_csv():
    """Експортує дані у форматі CSV"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM posts")
    posts = cursor.fetchall()
    
    # Отримуємо назви стовпців
    column_names = [description[0] for description in cursor.description]
    
    conn.close()
    
    # Створюємо тимчасовий файл
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"instagram_export_{timestamp}.csv"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(column_names)
        for post in posts:
            writer.writerow(post)
    
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )

# Ініціалізуємо базу даних при запуску
from parser import init_db

# Переконуємося, що таблиці існують
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
