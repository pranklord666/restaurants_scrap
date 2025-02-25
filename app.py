import os
import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import nest_asyncio
nest_asyncio.apply()

# === Modified Scraping and Summarization Code ===

import feedparser
from playwright.async_api import async_playwright
import logging
import time
import httpx
from urllib.parse import urlparse, parse_qs

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# RSS Feeds list
RSS_FEEDS = [
    "https://www.google.com/alerts/feeds/10761550076048473387/17917991328404962919",
    "https://www.google.com/alerts/feeds/10761550076048473387/596446234793271456",
    "https://www.google.com/alerts/feeds/10761550076048473387/16339924130653215114",
    "https://www.google.com/alerts/feeds/10761550076048473387/15297762454452931038"
]

# Basic configuration options
CONFIG = {
    'max_concurrent_scrapes': 2,
    'page_load_timeout': 20000
}

# --- Database and Scraper Classes ---

class DatabaseManager:
    def __init__(self, db_name: str):
        self.db_name = db_name

    async def init_db(self):
        import aiosqlite
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_link ON rss_articles(link)")
            await db.commit()

    async def article_exists(self, link: str) -> bool:
        import aiosqlite
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute("SELECT 1 FROM rss_articles WHERE link = ?", (link,))
            result = await cursor.fetchone()
            return result is not None

class ArticleScraper:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.browser = None
        self.context = None

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ])
        self.context = await self.browser.new_context()

    async def close_browser(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def fetch_article_content(self, url: str) -> str:
        page = await self.context.new_page()
        content = ""
        try:
            response = await page.goto(url, timeout=CONFIG['page_load_timeout'], wait_until='domcontentloaded')
            if response and response.status == 200:
                content = await page.content()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        finally:
            await page.close()
        return content

    @staticmethod
    def extract_real_link(google_url: str) -> str:
        try:
            parsed_url = urlparse(google_url)
            real_url = parse_qs(parsed_url.query).get('url', [None])[0]
            return real_url if real_url else google_url
        except Exception as e:
            logger.error(f"Error extracting real link: {e}")
            return google_url

    @staticmethod
    def convert_date(date_str: str) -> str:
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")

async def process_feed(feed_url: str, scraper: ArticleScraper, db_manager: DatabaseManager):
    feed = feedparser.parse(feed_url)
    tasks = []
    for entry in feed.entries:
        link = scraper.extract_real_link(entry.link)
        if not await db_manager.article_exists(link):
            tasks.append(process_entry(scraper, entry, db_manager))
    # Run tasks concurrently in chunks
    chunk_size = CONFIG['max_concurrent_scrapes']
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i+chunk_size]
        await asyncio.gather(*chunk)
        await asyncio.sleep(1)

async def process_entry(scraper: ArticleScraper, entry, db_manager: DatabaseManager):
    import aiosqlite
    try:
        title = entry.title
        date = scraper.convert_date(entry.get('published', datetime.now().isoformat()))
        link = scraper.extract_real_link(entry.link)
        content = await scraper.fetch_article_content(link)
        if not content:
            return
        async with aiosqlite.connect(db_manager.db_name) as conn:
            await conn.execute("""
                INSERT OR IGNORE INTO rss_articles (date, title, raw_content, summary, keyword, link)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, title, content, "", "", link))
            await conn.commit()
        logger.info(f"Processed: {title}")
    except Exception as e:
        logger.error(f"Error processing entry: {e}")

async def main_scraping(db_name):
    db_manager = DatabaseManager(db_name)
    await db_manager.init_db()
    scraper = ArticleScraper(db_manager)
    await scraper.init_browser()
    try:
        for feed_url in RSS_FEEDS:
            logger.info(f"Processing feed: {feed_url}")
            await process_feed(feed_url, scraper, db_manager)
    except Exception as e:
        logger.error(e)
    finally:
        await scraper.close_browser()

# --- Summarization Functions ---

api_key = "YOUR_MISTRAL_API_KEY"  # Replace with your API key

def truncate_text(text, max_tokens):
    words = text.split()
    truncated = []
    count = 0
    for word in words:
        count += len(word) + 1
        if count > max_tokens:
            break
        truncated.append(word)
    return ' '.join(truncated)

def generate_summary(raw_content, retry=1):
    max_tokens = 16000
    truncated_content = truncate_text(raw_content, max_tokens)
    prompt = (
        "Tu es un auteur inspiré, rédige un résumé concis (90 mots max) sans introduction. "
        "Voici le texte : " + truncated_content
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = httpx.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=60.0)
        response.raise_for_status()
        summary = response.json()['choices'][0]['message']['content'].strip()
        return summary
    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        return "Résumé non généré."

def generate_summaries_for_in_articles(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT id, raw_content FROM rss_articles WHERE LOWER(keyword) = 'in'")
    rows = cursor.fetchall()
    for row in rows:
        article_id, raw_content = row
        summary = generate_summary(raw_content)
        cursor.execute("UPDATE rss_articles SET summary = ? WHERE id = ?", (summary, article_id))
        conn.commit()
    cursor.close()
    conn.close()

# === End of Scraping & Summarization Code ===

# --- Flask App Setup ---

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DB_NAME = "articles.db"

# Global flag to track scraping status
scraping_done = False

@app.route("/")
def index():
    return render_template("index.html", scraping_done=scraping_done)

def run_scraping_background():
    global scraping_done
    asyncio.run(main_scraping(DB_NAME))
    scraping_done = True

@app.route("/start-scraping", methods=["POST"])
def start_scraping():
    global scraping_done
    scraping_done = False
    threading.Thread(target=run_scraping_background).start()
    return redirect(url_for("loading"))

@app.route("/loading")
def loading():
    # A simple page that refreshes until scraping is done
    if scraping_done:
        return redirect(url_for("selection"))
    return render_template("loading.html")

@app.route("/selection", methods=["GET", "POST"])
def selection():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == "POST":
        # Process selection form: update each article's "keyword" based on user choice
        selections = request.form
        for key in selections:
            if key.startswith("article_"):
                article_id = key.split("_")[1]
                keyword = selections.get(key)
                cursor.execute("UPDATE rss_articles SET keyword = ? WHERE id = ?", (keyword, article_id))
        conn.commit()
        cursor.close()
        conn.close()
        # Generate summaries for articles marked "in"
        generate_summaries_for_in_articles(DB_NAME)
        return redirect(url_for("results"))
    else:
        cursor.execute("SELECT id, title, keyword FROM rss_articles")
        articles = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("selection.html", articles=articles)

@app.route("/results")
def results():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title, summary, link FROM rss_articles WHERE LOWER(keyword) = 'in'")
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("results.html", articles=articles)

if __name__ == "__main__":
    app.run(debug=True)
