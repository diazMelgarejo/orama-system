/** Decode platform and application failures without exposing raw provider responses. */
const SIGN_IN = 'Sign in with ChatGPT using the account granted access to this Site. If access is still denied, contact the Site owner; your input is preserved.';

/** The Site's own JSON-RPC error text, only when the body is a well-formed envelope. @param {Response} response @returns {Promise<string|null>} */
async function envelopeMessage(response) {
  try {
    const body = await response.json();
    const message = body?.jsonrpc === '2.0' ? body.error?.message : null;
    return typeof message === 'string' && message.length > 0 && message.length <= 200 ? message : null;
  } catch { return null; }
}

/** Return structured tool output or a bounded actionable error without raw provider text. @param {Response} response @returns {Promise<object>} */
export async function decodeMcpResponse(response) {
  if (response.status === 401) throw new Error(SIGN_IN);
  if (!response.ok) {
    const own = await envelopeMessage(response);
    if (own) throw new Error(`${own} Your input is preserved.`);
    throw new Error(response.status === 403 ? SIGN_IN : `The request failed (${response.status}). Your input is preserved; try again later.`);
  }
  let body;
  try { body = await response.json(); } catch { throw new Error('The service returned an invalid response. Your input is preserved; try again later.'); }
  if (body?.error || body?.result?.isError) throw new Error(body.error?.message || body.result?.content?.[0]?.text || 'Request failed');
  if (!body?.result || !Object.hasOwn(body.result, 'structuredContent')) throw new Error('Missing tool result');
  return body.result.structuredContent;
}
