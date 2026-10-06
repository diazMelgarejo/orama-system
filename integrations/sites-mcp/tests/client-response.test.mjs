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
