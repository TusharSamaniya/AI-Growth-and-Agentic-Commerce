from sqlmodel import SQLModel, create_engine

from backend.config import settings

# Our connection to PostgreSQL. The URL comes from settings (DATABASE_URL in .env),
# so it's never hardcoded here. pool_pre_ping tests that a pooled connection is
# still alive before handing it out — essential for Neon, whose free tier drops
# idle connections (without this, the first query after an idle gap crashes with
# "server closed the connection unexpectedly"). echo=False keeps the console clean.
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)


# Creates every table we've defined as a SQLModel in the connected database.
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
