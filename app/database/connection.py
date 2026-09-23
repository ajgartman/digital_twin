from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import Config
# Setting up the connection to the PostgresSQL.

engine = create_engine(Config.PG_DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

