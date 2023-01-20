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

