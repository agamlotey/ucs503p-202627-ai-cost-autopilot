/**
 * Talks to the AI Cost Autopilot gateway.
 *
 * Paths are relative: in dev, Vite proxies /stats and /v1 to the gateway
 * (see vite.config.ts), so the browser sees everything as same-origin.
 */

export type Outcome = 'cache' | 'trim' | 'forward';

export interface RecentEntry {
  time: string;
  model: string;
  preview: string;
  baseline: number;
  sent: number;
  saved: number;
  outcome: Outcome;
}

export interface Stats {
  requests: number;
  cache_hits: number;
  hit_rate: number;
  trimmed: number;
  baseline_tokens: number;
  sent_tokens: number;
  saved_tokens: number;
  reduction: number;
  saved_usd: number;
  recent: RecentEntry[];
}

export const emptyStats: Stats = {
  requests: 0,
  cache_hits: 0,
  hit_rate: 0,
  trimmed: 0,
  baseline_tokens: 0,
  sent_tokens: 0,
  saved_tokens: 0,
  reduction: 0,
  saved_usd: 0,
  recent: [],
};

export async function fetchStats(): Promise<Stats> {
  const r = await fetch('/stats', { cache: 'no-store' });
  if (!r.ok) throw new Error(`stats ${r.status}`);
  return r.json();
}

export async function resetStats(): Promise<void> {
  await fetch('/stats/reset', { method: 'POST' });
}

export interface PromptResult {
  answer: string;
  ms: number;
  last?: RecentEntry; // what the gateway recorded for this request
}

/** Send a prompt through the gateway and report what happened to it. */
export async function sendPrompt(content: string, model = 'gpt-4o-mini'): Promise<PromptResult> {
  const t0 = performance.now();
  const r = await fetch('/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages: [{ role: 'user', content }] }),
  });
  const j = await r.json();
  const ms = Math.round(performance.now() - t0);
  const answer: string = j?.choices?.[0]?.message?.content ?? JSON.stringify(j, null, 2);
  // the gateway records every request; recent[0] is this one
  let last: RecentEntry | undefined;
  try {
    last = (await fetchStats()).recent[0];
  } catch {
    /* stats unavailable — still return the answer */
  }
  return { answer, ms, last };
}

export const outcomeLabel: Record<Outcome, string> = {
  cache: 'cache hit',
  trim: 'trimmed',
  forward: 'forwarded',
};
