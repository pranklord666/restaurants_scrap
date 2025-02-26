from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__, static_folder='docs', static_url_path='/docs')
    
    # Load database URL from environment variable
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database and migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Enable CORS for all routes, allowing requests from GitHub Pages
    CORS(app, resources={r"/api/*": {"origins": "https://pranklord666.github.io"}})

    # Register blueprints with API prefix
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/api')

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
