/** Decode platform and application failures without exposing raw provider responses. */
/** @param {Response} response @returns {Promise<object>} */
export async function decodeMcpResponse(response) {
  if (response.status === 401 || response.status === 403) throw new Error('Sign in with ChatGPT using the account granted access to this Site. If access is still denied, contact the Site owner; your input is preserved.');
  if (!response.ok) throw new Error(`The request failed (${response.status}). Your input is preserved; try again later.`);
  let body;
  try { body = await response.json(); } catch { throw new Error('The service returned an invalid response. Your input is preserved; try again later.'); }
  if (body?.error || body?.result?.isError) throw new Error(body.error?.message || body.result?.content?.[0]?.text || 'Request failed');
  if (!body?.result || !Object.hasOwn(body.result, 'structuredContent')) throw new Error('Missing tool result');
  return body.result.structuredContent;
}
