from flask import Blueprint, jsonify, request
from . import db
from .models import Article
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

main = Blueprint("main", __name__)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,)))
@main.route("/articles", methods=["GET"])
def get_articles():
    articles = Article.query.all()
    return jsonify([{"id": a.id, "title": a.title, "summary": a.summary, "keyword": a.keyword} for a in articles])

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,)))
@main.route("/update-selection", methods=["POST"])
def update_selection():
    selections = request.get_json()
    for article_id, status in selections.items():
        article = Article.query.get(article_id)
        if article:
            article.status = "in" if status == "in" else "out"
    db.session.commit()
    return jsonify({"message": "Selection saved"})

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((sqlalchemy.exc.OperationalError,)))
@main.route("/results", methods=["GET"])
def get_results():
    articles = Article.query.filter_by(status="in").all()
    return jsonify([{"title": a.title, "summary": a.summary} for a in articles])
