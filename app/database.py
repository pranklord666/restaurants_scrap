import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    return psycopg2.connect(DATABASE_URL)

def get_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, keyword FROM articles")
    articles = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "summary": row[2], "keyword": row[3]} for row in articles]

def update_article_keyword(article_id, keyword):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE articles SET keyword = %s WHERE id = %s", (keyword, article_id))
    conn.commit()
    conn.close()

def delete_old_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles WHERE keyword IS NOT NULL")
    conn.commit()
    conn.close()
