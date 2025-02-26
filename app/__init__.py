from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import os
from urllib.parse import urlparse, parse_qs

db = SQLAlchemy()
migrate = Migrate()

def create_app(environ=None, start_response=None):
    app = Flask(__name__, static_folder='docs', static_url_path='/docs')
    
    # Load and modify DATABASE_URL to ensure SSL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        parsed_url = urlparse(db_url)
        if not parse_qs(parsed_url.query).get('sslmode'):
            db_url += "?sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///default.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database and migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Enable CORS for all routes, allowing requests from GitHub Pages with specific methods and headers
    CORS(app, resources={r"/api/*": {
        "origins": ["https://pranklord666.github.io", "https://pranklord666.github.io/restaurants_scrap"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }})

    # Register blueprints with API prefix
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/api')

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
