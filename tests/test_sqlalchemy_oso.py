import os
import pytest
from sqlalchemy import create_engine, schema
from sqlalchemy.sql import text as sa_text
from sqlalchemy.orm import sessionmaker, close_all_sessions, Session
from data_model import Base, Observations, Users, Stations, StationsRole
from oso import Oso, exceptions
from sqlalchemy_oso import authorized_sessionmaker, register_models

UID = os.environ["POSTGRES_USER"]
PWD = os.environ["POSTGRES_PASSWORD"]
DBNAME = os.environ["POSTGRES_DB"]

connection_url = f"postgresql+psycopg2://{UID}:{PWD}@opencdms-database:5432/{DBNAME}"

db_engine = create_engine(connection_url)

oso = Oso()
register_models(oso,Base)
oso.load_files(["authorization.polar"])

# Station IDs
STATION = {
    "london": "1",
    "nigeria": "2"
}

LONDON_STAFF = {
    "admin": "33",
    "metadata": "34",
    "operator": "35",
    "rainfall": "36"
}

NIGERIA_STAFF = {
    "admin": "43",
    "metadata": "44",
    "operator": "45",
    "rainfall": "46"
}

TEST_LONDON_OBSERVATION_ID = "1"
TEST_NIGERIA_OBSERVATION_ID = "3"

@pytest.fixture
def db_session():
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

# Fixture to mock user authentication
@pytest.fixture
def authorized_user(request, db_session):
    user_id= request.param[0]
    user = db_session.query(Users).filter(Users.id == user_id).one()
    return user

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

    
    london_station = Stations(id=STATION["london"],name="London Station")
    # "admin", "metadata", "operator", "rainfall"
    london_admin_staff = Users(id=LONDON_STAFF["admin"],username="John Doe")
    london_metadata_staff = Users(id=LONDON_STAFF["metadata"], username="Mike Metadata")
    london_operator_staff = Users(id=LONDON_STAFF["operator"], username="Dan Operator")
    london_rainfall_staff = Users(id=LONDON_STAFF["rainfall"], username="Dave Rainfall")
    session.add_all([london_station, london_admin_staff, london_metadata_staff, london_operator_staff, london_rainfall_staff])

    nigeria_station = Stations(id=STATION["nigeria"], name="Nigerian Station")
    nigeria_admin_staff = Users(id=NIGERIA_STAFF["admin"], username="Emeka Adeola")
    nigeria_metadata_staff = Users(id=NIGERIA_STAFF["metadata"], username="Hassan Metadata")
    nigeria_operator_staff = Users(id=NIGERIA_STAFF["operator"], username="Edidong Operator")
    nigeria_rainfall_staff = Users(id=NIGERIA_STAFF["rainfall"], username="Ukamaka Rainfall")

    session.add_all([nigeria_station, nigeria_admin_staff, nigeria_metadata_staff, nigeria_operator_staff, nigeria_rainfall_staff])

    #  Assigns a given station role to a user
    def station_role(user: Users,station: Stations,role: str):
        station_role = StationsRole(user=user,station=station,name=role)
        session.add(station_role)
    
    # We do the actually role assignment
    station_role(london_admin_staff,london_station,"admin")
    station_role(london_operator_staff,london_station,"operator")
    station_role(london_metadata_staff,london_station,"metadata")
    station_role(london_rainfall_staff,london_station,"rainfall")

    station_role(nigeria_admin_staff,nigeria_station,"admin")
    station_role(nigeria_operator_staff,nigeria_station,"operator")
    station_role(nigeria_metadata_staff,nigeria_station,"metadata")
    station_role(nigeria_rainfall_staff,nigeria_station,"rainfall")

    session.commit()
    session.flush()

    #  Create Observations from stations
    london_obs1 = Observations(id="1",comments="First observation from London", station=london_station.id)
    london_obs2 = Observations(id="2",comments="Second observation from London", station=london_station.id)

    nigeria_obs1 = Observations(id="3",comments="First observation from Nigeria", station=nigeria_station.id)
    nigeria_obs2 = Observations(id="4",comments="Second observation from Nigeria", station=nigeria_station.id)

    session.add_all([london_obs1, london_obs2, nigeria_obs1, nigeria_obs2])
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


# Mock controller method to test
#  The station_id is expected to come as a path variable
def list_observation(user: Users, station_id: str, session: Session):
    station = session.query(Stations).filter(Stations.id == station_id).one_or_none()
    oso.authorize(user, "list_observation", station)
    observations = session.query(Observations).filter(Observations.station == station_id).all()
    return observations

def create_observation(user: Users, station_id: str, session: Session):
    station = session.query(Stations).filter(Stations.id == station_id).one_or_none()
    oso.authorize(user, "create_observation", station)
    obs = Observations(id="239",comment=f"Observation from {station.name}", station=station_id)
    session.add(obs)
    session.commit()


def delete_observation(user, station_id: str, observation_id: str, session: Session):
    obs = session.query(Observations).filter(Observations.id == observation_id).one_or_none()
    if obs is None:
        return False
    else:
        oso.authorize(user,"delete_observation",obs)
        session.delete(obs)
        session.commit()
    return True
    
def update_observation(user, station_id: str, observation_id: str, session: Session):
    obs = session.query(Observations).filter(Observations.id == observation_id).one_or_none()
    if obs is None:
        raise Exception("Observation not found")
    else:
        oso.authorize(user,"delete_observation",obs)
        session.delete(obs)
        session.commit()

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_can_list_observation_in_own_station(authorized_user, db_session):
    observations = list_observation(authorized_user,STATION["london"],db_session)
    assert len(observations) == 2

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["rainfall"],)],indirect=True)
def test_rainfall_staff_cannot_list_observation_in_own_station(authorized_user, db_session):
    with pytest.raises(exceptions.NotFoundError):
        list_observation(authorized_user,STATION["london"],db_session)
   

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_staff_cannot_list_observation_in_another_station(authorized_user, db_session):
    with pytest.raises(exceptions.NotFoundError):
        list_observation(authorized_user,STATION["nigeria"],db_session)

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_staff_cannot_list_observation_in_another_station(authorized_user, db_session):
    with pytest.raises(exceptions.NotFoundError):
        list_observation(authorized_user,STATION["nigeria"],db_session)

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["operator"],)],indirect=True)
def test_operator_cannot_delete_observation_in_own_station(authorized_user, db_session):
    with pytest.raises(exceptions.AuthorizationError):
        delete_observation(authorized_user,STATION["london"],TEST_LONDON_OBSERVATION_ID, db_session)
    

@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_can_delete_observation_in_own_station(authorized_user, db_session):
    res = delete_observation(authorized_user,STATION["london"],TEST_LONDON_OBSERVATION_ID, db_session)
    assert res is True
    
@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_cannot_delete_observation_in_another_station(authorized_user, db_session):
    with pytest.raises(exceptions.AuthorizationError):
        delete_observation(authorized_user,STATION["london"], TEST_NIGERIA_OBSERVATION_ID, db_session)

