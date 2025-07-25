# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Obtém a URL do banco de dados da variável de ambiente DATABASE_URL
# Se não estiver definida (ex: desenvolvimento local), usa SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite3")

# Configurações do engine dependendo do tipo de banco de dados
# Para PostgreSQL no Render, SSL é frequentemente necessário
if DATABASE_URL.startswith("postgresql://"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else: # Para SQLite
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()