var config = require('./config')
var setup = require('./setup')
var setupVector = require('./setupVector')
var async = require('async')

async.eachLimit(config.layers, 1, function(layer, callback) {
  console.log(layer)
  async.parallel([
    function(cb) {
      setup(layer, function(error) {
        if (error) return cb(error)
        cb(null)
      })
    },

    function(cb) {
      setupVector(layer, function(error) {
        if (error) return cb(error)
        cb(null)
      })
    }
  ], function(error) {
    if (error) return callback(error)
    callback(null)
  })
}, function(error) {
  if (error) console.log(error)

  process.exit(0)
  console.log('Configuration files generated')
})
