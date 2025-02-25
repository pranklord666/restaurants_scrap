from app.main import create_app

app = create_app()

# Manually run startup tasks once before starting the server.
if hasattr(app, "startup_tasks"):
    app.startup_tasks()

if __name__ == "__main__":
    app.run()
