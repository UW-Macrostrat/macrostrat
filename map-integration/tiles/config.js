module.exports = {
  // Where to write the cache
  cachePath: __dirname + "/tiles/burwell",
  cachePathVector: __dirname + "/tiles/burwell_vector",

  // Where burwell_scale.xml live
  configPath: "./",

  // The port the tile cache server should run on
  port: 7890,
  redisPort: 6379,

  // All of our burwell scales
  scales: ["tiny", "small", "medium", "large"],

  // The scales that should be precached
  seedScales: ["tiny", "small", "medium"],

  layers: ["vanilla", "emphasized", "lithologies", "structures"],

  // Which zoom levels correspond to which map scales
  scaleMap: {
    "tiny": [0, 1, 2, 3],
    "small": [4, 5],
    "medium": [6, 7, 8, 9],
    "large": [10, 11, 12, 13]
  },

  // The order in which scales should be drawn for each layer
  layerOrder: {
    "tiny": ["tiny"],
    "small": ["tiny", "large", "medium", "small"],
    "medium": ["large", "small", "medium"],
    "large": ["medium", "large"]
    }
}
