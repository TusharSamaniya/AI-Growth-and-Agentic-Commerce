# Creates the SQLite database file and all tables.
# Run from the project root:  python -m scripts.init_db

from backend.database import create_db_and_tables
from backend.models import Cart, Product  # importing registers the tables so they get created

create_db_and_tables()
print("Database ready: cartpilot.db")
