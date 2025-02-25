from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app.database import get_articles, update_article_keyword, delete_old_articles

main = Blueprint("main", __name__)

@main.route("/")
def index():
    articles = get_articles()
    return render_template("index.html", articles=articles)

@main.route("/update_keyword", methods=["POST"])
def update_keyword():
    data = request.get_json()
    article_id = data.get("id")
    keyword = data.get("keyword")

    if article_id and keyword:
        update_article_keyword(article_id, keyword)
        return jsonify({"message": "Article updated successfully"}), 200

    return jsonify({"error": "Invalid request"}), 400

@main.route("/delete_old", methods=["POST"])
def delete_old():
    delete_old_articles()
    return jsonify({"message": "Old articles deleted"}), 200
