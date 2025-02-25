import os
import psycopg2

def get_connection():
    # Use the provided DATABASE_URL or fallback to the given string.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://pranklord:qO1pVU1xCxvV4XKMT2jZgAh81KkLp4m5@dpg-cuuvnhdumphs73f3k6ug-a/restaurants_m0cf"
    )
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Create the articles table if it does not exist.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            summary TEXT,
            keyword VARCHAR(100)
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_articles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, keyword FROM articles")
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return articles
