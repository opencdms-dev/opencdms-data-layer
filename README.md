# opencdms-data-layer


## Steps

1. Run `docker-compose up -d`.
2. `docker-compose run db-builder`
3. `python build_db.py`


# ERD Diagram

[ERD Diagram](assets/opencdms_erd.png "ERD diagram")

## RBAC using Sqlachemy-oso

Sqlachemy-oso library provides a RBAC on Sqlachemy models. 
Using Sqlachemy-oso's authorized_sesssion object, we can limit database records that a user can access without explicitly applying filters or "WHERE" clauses.

Sqlalchemy-oso, internally, applies filters on the models using the policies specified in the polar file.

To use sqlalchemy-oso, 

1. Determine the table or models you want to apply RBAC on. In our case, we want to limit access to Observations table to only users who have relationship to the station from where the Observations were made.

2. Define the polar policy file

```
policy.polar

allow(user: Users, "read", observation: Observations) if
    observation.station in user.station_ids;

allow(user: Users, "write", observation: Observations) if
    observation.station in user.station_ids;

```

In the above policy definition we are allowing read and write permissions on observations table to users who have a relationship with the source station.


## Sample Setup 

```

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

# Migrate tables
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Create Station 1 and Station 2
station1 = Stations(id="1",name="Station 1")
station2 = Stations(id="2", name="Station 2")

# Create test users
user1 = Users(id="1",username="John Doe")
user2 = Users(id="2", username="Emeka Adeola")

# User 1 is registered only to station 1
user1.stations.append(station1)

# User 2 is registered to both station 1 and 2
user2.stations.append(station2)
user2.stations.append(station1)

# Add all to database
session.add_all([user1,user2])
session.commit()

# Create Station 1 observations
obs1 = Observations(id="1",comments="First observation from station 1", station=station1.id)
obs2 = Observations(id="2",comments="Second observation from station 1", station=station1.id)

# Create Station 2 observations
obs3 = Observations(id="3",comments="First observation from station 2", station=station2.id)
obs4 = Observations(id="4",comments="Second observation from station 2", station=station2.id)

session.add_all([obs1,obs2, obs3, obs4])
session.commit()
session.close()

```

## Comparison of Queries using Standard Sqlalchemy and Oso

With standard sqlalchemy:

Any user can query the Observations table and would retrieve all the data.

```
# Create standard session
session = Session()
observations = session.query(Observations).all()

assert len(observations) == 4

```

Using sqlachemyl-oso:

Sqlachemy-oso requires you pass the authenticated user to the session as such:

```
# Define a custom user authentication that would retrieve the current user

# The current user id
user_id = "1"

# Action to be performed by user
action = "read"

def get_authenticated_user(user_id: str):
    """ Uses the standard session to retrieve user info """ 
    Session = sessionmaker(bind=db_engine)
    session = Session()
    user = session.query(Users).filter(Users.id == user_id).one()
    return user


# Create an authorised session

AuthorizedSession = authorized_sessionmaker(bind=db_engine,
                                                get_oso=lambda: oso,
                                                get_user=lambda: get_authenticated_user(user_id),
                                                get_checked_permissions=lambda: { Observations: action })
auth_session = AuthorizedSession()

# Query the observations table
observations = auth_session.query(Observations).all()

# Only 2 observations can eb retrieved by this user
assert len(observations) == 2
```
