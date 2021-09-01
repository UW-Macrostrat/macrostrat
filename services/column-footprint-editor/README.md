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

07/02/21:

Multiple projects exist in the database as separate schemas and linked topologies using a config file for each project and a passing the project_id and config to a database class instance. The config is also passed to the docker container through a subprocess so the map topology can resolve the correct schema.

Frontend WIP, click and add polygon. For now it just adds a box. Can become much more sophisticated to sense polygons around it and attach to their vertices if they're close by.

07/13/21:

Can swtich between projects through navbar and open import dialog. Import dialog has more info including all of the available projects in macrostrat.

`change_set_clean` function for backend works much better now.

Projects table in database holds project name and description.

Slightly better U.I with more info in the import overlay

Helper Project class created to make passing project attributes around easier

08/02/21:

Frontend context has more robust architecture. A async runActions allows for side-effects like fetching data
in an async method while also passing off the dispatch for the rest of the app reducer. Things are simplified and standardized through types as well.

Backend Project and Database class have some new methods to make it easier for creating a new project.

Can now successfully create blank new projects through the frontend.

08/20/21:

Deleting shared nodes now works and doesn't break the frontend.

Backend `clean_changeset` function works much better now after some additional fixes.

MAJOR FEATURE ADDITION:

- The ability to view, assign, and create `col_groups` and `col_group_names`.

onClick highlight of column in property view.

A color coded legned for column info.

feedback on create new project and import

### Bugs:

Strange console error, `Cannot read property 'getSelectedIds' of null`, on stopDragging event

Forseable Bug-- when deciding how map-faces get col identity, it is possible that a user will cut an identity column, which would mean both columns, old and generated, would recieve the same identity. I think to solve this we could employ a frontend warning or something.

`isEditing` state of prop overlay needs to be better handled onClose or onSave.

### Goals:

Create a column version management system. Similar to git... Have a "compare" view to view two topology versions sideby side or on top. Metadata descriptions about project being edited.. Total area of polygons.

Have a info panel at top: what project, total area of polygons.

Some component that shows the change_set with maybe the ability to undo them.

Ability to switch between different projects and maybe even different drafts of projects.

### Next Steps/ Wanted Features:

Backend workflow to remove an identity polygon when there are two for an geometry.

- Rounding of points, to 4 spots

- Will include all geometries and identity polygons as point
  - for that `ST_Centroid` will work because the identity polygons are symmetrical.

Dockerization

Add a known geometry-- like a basin geometry. Maybe have the ability to teselate it into n internal polygons.

Ability to copy the properties, i.e `column_name`, `col_group`, `col_group_name` from nearby columns.. Maybe a suggester based on columns nearby.

Move viewport to "next column without an column property."

Export CSV

Column groups need to be unique to projects--have a project specific column-group table

Burwell Layer

Highlight lines on snap, on Join

eODP -- drill hole points, polygons aren't showing up. Perhaps render the centroid as a point.

Feedback on import and create new project should catch errors and display them

Download individual columns, column-groups and selected columns (multiple)

Notes field for column properties
