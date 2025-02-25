import psycopg2
import os
from typing import List, Tuple

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rss_articles (
            id SERIAL PRIMARY KEY,
            date TEXT,
            title TEXT,
            raw_content TEXT,
            summary TEXT,
            keyword TEXT,
            link TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(link)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_link ON rss_articles(link)")
    conn.commit()
    conn.close()

def article_exists(link: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM rss_articles WHERE link = %s", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_articles() -> List[Tuple]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, keyword, link FROM rss_articles")
    articles = cursor.fetchall()
    conn.close()
    return articles

def update_article_keyword(article_id: int, keyword: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rss_articles SET keyword = %s WHERE id = %s", (keyword, article_id))
    conn.commit()
    conn.close()

def delete_old_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rss_articles WHERE keyword IS NOT NULL")
    conn.commit()
    conn.close()
