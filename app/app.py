from flask import Flask
from app.main import main as main_blueprint
import os

def create_app():
    app = Flask(__name__)
    
    # Load database URL from environment variables
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")

    # Register blueprints
    app.register_blueprint(main_blueprint)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=10000)
