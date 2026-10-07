import test from 'node:test';
import assert from 'node:assert/strict';
import { decodeMcpResponse } from '../site/app/lib/client.mjs';
test('platform authentication denial is actionable even when the body is not JSON', async () => {
  for (const status of [401, 403]) await assert.rejects(decodeMcpResponse(new Response('Unauthorized', { status })), /Sign in with ChatGPT.*access/);
});
test('non-JSON platform failures are sanitized and successful envelopes retain results', async () => {
  await assert.rejects(decodeMcpResponse(new Response('<html>provider secret</html>', { status: 502 })), error => /502/.test(error.message) && !/secret/.test(error.message));
  await assert.rejects(decodeMcpResponse(new Response('not json')), /invalid response/);
  const expected = { original: 'λ\r\n\n', mode: 'structured-contract' };
  assert.deepEqual(await decodeMcpResponse(Response.json({ result: { structuredContent: expected } })), expected);
  await assert.rejects(decodeMcpResponse(Response.json({ result: { isError: true, content: [{ text: 'Validation failed' }] } })), /Validation failed/);
});
test('the Site\'s own JSON-RPC errors stay visible; platform bodies and bare 401s do not leak', async () => {
  /** Build a Site-owned JSON-RPC error response, distinct from a platform denial. */
  const envelope = (status, message) => new Response(JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32001, message } }), { status, headers: { 'content-type': 'application/json' } });
  await assert.rejects(decodeMcpResponse(envelope(413, 'Request too large')), /Request too large.*input is preserved/);
  await assert.rejects(decodeMcpResponse(envelope(403, 'Origin not allowed')), /Origin not allowed/);
  await assert.rejects(decodeMcpResponse(envelope(401, 'Authentication required')), /Sign in with ChatGPT/);
  await assert.rejects(decodeMcpResponse(Response.json({ error: { message: 'provider secret' } }, { status: 500 })), error => /500/.test(error.message) && !/secret/.test(error.message));
  await assert.rejects(decodeMcpResponse(envelope(500, 'x'.repeat(201))), /\(500\)/);
});
