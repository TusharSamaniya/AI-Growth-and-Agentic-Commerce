from sqlmodel import SQLModel, create_engine

# SQLite keeps the whole database in one local file: cartpilot.db
sqlite_url = "sqlite:///cartpilot.db"

# The engine is our connection to that file. echo=True prints the SQL it runs
# (great for learning — we can turn it off later).
engine = create_engine(sqlite_url, echo=True)


# Creates the database file and every table we've defined as a SQLModel.
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
