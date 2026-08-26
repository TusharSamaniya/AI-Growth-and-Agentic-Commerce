from sqlmodel import SQLModel, create_engine

from backend.config import settings

# Our connection to PostgreSQL. The URL comes from settings (DATABASE_URL in .env),
# so it's never hardcoded here. echo=True prints the SQL it runs (handy for learning).
engine = create_engine(settings.database_url, echo=True)


# Creates every table we've defined as a SQLModel in the connected database.
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
