export const API = import.meta.env.VITE_API_URL || "http://localhost:8897";

export type ApiIdentity = "external" | "internal";
export type Provider = "deepseek" | "ollama";

export type Citation = {
  citation: string;
  source: string;
  similarity: number;
  evidence: string;
  partition: "public" | "sensitive";
  locator: Record<string, unknown>;
};

export type SearchResponse = {
  query: string;
  total: number;
  results: Citation[];
};

export type AskResponse = {
  answer: string;
  mode: "generate" | "excerpt_only";
  citations: Citation[];
};

async function postJson<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败，请稍后重试。");
  return data as T;
}

export function searchOriginals(query: string, identity: ApiIdentity) {
  return postJson<SearchResponse>("/search", { query, identity, limit: 10 });
}

export function askKnowledge(question: string, identity: ApiIdentity, provider: Provider, allowSensitiveCloud: boolean) {
  return postJson<AskResponse>("/ask", {
    question,
    identity,
    provider,
    allow_sensitive_cloud: allowSensitiveCloud,
  });
}

export function locationText(locator: Record<string, unknown>) {
  if (locator.page) return `第 ${locator.page} 页`;
  if (locator.sheet) {
    const range = locator.cell_range ? ` · 单元格 ${locator.cell_range}` : "";
    return `工作表 ${locator.sheet}${range}`;
  }
  if (locator.slide) return `第 ${locator.slide} 张幻灯片`;
  if (locator.paragraph) return `第 ${locator.paragraph} 段`;
  if (locator.line_start) {
    const end = locator.line_end && locator.line_end !== locator.line_start ? `–${locator.line_end}` : "";
    return `第 ${locator.line_start}${end} 行`;
  }
  return "文档原文";
}
