module.exports = options => {
    return {
        name: 'empties',
        init: (server, callback) => {
            callback()
        },
        reshook: (server, tile, req, res, result, callback) => {
          if (result.buffer.length === 0) {
            result.status = 204
          }
          callback()
        }
    }
}
