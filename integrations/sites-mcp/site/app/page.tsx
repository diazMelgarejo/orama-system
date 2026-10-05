"use client";
import { useEffect, useState } from 'react';

type RecordItem = { id: string; original_preview: string; created_at: string; mode: string };
type Input = { original: string; role: string; goal: string; constraints: string; output_format: string };

async function call<T>(name: string, args: object): Promise<T> {
  const response = await fetch('/mcp', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: crypto.randomUUID(), method: 'tools/call', params: { name, arguments: args } }) });
  const body = await response.json() as { error?: { message: string }; result?: { isError?: boolean; content?: { text: string }[]; structuredContent: T } };
  if (!response.ok || body.error || body.result?.isError) throw new Error(body.error?.message || body.result?.content?.[0]?.text || 'Request failed');
  if (!body.result) throw new Error('Missing tool result');
  return body.result.structuredContent;
}

export default function Page() {
  const [input, setInput] = useState<Input>({ original: '', role: '', goal: '', constraints: '', output_format: '' });
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [output, setOutput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [retry, setRetry] = useState<{ key: string; input: string } | null>(null);
  async function load(before = '') {
    const result = await call<{ items: RecordItem[]; next_cursor: string | null }>('prompts_list', { limit: 20, before });
    setRecords(previous => before ? [...previous, ...result.items] : result.items);
    setCursor(result.next_cursor);
  }
  useEffect(() => {
    let active = true;
    call<{ items: RecordItem[]; next_cursor: string | null }>('prompts_list', { limit: 20 }).then(result => {
      if (active) { setRecords(result.items); setCursor(result.next_cursor); }
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  async function submit(save: boolean) {
    setBusy(true); setError(''); setNotice('');
    try {
      const serialized = JSON.stringify(input);
      const key = retry?.input === serialized ? retry.key : crypto.randomUUID();
      if (save) setRetry({ key, input: serialized });
      const result = await call<{ improved: string }>(save ? 'prompts_save' : 'oramasys_prepare_prompt', save ? { ...input, request_key: key } : input);
      setOutput(result.improved);
      if (save) { setRetry(null); await load(); setNotice('Original and structured prompt saved.'); }
    } catch (e) { setError(e instanceof Error ? e.message : 'Unavailable. Your input is preserved.'); }
    finally { setBusy(false); }
  }
  async function read(id: string) {
    setError('');
    try {
      const record = await call<{ improved: string } | { record: null }>('prompts_get', { id });
      if (!('improved' in record)) throw new Error('Record unavailable');
      setOutput(record.improved);
    } catch (e) { setError(e instanceof Error ? e.message : 'Read failed'); }
  }
  async function archive(id: string) {
    if (!window.confirm('Archive this prompt? Its original and structured text will remain stored.')) return;
    setError('');
    try { await call('prompts_archive', { id }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Archive failed'); }
  }
  return <main>
    <header><div><span className="eyebrow">ORAMASYS / PROMPT WORKSPACE</span><h1>Give your prompt a clear contract.</h1></div><a className="signin" href="/signin-with-chatgpt?return_to=%2F">Sign in with ChatGPT</a></header>
    <p className="intro">Keep your original. Define the role, goal, constraints, and result you want. This workspace structures prompts; it does not run a model.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="notice">{notice}</p>}
    <div className="workspace">
      <section className="editor"><h2>Original input</h2><label className="sr-only" htmlFor="original">Original prompt</label><textarea id="original" rows={8} value={input.original} placeholder="What do you need to accomplish?" onChange={e => setInput({ ...input, original: e.target.value })} />
        <div className="fields">{([['role', 'Role / context'], ['goal', 'Goal / task'], ['constraints', 'Constraints'], ['output_format', 'Output format']] as const).map(([key, label]) => <label key={key}>{label}<textarea rows={2} value={input[key]} onChange={e => setInput({ ...input, [key]: e.target.value })} placeholder="Optional; a visible default is used if blank" /></label>)}</div>
        <div className="actions"><button disabled={busy || !input.original.trim()} onClick={() => submit(false)}>Preview contract</button><button className="primary" disabled={busy || !input.original.trim()} onClick={() => submit(true)}>{busy ? 'Working…' : 'Structure & save'}</button></div>
      </section>
      <section className="result"><div className="section-head"><h2>Structured prompt</h2><button disabled={!output} onClick={() => navigator.clipboard.writeText(output).then(() => setNotice('Copied.')).catch(() => setError('Could not copy. Select the text instead.'))}>Copy</button></div>{output ? <pre>{output}</pre> : <div className="empty"><span>01</span><p>Your role, goal, constraints, and output format will appear here.</p><small>No inference cost. No external provider calls.</small></div>}</section>
    </div>
    <section className="history"><div className="section-head"><h2>Saved prompts</h2><span>Private to your account</span></div>{records.length === 0 ? <p>No active saved prompts. Sign in and save your first contract.</p> : <div className="records">{records.map(record => <article key={record.id}><time>{new Date(record.created_at).toLocaleString()}</time><p>{record.original_preview}</p><div><button onClick={() => read(record.id)}>Read contract</button><button onClick={() => archive(record.id)}>Archive</button></div></article>)}</div>}{cursor && <button onClick={() => load(cursor).catch(e => setError(e.message))}>Load more</button>}</section>
    <footer><span>Powered by the v1 prompt contract, not the local agent runtime.</span><nav><a href="https://github.com/diazMelgarejo/Perpetua-Tools">Perpetua-Tools</a><a href="https://github.com/diazMelgarejo/orama-system">orama-system</a></nav></footer>
  </main>;
}
