from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = 'postgresql://postgres.oqlrprxthyllastssesc:finalexambackend@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres'

db_url = SQLALCHEMY_DATABASE_URL
try:
    import psycopg
except ImportError:
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(db_url)

sessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()
