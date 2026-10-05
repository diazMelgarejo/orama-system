import { env } from 'cloudflare:workers';
import { handleMcp } from '../lib/server.mjs';

export async function POST(request: Request): Promise<Response> {
  return handleMcp(request, env.DB ?? null);
}
export async function GET(): Promise<Response> {
  return new Response(null, { status: 405, headers: { Allow: 'POST' } });
}
