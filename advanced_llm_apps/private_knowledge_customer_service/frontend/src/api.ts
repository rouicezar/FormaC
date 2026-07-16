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

export type AdminConfig = {
  knowledge: { root: string | null; public_path: string | null; sensitive_path: string | null };
  models: {
    active_provider: Provider;
    allow_sensitive_cloud: boolean;
    deepseek: { model: string; endpoint: string; api_key_configured: boolean };
    ollama: { model: string; endpoint: string };
  };
  audit_recorded: boolean;
};

export type ScanReport = {
  id: string;
  trigger: string;
  status: string;
  added: number;
  updated: number;
  deleted: number;
  failed: number;
  skipped: number;
  errors: Array<{ path: string; error: string }>;
};

export type ManagedIdentity = {
  id: string; feishu_user_id: string; display_name: string | null;
  role: "external" | "internal"; bound: boolean; added_by: string;
  created_at: string; updated_at: string;
};
export type IdentityList = { total: number; external: number; internal: number; users: ManagedIdentity[] };
export type IdentityAudit = {
  id: string; actor_id: string;
  action: "bind_feishu_identity" | "promote_internal_identity" | "downgrade_external_identity";
  identity_id: string; details: Record<string, string>; created_at: string;
};
export type FeishuConfig = {
  app_id: string | null; app_secret_configured: boolean;
  verification_token_configured: boolean; encrypt_key_configured: boolean;
  callback_path: string; protocol: string[];
};
export type InteractionRecord = {
  id: string; channel: "web" | "feishu"; kind: "search" | "ask";
  requester_id: string; identity: ApiIdentity; query: string; answer: string | null;
  citations: Citation[]; metadata: Record<string, unknown>; created_at: string;
};
export type InteractionRecordList = { total: number; records: InteractionRecord[] };
export type PersonalRecordList = InteractionRecordList & {
  stats: { total: number; search: number; ask: number; web: number; feishu: number; citations: number };
};
export type AppProfile = {
  requester_id: string;
  feishu_user_id: string | null;
  display_name: string;
  role: "anonymous" | "external" | "internal";
  feishu_bound: boolean;
  visible_scope: string;
  records: PersonalRecordList["stats"];
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

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败，请稍后重试。");
  return data as T;
}

export function getAdminConfig() {
  return requestJson<AdminConfig>("/admin/config");
}

export function saveAdminConfig(body: Record<string, unknown>) {
  return requestJson<AdminConfig>("/admin/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function startManualScan() {
  return requestJson<ScanReport>("/admin/scans", { method: "POST" });
}

export function getManagedIdentities() { return requestJson<IdentityList>("/admin/users"); }
export function getIdentityAudits() { return requestJson<IdentityAudit[]>("/admin/users/audits"); }
export function bindFeishuIdentity(feishuUserId: string, displayName: string) {
  return requestJson<ManagedIdentity>("/admin/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feishu_user_id: feishuUserId, display_name: displayName || null }) });
}
export function updateIdentityRole(identityId: string, role: "external" | "internal") {
  return requestJson<{ identity: ManagedIdentity; audit_recorded: boolean }>(`/admin/users/${identityId}/role`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role }) });
}
export function getFeishuConfig() { return requestJson<FeishuConfig>("/admin/feishu/config"); }
export function saveFeishuConfig(body: Record<string, string>) {
  return requestJson<FeishuConfig>("/admin/feishu/config", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}
export function getInteractionRecords(filters: { channel?: string; kind?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.channel) params.set("channel", filters.channel);
  if (filters.kind) params.set("kind", filters.kind);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return requestJson<InteractionRecordList>(`/admin/records${suffix}`);
}

export function getPersonalRecords(requesterId: string, filters: { kind?: string; feishuUserId?: string | null } = {}) {
  const params = new URLSearchParams({ requester_id: requesterId });
  if (filters.feishuUserId) params.set("feishu_user_id", filters.feishuUserId);
  if (filters.kind) params.set("kind", filters.kind);
  return requestJson<PersonalRecordList>(`/app/records?${params.toString()}`);
}

export function getAppProfile(requesterId: string, feishuUserId?: string | null, displayName?: string) {
  const params = new URLSearchParams({ requester_id: requesterId });
  if (feishuUserId) params.set("feishu_user_id", feishuUserId);
  if (displayName) params.set("display_name", displayName);
  return requestJson<AppProfile>(`/app/profile?${params.toString()}`);
}

export function bindAppFeishuProfile(body: { requesterId: string; feishuUserId: string; displayName?: string }) {
  return requestJson<AppProfile>("/app/profile/bind-feishu", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requester_id: body.requesterId,
      feishu_user_id: body.feishuUserId,
      display_name: body.displayName || null,
    }),
  });
}

export function searchOriginals(query: string, identity: ApiIdentity, requesterId: string) {
  return postJson<SearchResponse>("/search", { query, identity, requester_id: requesterId, limit: 10 });
}

export function askKnowledge(question: string, identity: ApiIdentity, provider: Provider, requesterId: string) {
  return postJson<AskResponse>("/ask", {
    question,
    identity,
    provider,
    requester_id: requesterId,
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
