"use strict";
const api = require("./api");
const larkin = require("./larkin");
const buffer = require("@turf/buffer");
const envelope = require("@turf/envelope");
const hillshade = require("hillshadejs");
const hillshadeCache = require("./hillshadeCache");

function big(coord) {
  let point = {
    type: "Point",
    coordinates: coord,
  };

  let bigBuffer = envelope(buffer(point, 22, "miles"));
  let smallBuffer = envelope(buffer(point, 12, "miles"));

  let minLngs = smallBuffer.geometry.coordinates[0].map((coords) => {
    return coords[0];
  });

  let minLng = Math.min.apply(null, minLngs);
  let maxLng = Math.max.apply(null, minLngs);

  let maxLats = bigBuffer.geometry.coordinates[0].map((coords) => {
    return coords[1];
  });

  let minLat = Math.min.apply(null, maxLats);
  let maxLat = Math.max.apply(null, maxLats);

  return [minLng, minLat, maxLng, maxLat];
}

function small(coord) {
  let point = {
    type: "Point",
    coordinates: coord,
  };

  let bigBuffer = envelope(buffer(point, 4, "miles"));
  let smallBuffer = envelope(buffer(point, 2, "miles"));

  let minLats = smallBuffer.geometry.coordinates[0].map((coords) => {
    return coords[1];
  });

  let minLat = Math.min.apply(null, minLats);
  let maxLat = Math.max.apply(null, minLats);

  let maxLngs = bigBuffer.geometry.coordinates[0].map((coords) => {
    return coords[0];
  });

  let minMaxLng = Math.min.apply(null, maxLngs);
  let maxMaxLng = Math.max.apply(null, maxLngs);

  return [minMaxLng, minLat, maxMaxLng, maxLat];
}

const VALID_ASPECTS = ["small", "big"];

module.exports = (req, res, next) => {
  if (Object.keys(req.query).length < 1) {
    return larkin.info(req, res, next);
  }
  if ((!req.query.lat || !req.query.lng) && !("sample" in req.query)) {
    return larkin.error(req, res, next, "Invalid parameters", 401);
  }

  let lng = larkin.normalizeLng(req.query.lng) || -89.4;
  let lat = parseFloat(req.query.lat) || 43.07;

  let aspect = req.query.aspect ? req.query.aspect : "small";

  if (VALID_ASPECTS.indexOf(aspect) === -1) {
    aspect = "small";
  }
  // Check the cache
  hillshadeCache.get([lng, lat], aspect, (error, buffer) => {
    if (error) {
      console.log(error);
    }
    if (buffer) {
      return larkin.sendImage(req, res, next, buffer, true);
    }

    let extent = aspect === "small" ? small([lng, lat]) : big([lng, lat]);

    hillshade(
      extent,
      {
        zoom: aspect === "small" ? 12 : 10,
        format: "jpeg",
      },
      (error, jpeg) => {
        if (error) {
          console.log(error);
          return larkin.error(req, res, next, "Internal error", 500);
        }
        hillshadeCache.set(
          [lng, lat],
          aspect,
          Math.random().toString(36).substring(15),
          jpeg,
        );

        larkin.sendImage(req, res, next, jpeg, false);

        // Go ahead and cache the big version
        if (aspect === "small") {
          extent = big([lng, lat]);
          hillshade(
            extent,
            {
              zoom: 10,
              format: "jpeg",
            },
            (error, jpeg) => {
              if (error) {
                console.log(error);
                return;
              }
              hillshadeCache.set(
                [lng, lat],
                "big",
                Math.random().toString(36).substring(15),
                jpeg,
              );
            },
          );
        }
      },
    );
  });
};
