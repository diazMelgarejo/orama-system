import { apiFetch } from "./client";

export interface KnowledgeHit {
  title: string;
  path: string;
  excerpt: string;
  score: number;
}

export interface KnowledgeSearchResult {
  query: string;
  hits: KnowledgeHit[];
  read_only: true;
}

export const searchKnowledge = (query: string, signal?: AbortSignal) =>
  apiFetch<KnowledgeSearchResult>(`/api/knowledge/search?q=${encodeURIComponent(query)}`, { signal });
