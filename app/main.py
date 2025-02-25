from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Define a function to run your startup tasks.
    def startup_tasks():
        print("Running startup tasks...")
        # Add any initialization logic here (e.g. connecting to services, scheduling tasks, etc.)
    
    # Attach the startup tasks to the app so we can call it later.
    app.startup_tasks = startup_tasks

    @app.route("/")
    def index():
        return "Hello, world!"

    return app
