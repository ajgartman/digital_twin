from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import Config
# Setting up the connection to the PostgreSQL.

engine = create_engine(Config.PG_DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

