import os
import pytest
from sqlalchemy import create_engine, schema
from sqlalchemy.sql import text as sa_text
from sqlalchemy.orm import sessionmaker, close_all_sessions
from data_model import Base, Observations, Users, Stations
from oso import Oso
from sqlalchemy_oso import authorized_sessionmaker, register_models

UID = os.environ["POSTGRES_USER"]
PWD = os.environ["POSTGRES_PASSWORD"]
DBNAME = os.environ["POSTGRES_DB"]

connection_url = f"postgresql+psycopg2://{UID}:{PWD}@opencdms-database:5432/{DBNAME}"

db_engine = create_engine(connection_url)

oso = Oso()
register_models(oso,Base)
oso.load_files(["policy.polar"])


@pytest.fixture
def authorized_session(request):
    action = request.param[0]
    user_id = request.param[1]
    def get_authenticated_user(user_id: str):
        Session = sessionmaker(bind=db_engine)
        session = Session()
        user = session.query(Users).filter(Users.id == user_id).one()
        return user

    AuthorizedSession = authorized_sessionmaker(bind=db_engine,
                                                get_oso=lambda: oso,
                                                get_user=lambda: get_authenticated_user(user_id),
                                                get_checked_permissions=lambda: { Observations: action })
    auth_session = AuthorizedSession()
    
    yield auth_session
    auth_session.close()


def setup_module(module):
    # Create tables
    Base.metadata.bind = db_engine

    schemas = {v.schema for k, v in Base.metadata.tables.items()}

    for _schema in schemas:
        if not db_engine.dialect.has_schema(db_engine, _schema):
            db_engine.execute(schema.CreateSchema(_schema))

    Base.metadata.create_all(db_engine)

    Session = sessionmaker(bind=db_engine)
    session = Session()

    station1 = Stations(id="1",name="Station 1")
    station2 = Stations(id="2", name="Station 2")
    user1 = Users(id="1",username="John Doe")
    user2 = Users(id="2", username="Emeka Adeola")


    # User 1 is registered only to station 1
    user1.stations.append(station1)
    # User 2 is registered to both station 1 and 2
    user2.stations.append(station2)
    user2.stations.append(station1)
  
    session.add_all([user1,user2])
    session.commit()
    # Each station has two observations
    obs1 = Observations(id="1",comments="First observation from station 1", station=station1.id)
    obs2 = Observations(id="2",comments="Second observation from station 1", station=station1.id)

    obs3 = Observations(id="3",comments="First observation from station 2", station=station2.id)
    obs4 = Observations(id="4",comments="Second observation from station 2", station=station2.id)
    session.add_all([obs1,obs2, obs3, obs4])
    session.commit()
    session.close()


def teardown_module(module):
    # Postgresql does not automatically reset ID if a table is truncated like mysql does
    # Closing all active sessions on the DB
    close_all_sessions()
    with db_engine.connect() as connection:
        with connection.begin():
            db_engine.execute(sa_text(f'''TRUNCATE TABLE cdm.{Observations.__tablename__} RESTART IDENTITY CASCADE''').execution_options(autocommit=True))
            db_engine.execute(sa_text(f'''TRUNCATE TABLE cdm.{Stations.__tablename__} RESTART IDENTITY CASCADE''').execution_options(autocommit=True))
            db_engine.execute(sa_text(f'''TRUNCATE TABLE cdm.{Users.__tablename__} RESTART IDENTITY CASCADE''').execution_options(autocommit=True))
    db_engine.dispose()


@pytest.mark.parametrize("authorized_session", [("read", "1")],indirect=True)
def test_that_user_1_can_see_only_observations_in_station_1(authorized_session):
    observations = authorized_session.query(Observations).all()
    assert len(observations) == 2
    for observation in observations:
        assert "station 1" in  observation.comments
    

@pytest.mark.parametrize("authorized_session", [("read", "2")], indirect=True)
def test_that_user_2_can_see_observations_in_station_1_and_station_2(authorized_session):
    observations = authorized_session.query(Observations).all()
    assert len(observations) == 4


@pytest.mark.parametrize("authorized_session",[("write","1")], indirect=True)
def test_user_1_can_edit_observations_from_station_1(authorized_session):
    observations = authorized_session.query(Observations).all()
    assert len(observations) == 2
    for observation in observations:
        observation.comments = "User 1 Changed this comment"
        authorized_session.add(observation)
        authorized_session.commit()
    
    observations = authorized_session.query(Observations).all()
    assert len(observations) == 2
    for observation in observations:
        assert "User 1 Changed this comment" in  observation.comments


@pytest.mark.parametrize("authorized_session",[("write","2")], indirect=True)
def test_user_2_can_edit_observations_from_station_1_and_station_2(authorized_session):
    observations = authorized_session.query(Observations).all()
    assert len(observations) == 4
    for observation in observations:
        observation.comments = "User 2 Changed this comment"
        authorized_session.add(observation)
        authorized_session.commit()
    
    observations = authorized_session.query(Observations).all()
    for observation in observations:
        assert "User 2 Changed this comment" in  observation.comments
    

    
