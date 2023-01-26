import os
from sqlalchemy import create_engine, schema
from sqlalchemy.orm import sessionmaker, Session
from data_model import Base

UID = os.environ["POSTGRES_USER"]
PWD = os.environ["POSTGRES_PASSWORD"]
DBNAME = os.environ["POSTGRES_DB"]

connection_url = f"postgresql+psycopg2://{UID}:{PWD}@opencdms-database:5432/{DBNAME}"

engine = create_engine(connection_url)


Base.metadata.bind = engine


schemas = {v.schema for k, v in Base.metadata.tables.items()}

for _schema in schemas:
    if not engine.dialect.has_schema(engine, _schema):
        engine.execute(schema.CreateSchema(_schema))

Base.metadata.create_all(engine)

