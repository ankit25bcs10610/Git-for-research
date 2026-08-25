const http = require('http');
const WebSocket = require('ws');
const { setupWSConnection } = require('y-websocket/bin/utils');

const PORT = process.env.PORT || 1234;

const server = http.createServer((request, response) => {
  response.writeHead(200, { 'Content-Type': 'text/plain' });
  response.end('crdt-relay ok');
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (conn, req) => {
  setupWSConnection(conn, req);
});

server.listen(PORT, () => {
  console.log(`crdt-relay websocket server listening on port ${PORT}`);
});

// The snapshot HTTP server (reads live Yjs doc text back out for the
// versioning bridge) is a separate module but must run in this same
// process so it shares the in-memory `docs` map the websocket connections
// populate -- a second process would see an empty map.
require('./snapshot');

module.exports = { server, wss };
