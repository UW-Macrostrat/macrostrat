# Topology Editing

### Introduction:

Column-Topology is an application that is aimed at editing GeoJSON polygons **_while_** keeping topology. This application is being developed under the [UW-Macrostrat](https://macrostrat.org/) lab group.

### Motivation:

The Macrostrat group keeps track of sedimentary columns around the world and a U.I interface for editing and creating new columns, in the form of GeoJSON polygons, is needed. An easy to use interface that allows users to create and edit their topologies would help expand the macrostrat database and increase community unification.

Editing topologies is a difficult problem and outside of expense desktop solutions (ArcGIS) it has not been solved. Advancements in technology, topojson and mapbox gl draw, have made it easier to develop these tools open-source. Client side editing is ideal for quick visualization.

### Strategy:

Most of the work has been done on the client side (javascript). The frontend is made using React js with vanilla javascript as well. For the map I am using [Mapbox-gl](https://github.com/mapbox/mapbox-gl-js) and for GeoJSON rendering I am using [Mapbox-gl-draw](https://github.com/mapbox/mapbox-gl-draw). Conceptually, I am thinking about it as lines instead of polygons. In a topology, polygons share sides, which is why in topojson they remove redundant coordinates. Here I think about it similiarly. All the sides of a polygon turn in lines. Then all you need to do is drag the vertices around.

### Progress:

You can click on a point, that has more than one vertex, and drag them together, causing the lines to also be dragged together. Deleting and creating nodes also work.

### Goals:

Create a new "polygon", by either splitting an existing one or adding a new one to the perimeter of the topology.

Creating a new topology from scratch.
