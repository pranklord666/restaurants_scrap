from flask import Blueprint, render_template, request, redirect, url_for
from .scraper import process_feeds
from .database import get_articles, update_article_keyword, delete_old_articles

main = Blueprint('main', __name__)

@main.route('/')
def index():
    articles = get_articles()
    return render_template('index.html', articles=articles)

@main.route('/update_keyword', methods=['POST'])
def update_keyword():
    article_id = request.form['article_id']
    keyword = request.form['keyword']
    update_article_keyword(article_id, keyword)
    return redirect(url_for('main.index'))

@main.route('/delete_old_articles')
def delete_old():
    delete_old_articles()
    return redirect(url_for('main.index'))
