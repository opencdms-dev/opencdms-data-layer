# opencdms-data-layer


## Steps

1. Run `docker-compose up -d`.
2. `docker-compose run db-builder`
3. `pytest`


# ERD Diagram

[ERD Diagram](assets/opencdms_erd.png "ERD diagram")

## Problem Statement

Enforcing a RBAC system and multi-tenancy on database is a herculian task. Here we have
similar problem controlling who has access to Opencdms models. In this project, we used Sqlalchemy-oso to enforce RBAC system on opencdms database.

In this database, We have observations table which collects observations from different Stations.
In these stations, we have users who run the daily activities of the station. Members in one station, have no relationship with members in another station. And staff members in a station, have 
defined activities which they can perform.

In Station we have four roles that a user can have namely:
1. rainfall  can "read_observation" in a station.
2. operator can  "list_observation" in station and inherits rainfall permissions.
3. metadata can "create_observation" in a station and inherits operator permissions.
4. admin  inherits metadata permissions.

The admin can perform any activity that other members can perform but cannot do same in other station.

The activities permissions above is not resource specific, notice there is no delete_permissions and update_permissions. Hence we need a means to enforce authorization on the resource level as well.


### Sqlalchemy-oso solution

Using oso, an authorization framework, we are able to define the application authorization logic, both at the stations level and at the observation table. 

To do this we define and StationsRole table that would contain the role assignment to users in a station. Then in the authorization.polar file we define:

1. the actor to assume the role, in our case the  User model.
2. the resource on which the action would be performed, the Station and the Observation models in our case
3. In the resource schema, we define the available roles in that resource and the corresponding permissions. We can also specify the permission inheritance logic.

#### Enforcing authorization

To enforce the authorization we call oso.authorize(actor, "permission_name", resource) to check if the actor (User) has the permission to perform the desired action on the resource.


### Example authorization.polar file

```
authorization.polar

actor Users {}

# Station resource
resource Stations {
    
    roles = ["admin", "metadata", "operator", "rainfall"];
    permissions = [
        "read_observation",
        "list_observation",
        "create_observation",
   ];

   "read_observation" if "rainfall";
   "list_observation" if "operator";
   "create_observation" if "metadata";

   "rainfall" if "operator";
   "operator" if "metadata";
   "metadata" if "admin";

    
}

has_role(user: Users, name: String, station: Stations) if
    role in user.station_roles and
    role matches { name: name, station_id: station.id };


resource Observations {
  roles = ["reader", "writer" ];
  permissions = [
        "read_observation",
        "list_observation",
        "create_observation",
        "delete_observation",
        "update_observation"
   ];
  relations = { parent: Stations };
  
  "read_observation" if "reader";
  "list_observation" if "reader";
  "create_observation" if "writer";

  "reader" if "writer";
  "writer" if "admin" on "parent";

  "delete_observation" if "admin" on "parent";
  "update_observation" if "admin" on "parent";

  
}

has_relation(station: Stations, "parent", observation: Observations) if observation.source_station = station;

```

From the above snippets, rainfall staff role has the least privileges, it can only read an observation in a station but cannot list_observation nor create_observation. Conversely, the admin, though not explictly defined, inherits all the permissions owned by metadata, which in turn inherits that of the operator role. Of cource there must be a corresponding table model in which these roles are assgined to the correponding users.

See below:

```
class StationsRole(Base):
    __tablename__ = "station_roles"
    __table_args__ = {'schema': 'cdm'}
    name = Column(String, index=True)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("cdm.users.id"), nullable=False)
    station_id = Column(String, ForeignKey("cdm.stations.id"), nullable=False)
    user = relationship("Users", backref=backref("station_roles", lazy=False), lazy=False)
    station = relationship("Stations", backref=backref("roles", lazy=False), lazy=False)
```


On the observations table, it has a relationship with the Stations table as the parent. Notice that the roles on the parent table, can be assigned permissions on the Observations table. Hence only admin in a Station can update_observation and delete_observation. Since the reader and writer roles are unique to this table, we can choose to optionally create a table mapping ObservationRole to represent users who are assigned these unique roles. But since we want to scope all roles to the station roles, its not needed. 

 
### Example Policy enforcement

```
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
```

In the above snippet, we demonstrate how used oso to authorize user's action on the controller level.
Users who do not have the required permissions get a NotFoundError or AuthorizationError. For example:

```
@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_can_delete_observation_in_own_station(authorized_user, db_session):
    res = delete_observation(authorized_user,STATION["london"],TEST_LONDON_OBSERVATION_ID, db_session)
    assert res is True
    
@pytest.mark.parametrize("authorized_user", [(LONDON_STAFF["admin"],)],indirect=True)
def test_admin_cannot_delete_observation_in_another_station(authorized_user, db_session):
    with pytest.raises(exceptions.AuthorizationError):
        delete_observation(authorized_user,STATION["london"], TEST_NIGERIA_OBSERVATION_ID, db_session)


```

In the test cases above, we could see that an admin user from a station in London can delete observations in London but cannot delete observations from a station in Nigeria.

