/** Decode a tool result or reject with a sanitized, actionable transport/application error. */
export function decodeMcpResponse<T>(response: Response): Promise<T>;
