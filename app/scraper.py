import asyncio
import aiosqlite
import feedparser
from playwright.async_api import async_playwright
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from typing import Dict
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# RSS Feeds
RSS_FEEDS = [
    "https://www.google.com/alerts/feeds/10761550076048473387/17917991328404962919",
    "https://www.google.com/alerts/feeds/10761550076048473387/596446234793271456",
    "https://www.google.com/alerts/feeds/10761550076048473387/16339924130653215114",
    "https://www.google.com/alerts/feeds/10761550076048473387/15297762454452931038"
]

# Configuration
CONFIG = {
    'max_concurrent_scrapes': 2,
    'max_retries': 2,
    'retry_delay': 2,
    'db_timeout': 60,
    'page_load_timeout': 20000,
    'wait_after_navigation': 1000,
    'stealth_mode': True
}

class ArticleScraper:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.browser = None
        self.context = None

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            bypass_csp=True,
            java_script_enabled=True,
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
        )

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
            response = await page.goto(
                url,
                timeout=CONFIG['page_load_timeout'],
                wait_until='domcontentloaded'
            )

            if response.status == 200:
                content = await self._extract_content_with_fallbacks(page)

                if not content.strip():
                    await page.wait_for_timeout(2000)
                    content = await self._extract_content_with_fallbacks(page)

            if not content.strip() or "subscribe" in content.lower() or "cookie" in content.lower():
                content = await self._handle_restricted_content(page)

        except Exception as e:
            logger.error(f"Error fetching article {url}: {str(e)}")
            content = await self._fallback_content_extraction(page)

        finally:
            await page.close()

        return content.strip()

    async def _extract_content_with_fallbacks(self, page) -> str:
        content = ""
        selectors = [
            'article',
            'main',
            '.article-content',
            '.content',
            '#article-content',
            '.article-body',
            '.post-content'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.text_content()
                    if content.strip():
                        break
            except:
                continue

        if not content.strip():
            content = await page.evaluate('''() => {
                const elementsToRemove = document.querySelectorAll(
                    'header, footer, nav, aside, .ads, .advertisement, .social-share'
                );
                elementsToRemove.forEach(el => el.remove());

                const article = document.querySelector('article');
                if (article) return article.innerText;

                const main = document.querySelector('main');
                if (main) return main.innerText;

                const paragraphs = Array.from(document.getElementsByTagName('p'));
                return paragraphs.map(p => p.innerText).join('\\n');
            }''')

        return content

    async def _handle_restricted_content(self, page) -> str:
        try:
            cookie_buttons = [
                'button:has-text("Accept")',
                'button:has-text("Accepter")',
                'button:has-text("I agree")',
                '.cookie-button',
                '#cookie-accept'
            ]

            for button in cookie_buttons:
                try:
                    await page.click(button, timeout=2000)
                    await page.wait_for_timeout(1000)
                except:
                    continue

            return await self._extract_content_with_fallbacks(page)

        except Exception as e:
            logger.error(f"Error handling restricted content: {str(e)}")
            return ""

    async def _fallback_content_extraction(self, page) -> str:
        try:
            content = await page.evaluate('''() => {
                const paragraphs = document.getElementsByTagName('p');
                return Array.from(paragraphs)
                    .map(p => p.innerText)
                    .filter(text => text.length > 100)
                    .join('\\n');
            }''')
            return content
        except:
            return ""

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
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return datetime.now().strftime("%Y-%m-%d")

async def process_feed(feed_url: str, scraper: ArticleScraper, db_manager):
    feed = feedparser.parse(feed_url)
    tasks = []

    for entry in feed.entries:
        link = scraper.extract_real_link(entry.link)
        if not await db_manager.article_exists(link):
            tasks.append(process_entry(scraper, entry, db_manager))

    chunk_size = CONFIG['max_concurrent_scrapes']
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        await asyncio.gather(*chunk)
        await asyncio.sleep(1)

async def process_entry(scraper: ArticleScraper, entry: Dict, db_manager):
    try:
        title = entry.title
        date = scraper.convert_date(entry.get('published', datetime.now().isoformat()))
        link = scraper.extract_real_link(entry.link)

        content = await scraper.fetch_article_content(link)
        if not content:
            logger.warning(f"No content retrieved for {link}")
            return

        async with aiosqlite.connect(db_manager.db_name) as conn:
            await conn.execute("""
                INSERT OR IGNORE INTO rss_articles (date, title, raw_content, summary, keyword, link)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, title, content, "", "", link))
            await conn.commit()

        logger.info(f"Successfully processed: {title}")

    except Exception as e:
        logger.error(f"Error processing entry: {str(e)}")

async def process_feeds(db_manager):
    scraper = ArticleScraper(db_manager)
    await scraper.init_browser()

    try:
        for feed_url in RSS_FEEDS:
            logger.info(f"Processing feed: {feed_url}")
            await process_feed(feed_url, scraper, db_manager)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning("Operation cancelled. Cleaning up...")

    finally:
        await scraper.close_browser()
        logger.info("Scraping completed.")
