# Creates the SQLite database file and all tables.
# Run from the project root:  python -m scripts.init_db

from backend.database import create_db_and_tables
from backend.models import Product  # importing registers the table so it gets created

create_db_and_tables()
print("Database ready: cartpilot.db")
