"""Start NeuraBrowse:  python run.py   ->  http://127.0.0.1:5000"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from app import create_app  # noqa: E402

if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=bool(os.environ.get("FLASK_DEBUG")))
