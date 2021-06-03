# Topology Editing

### Introduction:

Column-Topology is an application that is aimed at editing GeoJSON polygons **_while_** keeping topology. This application is being developed under the [UW-Macrostrat](https://macrostrat.org/) lab group.

This application will hopefully be a column management system for footprint geometries for strategraphic columns.

### Motivation:

The Macrostrat group keeps track of sedimentary columns around the world and a U.I interface for editing and creating new columns, in the form of GeoJSON polygons, is needed. An easy to use interface that allows users to create and edit their topologies would help expand the macrostrat database and increase community unification.

Editing topologies is a difficult problem and outside of expense desktop solutions (ArcGIS) it has not been solved. Advancements in technology, topojson and mapbox gl draw, have made it easier to develop these tools open-source. Client side editing is ideal for quick visualization.

### Strategy:

Most of the work has been done on the client side (javascript). The frontend is made using React js with vanilla javascript as well. For the map I am using [Mapbox-gl](https://github.com/mapbox/mapbox-gl-js) and for GeoJSON rendering I am using [Mapbox-gl-draw](https://github.com/mapbox/mapbox-gl-draw). Conceptually, I am thinking about it as lines instead of polygons. In a topology, polygons share sides, which is why in topojson they remove redundant coordinates. Here I think about it similiarly. All the sides of a polygon turn in lines. Then all you need to do is drag the vertices around.

### Progress:

You can click on a point, that has more than one vertex, and drag them together, causing the lines to also be dragged together. Deleting and creating nodes also work.

Can create new polygons from scratch using the line create tool. Edits are relatively easy, except for bugs listed below.

Backend is bootstrapped to postgis-geologic-map and mapboard-server. Creates topology nicely from lines and centroid identity polygons.

Database persistence onClick of the `save` button.

Fixed Bug of dragging two points in same feature and 1+ of another feature. My mistake was overcomplicating the logic.

I have successfully isolated the fronted custom drawing modes. Now state is handled the "right" way. The `draw.update` logic is performed in the `directselect.onstop` method.

It looks like these coding clean-ups have also fixed the deleting points where shared bug that was occuring. But some odd behavior is causing me to leave it on bugs.

Created a `GET` endpoint on top of a view table that joins `map_face` from `map_topology` schema onto the identity polygons and then the column properties table. Renders in the frontend as a geojson layer in mapbox, shade is determined by if the column has an identity.

Clicking on shaded column brings a popup that has some basic info about the column.

### Bugs:

Deleting nodes where points are shared doesn't work. This may be trickier to solve. Sometimes it seems like the code is breaking here and other times not..

Forseable Bug-- when deciding how map-faces get col identity, it is possible that a user will cut an identity column, which would mean both columns, old and generated, would recieve the same identity. I think to solve this we could employ a frontend warning or something.

Identity polygon, as centroids don't work! Centroids are not always inside of a polygon, especially irregularly shaped ones, which is basically all geology columns. Possible solution: Point of Unaccessability, not implemented in postgis but there is a JavaScript algorithm I think.

### Goals:

Create a column version management system. Similar to git... Have a "compare" view to view two topology versions sideby side or on top. Metadata descriptions about project being edited.. Total area of polygons.

Have a info panel at top: what project, total area of polygons.

Have a "properties" view which shows the topology faces, and color coded based on if they have an identity or not. This view would also ideally support editing properties of the column geometries.

Ability to switch between different projects and maybe even different drafts of projects.
