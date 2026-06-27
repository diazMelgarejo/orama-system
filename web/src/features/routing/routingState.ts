export const LMSTUDIO_WIN_ROW_MODEL = "lmstudio-win/qwen3.5-27b-*";

export function selectFallbackChain<T extends { model: string }>(
  chain: readonly T[],
  lmstudioOnline: boolean,
): T[] {
  if (lmstudioOnline) {
    return [...chain];
  }
  return chain.filter((row) => row.model !== LMSTUDIO_WIN_ROW_MODEL);
}
