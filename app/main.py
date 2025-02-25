from flask import Flask, jsonify
from database import get_articles, init_db

app = Flask(__name__)

# Run the initialization to create the table before handling any requests.
@app.before_first_request
def initialize():
    init_db()

@app.route("/")
def index():
    articles = get_articles()
    # Convert the list of tuples to a list of dictionaries for better JSON output.
    article_list = [
        {"id": row[0], "title": row[1], "summary": row[2], "keyword": row[3]}
        for row in articles
    ]
    return jsonify(article_list)

if __name__ == "__main__":
    # The host and port are set according to your current deployment.
    app.run(host="0.0.0.0", port=10000)
