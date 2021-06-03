# Topology Editing

### Introduction:

Column-Topology is an application that is aimed at editing GeoJSON polygons **_while_** keeping topology. This application is being developed under the [UW-Macrostrat](https://macrostrat.org/) lab group.

This application will hopefully be a column management system for footprint geometries for strategraphic columns.

### Motivation:

The Macrostrat group keeps track of sedimentary columns around the world and a U.I interface for editing and creating new columns, in the form of GeoJSON polygons, is needed. An easy to use interface that allows users to create and edit their topologies would help expand the macrostrat database and increase community unification.

Editing topologies is a difficult problem and outside of expense desktop solutions (ArcGIS) it has not been solved. Advancements in technology, topojson and mapbox gl draw, have made it easier to develop these tools open-source. Client side editing is ideal for quick visualization.

### Strategy:

Most of the work has been done on the client side (javascript). The frontend is made using React js with vanilla javascript as well. For the map I am using [Mapbox-gl](https://github.com/mapbox/mapbox-gl-js) and for GeoJSON rendering I am using [Mapbox-gl-draw](https://github.com/mapbox/mapbox-gl-draw). Conceptually, I am thinking about it as lines instead of polygons. In a topology, polygons share sides, which is why in topojson they remove redundant coordinates. Here I think about it similiarly. All the sides of a polygon turn in lines. Then all you need to do is drag the vertices around.

### Progress/ changelog:

You can click on a point, that has more than one vertex, and drag them together, causing the lines to also be dragged together. Deleting and creating nodes also work.

Can create new polygons from scratch using the line create tool. Edits are relatively easy, except for bugs listed below.

Backend is bootstrapped to postgis-geologic-map and mapboard-server. Creates topology nicely from lines and centroid identity polygons.

Database persistence onClick of the `save` button.

Fixed Bug of dragging two points in same feature and 1+ of another feature. My mistake was overcomplicating the logic.

I have successfully isolated the fronted custom drawing modes. Now state is handled the "right" way. The `draw.update` logic is performed in the `directselect.onstop` method.

It looks like these coding clean-ups have also fixed the deleting points where shared bug that was occuring. But some odd behavior is causing me to leave it on bugs.

Created a `GET` endpoint on top of a view table that joins `map_face` from `map_topology` schema onto the identity polygons and then the column properties table. Renders in the frontend as a geojson layer in mapbox, shade is determined by if the column has an identity.

Clicking on shaded column brings a popup that has some basic info about the column.

06/03/2021:
Fixed the identity polygon bug, instead of using centroid use `ST_PointOnSurface`. It returns the "visual center" of a polygon much like the point of unaccessability.

Polygons are automatically added to map_face table without an identity polygon being set. New polygons can be created using the line tool.

Enhanced frontend with blueprint components. Nav bar buttons allows for saving and toggling between property and edit modes.

Property editing works! Uses `ModelEditor` component from ui-components.

Frontend component for if a polygon has two identities is around. Lists them as cards and you can choose which one.

### Bugs:

Deleting nodes where points are shared doesn't work. This may be trickier to solve. Sometimes it seems like the code is breaking here and other times not..

Forseable Bug-- when deciding how map-faces get col identity, it is possible that a user will cut an identity column, which would mean both columns, old and generated, would recieve the same identity. I think to solve this we could employ a frontend warning or something.

When creating a self-closing line to form a polygon, sometimes on save the ends separate. This was generally fixed when I tried closing them again. But maybe theres an easier way.

### Goals:

Create a column version management system. Similar to git... Have a "compare" view to view two topology versions sideby side or on top. Metadata descriptions about project being edited.. Total area of polygons.

Have a info panel at top: what project, total area of polygons.

Ability to switch between different projects and maybe even different drafts of projects.

### Next Steps:

Backend workflow to remove an identity polygon when there are two for an geometry.

Create a more structured database including a specific column attributes table for column ids and their attributes.

Backend workflow for adding identity to a polygon without any. A newly created polygon. Once properties are made on the frontend, need a backend process that creates a new identity polygon with a foreign key that matches the correct properties, whether they are new or exisiting.

Backend Workflow and frontend exposure of project import from macrostrat, what are the different properties that we care about?

- Need to talk to Shanan about the properties
- Need to adjust the database to handle multiple projects
- Frontend needs a way to request a project from macrostrat
  - have a list of projects currently in macrostrat?

Backend workflow and frontend implementation of getting data out! Need a geojson spitter outer.

- Forms geojson from whatever `column_map_face` view I have in the end.
- Will include all geometries and identity polygons as point
  - for that `ST_Centroid` will work because the identity polygons are symmetrical.
