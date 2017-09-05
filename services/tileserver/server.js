'use strict'

const express = require('express')
const app = express()
const tileServer = require('./tileserver')

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*')
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
  res.header('Access-Control-Allow-Methods', 'GET')
  next()
})

app.use(tileServer)
.route('/')
  .get((req, res, next) => {
    res.sendFile(`${__dirname}/pages/main/index.html`)
  })
app.route("/vector")
  .get(function(req, res, next) {
    res.sendFile(__dirname + "/leaflet-starter/vector_simple.html");
  });


app.port = process.argv[2] || 5555

app.start = function() {
  app.listen(app.port, function() {
    console.log(`Listening on port ${app.port}`)
  })
}

if (!module.parent) {
  app.start()
}

module.exports = app
