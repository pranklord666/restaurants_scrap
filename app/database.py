import aiosqlite
import sqlite3
from typing import List, Tuple

class DatabaseManager:
    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rss_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            await db.execute("CREATE INDEX IF NOT EXISTS idx_link ON rss_articles(link)")
            await db.commit()

    async def article_exists(self, link: str) -> bool:
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT 1 FROM rss_articles WHERE link = ?", (link,))
            result = await cursor.fetchone()
            return result is not None

def get_articles() -> List[Tuple]:
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, keyword, link FROM rss_articles")
    articles = cursor.fetchall()
    conn.close()
    return articles

def update_article_keyword(article_id: int, keyword: str):
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE rss_articles SET keyword = ? WHERE id = ?", (keyword, article_id))
    conn.commit()
    conn.close()

def delete_old_articles():
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rss_articles WHERE keyword IS NOT NULL")
    conn.commit()
    conn.close()
