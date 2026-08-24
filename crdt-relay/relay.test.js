process.env.PORT = '31234';
process.env.SNAPSHOT_PORT = '31235';

const test = require('node:test');
const assert = require('node:assert/strict');
const WebSocket = require('ws');
const Y = require('yjs');
const { WebsocketProvider } = require('y-websocket');

require('./server');
require('./snapshot');

function waitForSync(provider) {
  return new Promise((resolve) => {
    provider.on('sync', (isSynced) => {
      if (isSynced) {
        resolve();
      }
    });
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test('two clients in the same room converge on the same content via CRDT sync', async () => {
  const room = 'artifact-1__main';

  const docA = new Y.Doc();
  const providerA = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docA, {
    WebSocketPolyfill: WebSocket,
  });

  const docB = new Y.Doc();
  const providerB = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docB, {
    WebSocketPolyfill: WebSocket,
  });

  await Promise.all([waitForSync(providerA), waitForSync(providerB)]);

  const textA = docA.getText('content');
  textA.insert(0, 'hello from client A');

  await wait(300);

  const textB = docB.getText('content');
  assert.equal(textB.toString(), 'hello from client A');

  providerA.destroy();
  providerB.destroy();
});

test('the snapshot endpoint returns the current text for a room', async () => {
  const room = 'artifact-2__main';

  const doc = new Y.Doc();
  const provider = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, doc, {
    WebSocketPolyfill: WebSocket,
  });

  await waitForSync(provider);

  const text = doc.getText('content');
  text.insert(0, 'snapshot me');

  await wait(300);

  const response = await fetch(`http://localhost:${process.env.SNAPSHOT_PORT}/snapshot/${room}`);
  const body = await response.json();

  assert.equal(body.text, 'snapshot me');

  provider.destroy();
});
