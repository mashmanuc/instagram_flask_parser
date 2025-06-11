import sqlite3
import logging
import os

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flask_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DBMigration')

def migrate_db():
    """Міграція бази даних для додавання поля local_path"""
    try:
        # Перевіряємо, чи існує база даних
        if not os.path.exists('instagram_data.db'):
            logger.error("База даних не знайдена")
            return False
            
        conn = sqlite3.connect('instagram_data.db')
        cursor = conn.cursor()
        
        # Перевіряємо, чи існує колонка local_path
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'local_path' not in columns:
            logger.info("Додаємо колонку local_path до таблиці posts")
            cursor.execute("ALTER TABLE posts ADD COLUMN local_path TEXT")
            conn.commit()
            logger.info("Колонку local_path успішно додано")
        else:
            logger.info("Колонка local_path вже існує")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Помилка при міграції бази даних: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_db()
