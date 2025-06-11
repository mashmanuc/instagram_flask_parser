#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Конфігурація акаунтів для Instagram скрапера
"""

# Список доступних акаунтів для скрапінгу
AVAILABLE_ACCOUNTS = [
    {
        "username": "club_okinawa_karate",  # Ім'я користувача в Instagram
        "display_name": "Клуб Окінава Карате",  # Назва для відображення
        "database": "instagram_okinawa.db",  # Назва файлу бази даних
        "images_folder": "okinawa"  # Назва папки для зображень в static/img/
    },
    # Можна додати інші акаунти за потреби
    {
        "username": "default",  # Акаунт за замовчуванням
        "display_name": "Основний акаунт",
        "database": "instagram_data.db",
        "images_folder": "instagram"
    }
]

# Функція для отримання конфігурації акаунта за ім'ям користувача
def get_account_config(username):
    """
    Повертає конфігурацію акаунта за ім'ям користувача
    
    Args:
        username (str): Ім'я користувача в Instagram
        
    Returns:
        dict: Конфігурація акаунта або конфігурація за замовчуванням, якщо акаунт не знайдено
    """
    for account in AVAILABLE_ACCOUNTS:
        if account["username"] == username:
            return account
    
    # Повертаємо конфігурацію за замовчуванням, якщо акаунт не знайдено
    return next((account for account in AVAILABLE_ACCOUNTS if account["username"] == "default"), AVAILABLE_ACCOUNTS[0])

# Функція для отримання списку всіх доступних акаунтів
def get_all_accounts():
    """
    Повертає список всіх доступних акаунтів
    
    Returns:
        list: Список словників з конфігураціями акаунтів
    """
    return AVAILABLE_ACCOUNTS
