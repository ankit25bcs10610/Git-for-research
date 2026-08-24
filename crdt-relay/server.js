const http = require('http')

const PORT = process.env.PORT || 1234

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ status: 'ok' }))
})

server.listen(PORT, () => {
  console.log(`crdt-relay listening on port ${PORT}`)
})

module.exports = server
