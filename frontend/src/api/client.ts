const API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

export interface AgentResponse {
  output: string;
  agent: string;
  iterations: number;
  tokens_used: number;
  metadata: Record<string, unknown>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }

  return (await res.json()) as T;
}

export async function listAgents(): Promise<string[]> {
  const body = await request<{ agents: string[] }>("/agents");
  return body.agents;
}

export async function invokeAgent(
  agent: string,
  input: string,
): Promise<AgentResponse> {
  return request<AgentResponse>(`/agents/${agent}/invoke`, {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}
