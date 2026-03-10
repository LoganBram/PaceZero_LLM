# Entry point — runs the full pipeline
# Usage: python main.py

from src.db import init_db
from src.enrich import enrich_contact
from src.score import compute_composite
from src.export import export_to_excel

if __name__ == "__main__":
    pass
