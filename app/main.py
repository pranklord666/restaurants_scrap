from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Instead of before_first_request, we use before_serving to reliably run startup tasks.
    @app.before_serving
    def startup_tasks():
        # Add any initialization logic here
        print("Running startup tasks...")

    # Define a sample route (adjust or add more routes as needed)
    @app.route("/")
    def index():
        return "Hello, world!"

    return app
