import sqlite3
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DBViewer")

def connect_db():
    """З'єднання з базою даних"""
    try:
        conn = sqlite3.connect('instagram_data.db')
        return conn
    except Exception as e:
        logger.error(f"Помилка при підключенні до бази даних: {str(e)}")
        return None

def view_posts(conn, limit=10):
    """Перегляд постів з бази даних"""
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT id, post_type, media_url, description, parsed_date 
        FROM posts 
        ORDER BY id DESC 
        LIMIT ?
        """, (limit,))
        
        posts = cursor.fetchall()
        
        print("\n=== ОСТАННІ ЗАПИСИ В БАЗІ ДАНИХ ===")
        for post in posts:
            post_id, post_type, media_url, description, parsed_date = post
            
            print(f"\nID: {post_id}")
            print(f"Тип: {post_type}")
            print(f"URL: {media_url[:60]}..." if len(media_url) > 60 else f"URL: {media_url}")
            print(f"Опис: {description[:100]}..." if description and len(description) > 100 else f"Опис: {description}")
            print(f"Дата парсингу: {parsed_date}")
            print("-" * 50)
            
    except Exception as e:
        logger.error(f"Помилка при отриманні даних з бази: {str(e)}")

def main():
    conn = connect_db()
    if conn:
        view_posts(conn, 5)  # Показуємо останні 5 записів
        conn.close()
    else:
        logger.error("Не вдалося підключитися до бази даних")

if __name__ == "__main__":
    main()
