from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_folder='docs', static_url_path='/docs')
    
    # Load database URL from environment variable
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database
    db.init_app(app)

    # Enable CORS for all routes, allowing requests from GitHub Pages
    CORS(app, resources={r"/*": {"origins": "https://pranklord666.github.io"}})

    # Register blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/api')  # Optional: Add API prefix

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
