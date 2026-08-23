# Creates the SQLite database file and all tables.
# Run from the project root:  python -m scripts.init_db

from backend.database import create_db_and_tables

create_db_and_tables()
print("Database ready: cartpilot.db")
