const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface VerdictSummary {
  id: string;
  shot_id: string;
  final_status: string;
  has_panel_review: boolean;
  submitted_at: string;
}

export interface VerdictDetail extends VerdictSummary {
  payload: Record<string, unknown>;
}

async function authedFetch<T>(token: string, path: string): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export async function listVerdicts(token: string): Promise<VerdictSummary[]> {
  return (await authedFetch<VerdictSummary[]>(token, "/verdicts")) ?? [];
}

export async function getVerdict(
  token: string,
  id: string,
): Promise<VerdictDetail | null> {
  return await authedFetch<VerdictDetail>(token, `/verdicts/${id}`);
}

export interface AccountInfo {
  id: string;
  email: string;
  verdict_count: number;
}

export async function getAccount(token: string): Promise<AccountInfo | null> {
  return await authedFetch<AccountInfo>(token, "/account");
}
