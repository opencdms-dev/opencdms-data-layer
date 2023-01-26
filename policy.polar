allow(user: Users, "read", observation: Observations) if
    observation.station in user.station_ids;

allow(user: Users, "write", observation: Observations) if
    observation.station in user.station_ids;
