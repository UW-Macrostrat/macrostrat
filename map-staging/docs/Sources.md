Potential Data Sources
======================

This file lists out potential data sources and what it might take to scrape
or otherwise acquire new maps from them.


Wisconsin
---------

[On the web.](https://wgnhs.wisc.edu/catalog/publication?res_extras_element_type=Map&tags=Bedrock+Geology)

Potential approach:

- Query for the list of all packages:

      GET https://wgnhs.wisc.edu/catalog/api/3/action/package_list

- Query for the information for a specific package:

      GET https://wgnhs.wisc.edu/catalog/api/3/action/package_show?id={package_id}

- Search the output for `resources` with `tag_string = Bedrock Geology` and
  `element_type = GIS Data`.

- Download and ingest the `url`.
