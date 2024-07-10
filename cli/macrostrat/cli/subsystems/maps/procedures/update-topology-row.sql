UPDATE {data_schema}.linework l
SET
  topo = topology.toTopoGeom(
        l.geometry,
        :topo_name,
        {topo_schema}.__linework_layer_id(),
        0.01
      ),
      geometry_hash = {topo_schema}.hash_geometry(l),
      topology_error = null
WHERE l.source_id = :source_id;
