#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль з покращеннями для Instagram Scraper та Парсер
Цей файл містить функції, які роблять проект більш універсальним
"""

import os
import argparse
import logging
import configparser
import sqlite3
from datetime import datetime
from pathlib import Path

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("parser.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("InstagramImprover")

def create_config_file(config_path="config.ini"):
    """
    Створює конфігураційний файл з налаштуваннями за замовчуванням
    """
    config = configparser.ConfigParser()
    
    # Основні налаштування
    config["DEFAULT"] = {
        "HeadlessMode": "False",
        "ScrollCount": "10",
        "ScrollPauseTime": "2",
        "DatabasePath": "instagram_data.db",
        "LogFile": "parser.log",
        "OutputDir": "output"
    }
    
    # Налаштування Instagram
    config["INSTAGRAM"] = {
        "Username": "",
        "Password": "",
        "PostsUrl": "https://www.instagram.com/your_account/",
        "ReelsUrl": "https://www.instagram.com/your_account/reels/"
    }
    
    # Налаштування парсера
    config["PARSER"] = {
        "PostsFile": "instagram_posts.html",
        "ReelsFile": "instagram_reels.html",
        "DeleteAfterParsing": "True",
        "SaveImages": "False",
        "ImagesDir": "images"
    }
    
    # Налаштування Selenium
    config["SELENIUM"] = {
        "ImplicitWait": "10",
        "PageLoadTimeout": "30",
        "WindowWidth": "1920",
        "WindowHeight": "1080"
    }
    
    # Запис конфігурації у файл
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
    
    logger.info(f"Створено конфігураційний файл: {config_path}")
    return config

def load_config(config_path="config.ini"):
    """
    Завантажує конфігурацію з файлу або створює нову, якщо файл не існує
    """
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        logger.warning(f"Конфігураційний файл {config_path} не знайдено. Створюємо новий...")
        return create_config_file(config_path)
    
    config.read(config_path, encoding='utf-8')
    logger.info(f"Завантажено конфігурацію з {config_path}")
    return config

def create_directory_structure(config):
    """
    Створює необхідну структуру директорій на основі конфігурації
    """
    directories = [
        config["DEFAULT"]["OutputDir"],
        config["PARSER"]["ImagesDir"] if config["PARSER"].getboolean("SaveImages") else None
    ]
    
    for directory in directories:
        if directory:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Створено директорію: {directory}")

def setup_command_line_args():
    """
    Налаштовує аргументи командного рядка для більш гнучкого запуску
    """
    parser = argparse.ArgumentParser(description="Instagram Scraper та Парсер")
    
    # Загальні аргументи
    parser.add_argument("--config", default="config.ini", help="Шлях до конфігураційного файлу")
    parser.add_argument("--mode", choices=["scrape", "parse", "both"], default="both", 
                        help="Режим роботи: scrape - тільки скрапінг, parse - тільки парсинг, both - обидва (за замовчуванням)")
    
    # Аргументи для скрапінгу
    parser.add_argument("--headless", action="store_true", help="Запустити браузер у фоновому режимі")
    parser.add_argument("--url", help="URL для скрапінгу (перевизначає налаштування з конфігурації)")
    parser.add_argument("--scrolls", type=int, help="Кількість скролів сторінки")
    
    # Аргументи для парсингу
    parser.add_argument("--input", help="Шлях до HTML файлу для парсингу")
    parser.add_argument("--db", help="Шлях до бази даних SQLite")
    parser.add_argument("--save-images", action="store_true", help="Зберігати зображення локально")
    
    # Аргументи для виведення
    parser.add_argument("--verbose", action="store_true", help="Детальне логування")
    parser.add_argument("--stats", action="store_true", help="Показати статистику після виконання")
    
    return parser.parse_args()

def download_media(url, output_dir, filename=None):
    """
    Завантажує медіа за URL та зберігає його локально
    """
    import requests
    from urllib.parse import urlparse
    
    try:
        if not filename:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
        # Створюємо директорію, якщо вона не існує
        os.makedirs(output_dir, exist_ok=True)
        
        # Повний шлях для збереження файлу
        file_path = os.path.join(output_dir, filename)
        
        # Завантажуємо файл
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Завантажено медіа: {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Помилка при завантаженні медіа {url}: {str(e)}")
        return None

def export_data_to_json(conn, output_file="instagram_data.json"):
    """
    Експортує дані з бази даних у JSON формат
    """
    import json
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts")
        
        # Отримуємо назви стовпців
        column_names = [description[0] for description in cursor.description]
        
        # Отримуємо дані
        rows = cursor.fetchall()
        
        # Формуємо список словників
        data = []
        for row in rows:
            item = {}
            for i, column in enumerate(column_names):
                item[column] = row[i]
            data.append(item)
        
        # Зберігаємо у JSON файл
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"Дані експортовано у файл: {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Помилка при експорті даних: {str(e)}")
        return False

def backup_database(db_path="instagram_data.db", backup_dir="backups"):
    """
    Створює резервну копію бази даних
    """
    try:
        # Створюємо директорію для резервних копій
        os.makedirs(backup_dir, exist_ok=True)
        
        # Формуємо ім'я файлу резервної копії
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")
        
        # Копіюємо базу даних
        conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_file)
        
        conn.backup(backup_conn)
        
        conn.close()
        backup_conn.close()
        
        logger.info(f"Створено резервну копію бази даних: {backup_file}")
        return backup_file
    
    except Exception as e:
        logger.error(f"Помилка при створенні резервної копії: {str(e)}")
        return None

def main():
    """
    Головна функція для демонстрації покращень
    """
    # Отримуємо аргументи командного рядка
    args = setup_command_line_args()
    
    # Завантажуємо конфігурацію
    config = load_config(args.config)
    
    # Створюємо необхідну структуру директорій
    create_directory_structure(config)
    
    # Виводимо інформацію про налаштування
    logger.info("=== Налаштування ===")
    logger.info(f"Режим роботи: {args.mode}")
    logger.info(f"Headless режим: {args.headless or config['DEFAULT'].getboolean('HeadlessMode')}")
    logger.info(f"База даних: {args.db or config['DEFAULT']['DatabasePath']}")
    
    # Тут можна викликати інші функції в залежності від аргументів
    
    logger.info("Покращення для універсальності проекту успішно демонстровано")

if __name__ == "__main__":
    main()
