from flask import Blueprint, jsonify, request
from . import db
from .models import Article

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return "Hello, world!"

@main.route("/articles", methods=["GET"])
def get_articles():
    articles = Article.query.all()
    return jsonify([{"id": a.id, "title": a.title, "summary": a.summary, "keyword": a.keyword} for a in articles])

@main.route("/update-selection", methods=["POST"])
def update_selection():
    selections = request.get_json()
    for article_id, status in selections.items():
        article = Article.query.get(article_id)
        if article and status == "in":
            # Handle selected articles (e.g., mark as kept)
            pass  # Add logic if needed
    db.session.commit()
    return jsonify({"message": "Selection saved"})
