# Changelog:

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

09/01/21:

Can add a known geometry by pasting either geojson or wkt into text box.

Map legend for column-groups

09/13/21:

Column-groups are now project specific.

Frontend and Backend are Dockerized

11/23/21:

Frontend and sql queries adjusted to allow for `multilinestrings`. Dragging points
together uses more internal Mapbox-gl-js-draw methods now, consequently dragging is
more effecient and works better.

The `SnapLineMode` creates valid multiline strings. Now when using the tool if you snap to a non-vertix point on an existing line, it creates a vertix on that line at that position. This makes creating columns easier and more effcient.

12/27/21:

Backend:

- `clean_change_set` function is more efficient.

Frontend:

- U.I enhancements: Remodeled navbar and main overlay. About tab has short 'how to' section. Property dialog is draggable.
- Increased the click-buffer when determining which features' points should be dragged, increasing drag reliability. Also,
  when holding down the `shift` key while clicking on a vertex will ignore any dragging, allowing for un-linking vertices.
- Draw Polygon mode is much more enhanced. OnClick a n-sided polygon (hexagon by default) is created and mousemove will change
  size of the polgyon. Pressing 'a' (add) and 's' (subtract) allow the user to add or subtract how many sides the n-sided polygon
  has (minimum 3).

### Bugs:

Strange console error, `Cannot read property 'getSelectedIds' of null`, on stopDragging event

- This occurs during the onTouchEnd and onMouseUp in the custom direct_select
- During the `this.fireUpdate()`

Forseable Bug-- when deciding how map-faces get col identity, it is possible that a user will cut an identity column, which would mean both columns, old and generated, would recieve the same identity. I think to solve this we could employ a frontend warning or something.

`isEditing` state of prop overlay needs to be better handled onClose or onSave.

### Next Steps/ Wanted Features:

Backend workflow to remove an identity polygon when there are two for an geometry.

- Rounding of points, to 4 spots

- Will include all geometries and identity polygons as point
  - for that `ST_Centroid` will work because the identity polygons are symmetrical.

Dockerization

Maybe have the ability to teselate polygons into n internal polygons.

Ability to copy the properties, i.e `column_name`, `col_group`, `col_group_name` from nearby columns.. Maybe a suggester based on columns nearby.

Move viewport to "next column without an column property."

Export CSV

Burwell Layer

Highlight lines on snap, on Join

eODP -- drill hole points, polygons aren't showing up. Perhaps render the centroid as a point.

Feedback on import and create new project should catch errors and display them

Download individual columns, column-groups and selected columns (multiple)

Notes field for column properties
