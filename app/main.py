from flask import Blueprint, jsonify, request
from . import db
from .models import Article
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random, retry_if_exception_type
import sqlalchemy
import random
import asyncio
import httpx
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint("main", __name__)

# Configure Mistral API (use environment variable for API key)
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY environment variable not set")

def truncate_text(text, max_tokens):
    if not text or not isinstance(text, str):
        return ""
    words = text.split()
    truncated_text = []
    current_length = 0
    for word in words:
        current_length += len(word) + 1
        if current_length > max_tokens:  # Match your Mistral prompt limit
            break
        truncated_text.append(word)
    return ' '.join(truncated_text)

async def generate_summary(raw_content, retry=3):
    max_tokens = 16000
    truncated_content = truncate_text(raw_content, max_tokens)
    if not truncated_content.strip():
        logger.warning("Empty or invalid raw_content provided for summary generation")
        return "No summary available due to empty content"

    prompt = (
        "Tu es un auteur inspiré, doté d'une plume unique et captivante. Je vais te fournir un texte, "
        "et ta mission est de le condenser en un résumé autonome, qui ne fait aucune référence à un article, à une source ou à un contexte extérieur. "
        "Voici tes consignes :\n\n"
        "1. Imagine que c'est toi qui as eu les idées et écrit ce résumé de manière originale.\n"
        "2. Écris de manière concise (90 mots maximum) avec un ton décalé, engageant et vivant.\n"
        "3. Utilise des images fortes, des métaphores surprenantes, et un style fluide qui capte immédiatement l'attention.\n"
        "4. N'introduis pas le résumé avec des phrases comme 'Dans cet article' ou 'Il s'agit de'. "
        "Plonge directement dans le vif du sujet comme si tu présentais une réflexion ou une idée qui t'appartient.\n"
        "5. Évite toute redondance et fais ressortir l'essentiel de manière mémorable.\n\n"
        f"Texte à résumer : {truncated_content}\n\n"
        "Rends ce résumé percutant, créatif, et impossible à ignorer."
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {api_key}"
                },
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=httpx.Timeout(60.0)
            )
            response.raise_for_status()
            response_data = response.json()
            summary = response_data['choices'][0]['message']['content'].strip()
            logger.info(f"Generated summary: {summary[:50]}...")  # Log first 50 chars of summary
            return summary if summary and summary.strip() else "No summary available from Mistral"

    except httpx.ReadTimeout as e:
        logger.error(f"Timeout error generating summary: {e}")
        if retry > 0:
            logger.info("Retrying summary generation...")
            await asyncio.sleep(2)  # Wait before retry
            return await generate_summary(raw_content, retry=retry-1)
        return "No summary available due to timeout error"

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return "No summary available due to an unexpected error"

@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=2, max=60) + wait_random(0, 1),
    retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,))
)
@main.route("/articles", methods=["GET"])
def get_articles():
    articles = Article.query.all()
    return jsonify([{"id": a.id, "title": a.title, "summary": a.summary, "keyword": a.keyword} for a in articles])

@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=2, max=60) + wait_random(0, 1),
    retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,))
)
@main.route("/update-selection", methods=["POST"])
def update_selection():
    try:
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
        
        selections = request.get_json()
        if not isinstance(selections, dict):
            logger.error("Selections must be a dictionary")
            return jsonify({"error": "Invalid data format"}), 400

        for article_id, status in selections.items():
            try:
                article_id = int(article_id)  # Ensure article_id is an integer
                article = Article.query.get(article_id)
                if article:
                    article.status = "in" if status == "in" else "out"
                else:
                    logger.warning(f"Article with ID {article_id} not found")
            except ValueError:
                logger.error(f"Invalid article ID: {article_id}")
                return jsonify({"error": f"Invalid article ID: {article_id}"}), 400

        db.session.commit()
        logger.info("Selection saved successfully")
        return jsonify({"message": "Selection saved"})

    except Exception as e:
        logger.error(f"Error processing update-selection: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=2, max=60) + wait_random(0, 1),
    retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,))
)
@main.route("/results", methods=["GET"])
async def get_results():
    # First, get articles with status "in"
    articles = Article.query.filter_by(status="in").all()
    logger.info(f"Found {len(articles)} articles with status 'in'")
    
    # Generate summaries for all "in" articles using Mistral, forcing updates if raw_content exists
    tasks = []
    for article in articles:
        logger.debug(f"Processing article: {article.title}")
        if article.raw_content and article.raw_content.strip():
            tasks.append(generate_summary(article.raw_content))
        else:
            tasks.append(asyncio.Future())
            tasks[-1].set_result(article.summary or "No raw content available for summary")

    summaries = await asyncio.gather(*tasks)

    # Update articles with new summaries and log each update
    updated_count = 0
    for article, summary in zip(articles, summaries):
        if article.raw_content and article.raw_content.strip():
            article.summary = summary if summary and summary.strip() else "No summary available"
            updated_count += 1
            logger.info(f"Updated summary for article '{article.title}': {summary[:50]}...")
        else:
            logger.warning(f"No raw_content for article '{article.title}', kept summary: {article.summary or 'None'}")
    db.session.commit()
    logger.info(f"Updated {updated_count} article summaries")

    # Return results, ensuring summaries are included even if empty or default
    results = [{"title": a.title, "summary": a.summary or "No summary available"} for a in articles]
    logger.debug(f"Returning results: {results}")
    return jsonify(results)

# Ensure async compatibility for WSGI (Gunicorn handles this on Render)
from werkzeug.middleware.dispatcher import DispatcherMiddleware  # Updated import
from werkzeug.serving import run_simple

if __name__ == "__main__":
    # For testing locally with async
    from gevent.pywsgi import WSGIServer
    import gevent

    app = create_app()
    http_server = WSGIServer(('0.0.0.0', 10000), app)
    http_server.serve_forever()
