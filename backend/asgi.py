"""ASGI entry point for production servers (e.g. `uvicorn asgi:app`)."""
from app.main import create_app

app = create_app()
