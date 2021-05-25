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

### Bugs:

Deleting nodes where points are shared doesn't work. This may be trickier to solve.

The custom modes for clicking, dragging and line creation are not isolated enough from the map itself. Some of the methods inside these modes set variables outside of the interal map state. Solution: move variables to internal state. 

The `draw.udpate` logic should be moved to the custom line mode at the `onStop` or a similar event.

### Goals:

Create a column version management system. Similar to git... Have a "compare" view to view two topology versions sideby side or on top. Metadata descriptions about project being edited.. Total area of polygons.

Have a info panel at top: what project, total area of polygons.

Have a "properties" view which shows the topology faces, and color coded based on if they have an identity or not. This view would also ideally support editing properties of the column geometries.

Ability to switch between different projects and maybe even different drafts of projects.
