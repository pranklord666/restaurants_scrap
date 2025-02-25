import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pranklord:qO1pVU1xCxvV4XKMT2jZgAh81KkLp4m5@dpg-cuuvnhdumphs73f3k6ug-a/restaurants_m0cf")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def get_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM rss_articles")
    articles = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1]} for row in articles]

def update_article_keyword(article_id, keyword):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rss_articles SET keyword = %s WHERE id = %s", (keyword, article_id))
    conn.commit()
    conn.close()

def delete_old_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rss_articles WHERE created_at < NOW() - INTERVAL '1 day'")
    conn.commit()
    conn.close()
