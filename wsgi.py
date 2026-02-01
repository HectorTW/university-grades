"""
WSGI entrypoint for production servers (gunicorn / waitress).

Examples:
- Linux: gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app
- Windows: waitress-serve --host=0.0.0.0 --port=8000 wsgi:app
"""

from app import app

