'use strict'

const express = require('express')
const app = express()
const tileServer = require('./tileserver')

// Script to generate Mapnik XML files for dynamic tile generation
const compileStyles = require('./seeder/etc/convert')

// Make sure headers allow tiles to be requested across domains
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*')
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
  res.header('Access-Control-Allow-Methods', 'GET')
  next()
})

app.use(tileServer)

app.route('/')
  .get((req, res, next) => {
    res.sendFile(`${__dirname}/pages/main/index.html`)
  })

app.route('/preview/:layer')
  .get((req, res, next) => {
    res.sendFile(`${__dirname}/pages/preview/index.html`)
  })

app.port = process.argv[2] || 5555

app.start = () => {
  // Compile the Mapnik XML for raster tiless
  compileStyles(() => {
    app.listen(app.port, () => {
      console.log(`Tile server listening on port ${app.port}`)
    })
  })
}

if (!module.parent) {
  app.start()
}

module.exports = app
