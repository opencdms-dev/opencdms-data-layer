
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
