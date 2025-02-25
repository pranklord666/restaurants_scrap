from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
