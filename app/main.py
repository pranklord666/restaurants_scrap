from flask import Flask, jsonify
from .database import get_articles, init_db  # Use a relative import

def create_app():
    app = Flask(__name__)
    
    # Initialize the database (create the articles table) before the first request.
    @app.before_first_request
    def initialize():
        init_db()
    
    @app.route("/")
    def index():
        articles = get_articles()
        # Convert tuples to a list of dictionaries for JSON output.
        article_list = [
            {"id": row[0], "title": row[1], "summary": row[2], "keyword": row[3]}
            for row in articles
        ]
        return jsonify(article_list)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=10000)
    
