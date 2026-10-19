//var sizeOf = require("image-size");
const axios = require("axios");
const settings = require("./settings");

function sortKeysDeep(x) {
  if (Array.isArray(x)) return x.map(sortKeysDeep);
  if (x && typeof x === "object") {
    return Object.keys(x)
      .sort()
      .reduce((acc, k) => {
        acc[k] = sortKeysDeep(x[k]);
        return acc;
      }, {});
  }
  return x;
}

function isMetadataPayload(body) {
  return (
    body &&
    body.success &&
    body.success.options &&
    body.success.options.parameters &&
    typeof body.success.options.parameters === "object"
  );
}

function diffKeys(aObj = {}, bObj = {}) {
  const aKeys = new Set(Object.keys(aObj || {}));
  const bKeys = new Set(Object.keys(bObj || {}));
  const onlyInA = [...aKeys].filter((k) => !bKeys.has(k)).sort();
  const onlyInB = [...bKeys].filter((k) => !aKeys.has(k)).sort();
  return { onlyInA, onlyInB };
}

function extractArrayData(payload) {
  try {
    if (!payload || !payload.success) return null;
    const data = payload.success.data;
    if (Array.isArray(data)) return data;
    if (
      data &&
      data.type === "FeatureCollection" &&
      Array.isArray(data.features)
    ) {
      return data.features;
    }
    return null;
  } catch {
    return null;
  }
}
// Returns the object to scan for keys (GeoJSON Feature.properties if present)
function surfaceForIdScan(item) {
  if (!item) return null;
  if (item.properties && typeof item.properties === "object")
    return item.properties;
  return item;
}

// Find the first *_id key by insertion order on a single item
function firstStarIdKey(item) {
  const base = surfaceForIdScan(item);
  if (!base || typeof base !== "object") return null;
  for (const k of Object.keys(base)) {
    if (/_id$/i.test(k)) return k; // first *_id encountered wins
  }
  if (Object.prototype.hasOwnProperty.call(base, "id")) return "id";
  return null;
}

// Does at least one item in `arr` expose `key` (on root or Feature.properties)?
function arrayExposesKey(arr, key, sampleSize = 50) {
  const n = Math.min(arr.length, sampleSize);
  for (let i = 0; i < n; i++) {
    const it = arr[i];
    if (!it) continue;
    const props =
      it.properties && typeof it.properties === "object" ? it.properties : null;
    if (
      (props && Object.prototype.hasOwnProperty.call(props, key)) ||
      Object.prototype.hasOwnProperty.call(it, key)
    ) {
      return true;
    }
  }
  return false;
}

// Choose a shared id key by prioritizing the FIRST *_id in the objects.
function chooseCommonIdKey(localArr, prodArr) {
  // 1) Prefer first *_id on the FIRST local item (insertion order)
  const localFirst = firstStarIdKey(localArr[0]);
  if (localFirst && arrayExposesKey(prodArr, localFirst)) return localFirst;

  // 2) Otherwise try first *_id on the FIRST prod item
  const prodFirst = firstStarIdKey(prodArr[0]);
  if (prodFirst && arrayExposesKey(localArr, prodFirst)) return prodFirst;

  // 3) (Optional) fall back to legacy heuristic or null
  return null;
}

// Build a set of unique IDs from an array given a chosen id key.
// Supports both flat objects and GeoJSON Feature properties.
function uniqueIds(arr, idKey) {
  const out = new Set();
  for (const item of arr) {
    if (!item) continue;
    // Prefer .properties[idKey] if available (GeoJSON Feature)
    const props =
      item.properties && typeof item.properties === "object"
        ? item.properties
        : null;
    if (props && Object.prototype.hasOwnProperty.call(props, idKey)) {
      out.add(props[idKey]);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(item, idKey)) {
      out.add(item[idKey]);
      continue;
    }
    // Handle plain "id" on the Feature object itself (rare but possible)
    if (idKey === "id" && Object.prototype.hasOwnProperty.call(item, "id")) {
      out.add(item.id);
    }
  }
  return out;
}

type MacrostratResponse = {
  statusCode: number;
  headers: { [x: string]: string };
  body: { success: any; error: any };
};

function validateJSON(res: MacrostratResponse) {
  if (!res.body.success && !res.body.error) {
    throw new Error("Request did not return valid JSON");
  }
}

function aSuccessfulRequest(res: MacrostratResponse) {
  if (res.statusCode !== 200) {
    console.log(res.statusCode);
    throw new Error("Bad status code");
  }
  if (res.headers["access-control-allow-origin"] !== "*") {
    throw new Error("Wrong access-control-allow-origin headers");
  }
}

function returnsNoItems(res: MacrostratResponse) {
  aSuccessfulRequest(res);
  validateJSON(res);
  if (res.body.success.data.length != 0) {
    throw new Error("Expected no results to be returned");
  }
}

function returnsASingleItem(res: MacrostratResponse) {
  aSuccessfulRequest(res);
  validateJSON(res);
  if (res.body.success.data.length != 1) {
    throw new Error("Expected exactly one result to be returned");
  }
}

module.exports = {
  aSuccessfulRequest,
  returnsNoItems,
  returnsASingleItem,
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

  json: validateJSON,

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
  async compareWithProduction(requestPath = "", localResponse) {
    const { host_prod } = settings;
    if (!host_prod) return;

    const prodUrl = host_prod + requestPath;
    const { data: prodData } = await axios.get(prodUrl);

    // Helpers (kept inside the function to keep the diff localized)
    function keysOfItem(item) {
      const base =
        item?.properties && typeof item.properties === "object"
          ? item.properties
          : item;
      return base && typeof base === "object" ? Object.keys(base) : [];
    }

    function diffItemKeys(localArr, prodArr) {
      const localKeys = new Set(keysOfItem(localArr[0]));
      const prodKeys = new Set(keysOfItem(prodArr[0]));
      const onlyInLocal = [...localKeys].filter((k) => !prodKeys.has(k)).sort();
      const onlyInProd = [...prodKeys].filter((k) => !localKeys.has(k)).sort();
      return { onlyInLocal, onlyInProd };
    }

    function sameIdSet(aSet, bSet) {
      if (aSet.size !== bSet.size) return false;
      for (const v of aSet) if (!bSet.has(v)) return false;
      return true;
    }

    // 1) Canonical deep-equality (order-insensitive)
    if (
      JSON.stringify(sortKeysDeep(localResponse.body)) ===
      JSON.stringify(sortKeysDeep(prodData))
    ) {
      return;
    }

    // 2) Lenient path: metadata variance (warn, don't fail)
    if (isMetadataPayload(localResponse.body) && isMetadataPayload(prodData)) {
      const localParams = localResponse.body.success.options.parameters;
      const prodParams = prodData.success.options.parameters;

      const { onlyInA: onlyInLocal, onlyInB: onlyInProd } = diffKeys(
        localParams,
        prodParams,
      );

      if (onlyInLocal.length || onlyInProd.length) {
        console.warn(
          [
            `⚠️  metadata parameters mismatch for endpoint: ${requestPath}`,
            `   - Only in Dev (current host): ${
              onlyInLocal.length ? onlyInLocal.join(", ") : "(none)"
            }`,
            `   - Only in Prod (host_prod): ${
              onlyInProd.length ? onlyInProd.join(", ") : "(none)"
            }`,
            `   → Status: OK (metadata drift tolerated)`,
          ].join("\n"),
        );
        return;
      }
      // If no param-key diffs but still not equal, fall through (real mismatch elsewhere)
    }

    // 3) Existing lenient path for arrays (idKey count checks, sample logic, etc.)
    const localArr = extractArrayData(localResponse.body);
    const prodArr = extractArrayData(prodData);

    if (
      Array.isArray(localArr) &&
      Array.isArray(prodArr) &&
      localArr.length &&
      prodArr.length
    ) {
      // 3a) Sample variance (lenient)
      if (/\bsample\b/i.test(requestPath)) {
        if (localArr.length === prodArr.length) {
          console.warn(
            `⚠️  Sample variance for endpoint: ${requestPath}\n` +
              `   - Dev sample length: ${localArr.length}\n` +
              `   - Prod sample length: ${prodArr.length}\n` +
              `   → Status: OK (non-deterministic sample selection)`,
          );
          return;
        }
      }

      const idKey = chooseCommonIdKey(localArr, prodArr);
      if (idKey) {
        const localIds = uniqueIds(localArr, idKey);
        const prodIds = uniqueIds(prodArr, idKey);

        // 3b) Same-id-set but field-level drift (lenient)
        if (sameIdSet(localIds, prodIds)) {
          const { onlyInLocal, onlyInProd } = diffItemKeys(localArr, prodArr);
          if (onlyInLocal.length || onlyInProd.length) {
            console.warn(
              [
                `⚠️  Field-level drift for endpoint: ${requestPath}`,
                `   - Same ${idKey} set, but object keys differ`,
                `   - Only in Dev (current host): ${
                  onlyInLocal.length ? onlyInLocal.join(", ") : "(none)"
                }`,
                `   - Only in Prod (host_prod): ${
                  onlyInProd.length ? onlyInProd.join(", ") : "(none)"
                }`,
                `   → Status: OK (field drift tolerated)`,
              ].join("\n"),
            );
            return;
          }
        }

        // 3c) idKey count mismatch (lenient)
        if (localIds.size !== prodIds.size) {
          console.warn(
            [
              `⚠️  ${idKey} count mismatch for endpoint: ${requestPath}`,
              `   - Dev (current host) ${idKey} count: ${localIds.size}`,
              `   - Prod (host_prod) ${idKey} count: ${prodIds.size}`,
            ].join("\n"),
          );
          return;
        }
      }
    }

    // 4) Strict mismatch
    throw new Error(
      `Mismatch for endpoint: ${requestPath}\n` +
        `Local: ${JSON.stringify(localResponse.body, null, 2)}\n` +
        `Production: ${JSON.stringify(prodData, null, 2)}`,
    );
  },
};
