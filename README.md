# opencdms-data-layer


## Steps

1. Run `docker-compose up -d`.
2. `docker-compose run db-builder`
3. `python build_db.py`


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

The activities permissions above is not resource specific, notice there is no delete_permissions and update_permissions. Hence we need a means to enforce authorization on the resource level.




