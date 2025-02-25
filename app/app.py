from flask import Flask
from .main import main

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=10000)
