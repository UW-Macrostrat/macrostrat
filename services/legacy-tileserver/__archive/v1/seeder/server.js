const express = require('express')
const credentials = require('../credentials')
const app = express()


const compileStyles = require('./etc/convert')

console.log('Preparing mapnik styles...')
compileStyles(() => {
  const tileServer = require('./tileserver')
  app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*')
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
    res.header('Access-Control-Allow-Methods', 'GET')
    next()
  })
  app.use((req, res, next) => {
    if (!req.query || !req.query.secret || req.query.secret != credentials.secret) {
      res.status(401)
      return res.json({'message': 'access denied'})
    }
    next()
  })

  app.use(tileServer)

  app.port = process.argv[2] || 8675

  app.start = () => {
    app.listen(app.port, () => {
      console.log(`Tile seeder listening on port ${app.port}`)
    })
  }

  if (!module.parent) {
    app.start()
  }
})



module.exports = app
