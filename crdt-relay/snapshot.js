const http = require('http');
const { docs } = require('./docs');

const SNAPSHOT_PORT = process.env.SNAPSHOT_PORT || 1235;

function textForRoom(room) {
  const doc = docs.get(room);
  if (!doc) {
    return '';
  }
  const ytext = doc.getText('content');
  return ytext.toString();
}

const server = http.createServer((req, res) => {
  const match = req.url.match(/^\/snapshot\/([^/?]+)/);
  if (!match) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
    return;
  }
  const room = decodeURIComponent(match[1]);
  const text = textForRoom(room);
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ text }));
});

server.listen(SNAPSHOT_PORT, () => {
  console.log(`crdt-relay snapshot server listening on port ${SNAPSHOT_PORT}`);
});

module.exports = { server, textForRoom };
