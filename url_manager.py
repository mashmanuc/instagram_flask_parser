#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для роботи з URL конфігурацією Instagram парсера

Цей модуль управляє читанням і зберіганням URL-адрес для парсингу Instagram у JSON файлі.
Переваги цього підходу:
1. URL зберігаються між рестартами сервера
2. Легко редагувати вручну у форматі JSON
3. Можна буде в майбутньому розширити для зберігання інших налаштувань

Приклад використання:
```python
from url_manager import get_urls, set_urls

# Отримати установлені URL
url_posts, url_reels = get_urls()

# Встановити нові URL
set_urls("https://www.instagram.com/username/", "https://www.instagram.com/username/reels")
```
"""

import json
import os
import logging

logger = logging.getLogger("UrlManager")

URL_CONFIG_FILE = "url_config.json"
DEFAULT_CONFIG = {
    "url_posts": "",
    "url_reels": ""
}

def load_url_config():
    """Завантажує URL конфігурацію з JSON файлу
    
    Читає файл url_config.json і повертає його вміст як словник.
    Якщо файл не існує, створює новий файл з пустими URL.
    При помилці читання повертає конфігурацію за замовчуванням.
    
    Returns:
        dict: Словник з url_posts та url_reels
    """
    if not os.path.exists(URL_CONFIG_FILE):
        save_url_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
        
    try:
        with open(URL_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Помилка при завантаженні URL конфігурації: {e}")
        return DEFAULT_CONFIG

def save_url_config(config):
    """Зберігає URL конфігурацію в JSON файл
    
    Записує конфігурацію URL у файл url_config.json в форматі JSON.
    При помилці збереження записує помилку в лог.
    
    Args:
        config (dict): Словник з конфігурацією URL.
                        Має містити ключі 'url_posts' та 'url_reels'.
    """
    try:
        with open(URL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Помилка при збереженні URL конфігурації: {e}")

def get_urls():
    """Отримує URL для постів та reels з JSON файлу
    
    Завантажує URL конфігурацію і повертає значення URL для постів та reels.
    Якщо значення відсутні, повертає пусті рядки.
    
    Returns:
        tuple: Кортеж (url_posts, url_reels) - адреси для скрапінгу постів та reels
    """
    config = load_url_config()
    return config.get("url_posts", ""), config.get("url_reels", "")

def set_urls(url_posts, url_reels):
    """Встановлює URL для постів та reels і зберігає в JSON файл
    
    Оновлює URL конфігурацію і записує її у файл url_config.json.
    
    Args:
        url_posts (str): URL для парсингу постів Instagram (напр. 'https://www.instagram.com/username/')
        url_reels (str): URL для парсингу reels (напр. 'https://www.instagram.com/username/reels')
    """
    config = load_url_config()
    config["url_posts"] = url_posts
    config["url_reels"] = url_reels
    save_url_config(config)
