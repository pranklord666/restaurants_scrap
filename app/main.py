from flask import Blueprint, jsonify, request
from . import db
from .models import Article
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random, retry_if_exception_type
import sqlalchemy
import random
import asyncio
import httpx
import os

main = Blueprint("main", __name__)

# Configure Mistral API (use environment variable for API key)
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY environment variable not set")

def truncate_text(text, max_tokens):
    words = text.split()
    truncated_text = []
    current_length = 0
    for word in words:
        current_length += len(word) + 1
        if current_length > 16000:  # Match your Mistral prompt limit
            break
        truncated_text.append(word)
    return ' '.join(truncated_text)

async def generate_summary(raw_content, retry=3):
    max_tokens = 16000
    truncated_content = truncate_text(raw_content, max_tokens)
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
            return summary

    except httpx.ReadTimeout as e:
        print(f"Timeout error generating summary: {e}")
        if retry > 0:
            print("Retrying summary generation...")
            await asyncio.sleep(2)  # Wait before retry
            return await generate_summary(raw_content, retry=retry-1)
        return "Résumé non généré en raison d'une erreur de timeout."

    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Résumé non généré en raison d'une erreur inattendue."

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
    selections = request.get_json()
    for article_id, status in selections.items():
        article = Article.query.get(article_id)
        if article:
            article.status = "in" if status == "in" else "out"
    db.session.commit()
    return jsonify({"message": "Selection saved"})

@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=2, max=60) + wait_random(0, 1),
    retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,))
)
@main.route("/results", methods=["GET"])
async def get_results():
    # First, get articles with status "in"
    articles = Article.query.filter_by(status="in").all()
    
    # Generate summaries for all "in" articles using Mistral
    tasks = []
    for article in articles:
        if not article.summary or article.summary.startswith("Résumé non généré"):
            tasks.append(generate_summary(article.raw_content))
        else:
            tasks.append(asyncio.Future())  # Use existing summary if available
            tasks[-1].set_result(article.summary)

    summaries = await asyncio.gather(*tasks)

    # Update articles with new summaries
    for article, summary in zip(articles, summaries):
        if not article.summary or article.summary.startswith("Résumé non généré"):
            article.summary = summary
    db.session.commit()

    return jsonify([{"title": a.title, "summary": a.summary} for a in articles])

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
