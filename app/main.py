from flask import Blueprint, render_template, jsonify, request
from .database import get_articles, update_article_keyword, delete_old_articles

main = Blueprint('main', __name__)

@main.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)

@main.route("/articles")
def fetch_articles():
    articles = get_articles()
    return jsonify(articles)

@main.route("/update-selection", methods=["POST"])
def update_selection():
    data = request.json
    for article_id, keyword in data.items():
        update_article_keyword(article_id, keyword)
    return jsonify({"message": "Selection updated!"})

@main.route("/delete-old", methods=["POST"])
def delete_old():
    delete_old_articles()
    return jsonify({"message": "Old articles deleted!"})
