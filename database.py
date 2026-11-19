"""
Compatibility wrapper for database module
Redirects to database.connection
"""
from database.connection import Base, engine, SessionLocal, get_db, init_db, drop_all_tables
