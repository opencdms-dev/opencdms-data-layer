from sqlalchemy import create_engine, schema
from sqlalchemy.orm import Session
from oso import Oso
import os
from data_model import *
from sqlalchemy.orm import sessionmaker, Session, close_all_sessions


# oso = Oso()
# register_models(oso,Base)
# oso.load_files(["policy.polar"])

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



def get_authenticated_user(user_id: str):
    SessionLocal = sessionmaker(autocommit=False,class_=Session, autoflush=False, bind=engine)
    session = SessionLocal()
    user = session.query(Users).filter(Users.id == user_id).one()
    return user



