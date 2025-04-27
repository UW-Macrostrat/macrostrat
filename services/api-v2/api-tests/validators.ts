//var sizeOf = require("image-size");
const axios = require("axios");

module.exports = {
  aSuccessfulRequest: function (res: {
    statusCode: number;
    headers: { [x: string]: string };
  }) {
    if (res.statusCode !== 200) {
      console.log(res.statusCode);
      throw new Error("Bad status code");
    }
    if (res.headers["access-control-allow-origin"] !== "*") {
      throw new Error("Wrong access-control-allow-origin headers");
    }
  },

  metadata: function (res: {
    body: {
      success: {
        description: any;
        options: {
          parameters: {};
          output_formats: string | any[];
          examples: string | any[];
          fields: {};
        };
      };
    };
  }) {
    // Make sure all the key metadata sections exist
    if (!res.body.success.description) {
      throw new Error("Route description missing");
    }
    if (!res.body.success.options) {
      throw new Error("Route options missing");
    }
    if (!res.body.success.options.parameters) {
      throw new Error("Route parameters missing");
    }
    if (!res.body.success.options.output_formats) {
      throw new Error("Route output formats missing");
    }
    if (!res.body.success.options.examples) {
      throw new Error("Route examples missing");
    }
    if (!res.body.success.options.fields) {
      throw new Error("Route fields missing");
    }

    // Make sure the metadata sections are formatted properly
    if (!(res.body.success.options.parameters instanceof Object)) {
      throw new Error("Something wrong with parameters object");
    }
    if (!(res.body.success.options.output_formats instanceof Array)) {
      throw new Error("Something wrong with output formats array");
    }
    if (!(res.body.success.options.examples instanceof Array)) {
      throw new Error("Something wrong with examples array");
    }
    if (!(res.body.success.options.fields instanceof Object)) {
      throw new Error("Something wrong with fields object");
    }

    // Make sure metadata sections are populated
    if (Object.keys(res.body.success.options.parameters).length < 1) {
      throw new Error("Route is missing parameters");
    }
    if (res.body.success.options.output_formats.length < 1) {
      throw new Error("Route is missing output formats");
    }
    if (res.body.success.options.examples.length < 1) {
      throw new Error("Route is missing examples");
    }
    if (Object.keys(res.body.success.options.fields).length < 1) {
      throw new Error("Route is missing field definitions");
    }
  },

  aSample: function (res: {
    body: {
      success: {
        data: { type: any; features: string | any[]; length: number };
      };
    };
  }) {
    // Make sure 5 records were returned
    if (res.body.success.data.type) {
      if (res.body.success.data.features.length !== 5) {
        throw new Error("Sample returned wrong number of records");
      }
    } else {
      if (res.body.success.data.length !== 5) {
        throw new Error("Sample returned wrong number of records");
      }
    }
  },

  projectSample: function (res: {
    body: {
      success: {
        data: { type: any; features: string | any[]; length: number };
      };
    };
  }) {
    // Make sure 13 records were returned
    if (res.body.success.data.type) {
      if (res.body.success.data.length !== 13) {
        throw new Error("Sample returned wrong number of records");
      }
    }
  },

  geoJSON: function (res: {
    body: { success: { data: { type: string; features: any[] } } };
  }) {
    if (res.body.success.data.type !== "FeatureCollection") {
      throw new Error("GeoJSON was not returned");
    }

    res.body.success.data.features.forEach(function (d, index) {
      if (
        !d.geometry ||
        !d.geometry.coordinates ||
        !d.geometry.coordinates.length ||
        !d.properties
      ) {
        console.error("Malformed feature at index:", index, d); // Log issue for inspection
        throw new Error(`GeoJSON was malformed at feature index ${index}`);
      }
    });
  },

  topoJSON: function (res: { body: { success: { data: { type: string } } } }) {
    if (res.body.success.data.type !== "Topology") {
      throw new Error("TopoJSON was not returned");
    }
  },

  json: function (res: { body: { success: any; error: any } }) {
    if (!res.body.success && !res.body.error) {
      throw new Error("Request did not return valid JSON");
    }
  },

  csv: function (res: { body: string | any[] }) {
    if (res.body.length < 10) {
      throw new Error("No CSV output recieved");
    }
  },

  tile: function (res: any) {
    if (res.headers["content-type"] != "image/png") {
      throw new Error("Wrong content-type header on tile");
    }
    if (res.headers["content-length"] < 200) {
      throw new Error("Empty tile returned");
    }
    /*var dims = sizeOf(res.body);
    if (dims.width != 512 || dims.height != 512) {
      throw new Error("Tile has the wrong dimensions");
    }*/
  },

  atLeastOneResult: function (res: {
    body: { success: { data: string | any[] } };
  }) {
    if (res.body.success.data.length < 1) {
      throw new Error("Should have returned at least one result");
    }
  },

  correctDataTypes: function (res: any) {
    const data = res.body.success.data;
    data.forEach(
      (item: { t_age: any; b_age: any; t_prop?: any; t_int_age?: any }) => {
        if (typeof item.t_age !== "number") {
          throw new Error(
            `t_age is not a numeric type: ${item.t_age} (type: ${typeof item.t_age})`,
          );
        }
        if (typeof item.b_age !== "number") {
          throw new Error(
            `b_age is not a numeric type: ${item.b_age} (type: ${typeof item.b_age})`,
          );
        }
        if (item.t_prop !== undefined && typeof item.t_prop !== "number") {
          throw new Error(
            `t_prop is not a numeric type: ${item.t_prop} (type: ${typeof item.t_prop})`,
          );
        }
        if (
          item.t_int_age !== undefined &&
          typeof item.t_int_age !== "number"
        ) {
          throw new Error(
            `t_int_age is not a numeric type: ${item.t_int_age} (type: ${typeof item.t_int_age})`,
          );
        }
      },
    );
  },

  async compareWithProduction(queryParams = "", localResponse: any) {
    const prodUrl = `https://www.macrostrat.org/api/v2${queryParams}`;
    const externalResponse = await axios.get(prodUrl);
    if (
      JSON.stringify(localResponse.body) !==
      JSON.stringify(externalResponse.data)
    ) {
      throw new Error(
        `Mismatch for endpoint: ${queryParams}\nLocal: ${JSON.stringify(
          localResponse.body,
          null,
          2,
        )}\nProduction: ${JSON.stringify(externalResponse.data, null, 2)}`,
      );
    }
  },
};
