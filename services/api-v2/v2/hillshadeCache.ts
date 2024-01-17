"use strict";

const redis = require("redis");

const client = redis.createClient(6379, "127.0.0.1", { return_buffers: true });
function removeMember(member) {
  client.zrem("hillshades", member, (error) => {
    if (error) console.log(error);
  });
}

module.exports = {
  /*
     * @input:
        coord - [lng, lat]
        aspect - 'small' or 'big'
        callback

       @output
        buffer or null
    */
  get: (coord, aspect, callback) => {
    let radius = aspect === "big" ? 4 : 1;
    client.georadius(
      "hillshades",
      coord[0],
      coord[1],
      radius,
      "mi",
      "ASC",
      (error, results) => {
        if (error) return callback(error);
        if (!results || !results.length) return callback(null, null);
        let img = "";

        for (let i = 0; i < results.length; i++) {
          let key = results[i].toString();
          if (key.split("|")[0] === aspect) {
            img = key.split("|")[1];
            break;
          }
        }

        if (img.length) {
          client.get(img, (error, buffer) => {
            if (error) return callback(error);
            if (!buffer) {
              removeMember(img);
              return callback(null, null);
            }
            callback(null, buffer);
          });
        } else {
          callback(null, null);
        }
      },
    );
  },

  set: (coord, aspect, hash, buffer) => {
    client.geoadd(
      "hillshades",
      coord[0],
      coord[1],
      `${aspect}|${hash}`,
      (error) => {
        if (error) {
          console.log(error);
          return;
        }

        client.set(hash, buffer, (error) => {
          if (error) {
            console.log(error);
            return;
          }
        });
      },
    );
  },
};
