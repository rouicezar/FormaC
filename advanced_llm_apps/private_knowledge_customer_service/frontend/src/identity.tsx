import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type IdentityKind = "anonymous" | "external" | "internal";

type IdentityProfile = {
  kind: IdentityKind;
  displayName: string;
  feishuBound: boolean;
  requesterId: string;
  feishuUserId: string | null;
};

type IdentityContextValue = IdentityProfile & {
  visibleScope: "公开知识" | "公开与敏感知识";
  updateFromProfile: (profile: { role: IdentityKind | "anonymous"; display_name: string; feishu_bound: boolean; feishu_user_id: string | null }) => void;
  resetAnonymous: () => void;
};

const STORAGE_KEY = "coreknowledge.identity";
const REQUESTER_KEY = "coreknowledge.requester_id";

function loadRequesterId() {
  try {
    const saved = window.localStorage.getItem(REQUESTER_KEY);
    if (saved) return saved;
    const generated = `web-${crypto.randomUUID()}`;
    window.localStorage.setItem(REQUESTER_KEY, generated);
    return generated;
  } catch {
    return "web-anonymous";
  }
}

const anonymousProfile: IdentityProfile = {
  kind: "anonymous",
  displayName: "访客",
  feishuBound: false,
  requesterId: "web-anonymous",
  feishuUserId: null,
};

const IdentityContext = createContext<IdentityContextValue | null>(null);

function loadProfile(): IdentityProfile {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return anonymousProfile;
    const saved = JSON.parse(raw) as Partial<IdentityProfile>;
    if (saved.kind !== "external" && saved.kind !== "internal") return anonymousProfile;
    return {
      kind: saved.kind,
      displayName: saved.displayName || (saved.kind === "internal" ? "内部员工" : "外部用户"),
      feishuBound: Boolean(saved.feishuBound),
      requesterId: saved.requesterId || loadRequesterId(),
      feishuUserId: saved.feishuUserId || null,
    };
  } catch {
    return anonymousProfile;
  }
}

export function IdentityProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<IdentityProfile>(() => {
    const loaded = loadProfile();
    return loaded.kind === "anonymous" ? { ...loaded, requesterId: loadRequesterId() } : loaded;
  });

  useEffect(() => {
    if (profile.kind === "anonymous") {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  }, [profile]);

  const value = useMemo<IdentityContextValue>(() => ({
    ...profile,
    visibleScope: profile.kind === "internal" ? "公开与敏感知识" : "公开知识",
    updateFromProfile: (serverProfile) => setProfile({
      kind: serverProfile.role === "internal" ? "internal" : serverProfile.feishu_bound ? "external" : "anonymous",
      displayName: serverProfile.display_name,
      feishuBound: serverProfile.feishu_bound,
      requesterId: profile.requesterId,
      feishuUserId: serverProfile.feishu_user_id,
    }),
    resetAnonymous: () => setProfile({ ...anonymousProfile, requesterId: profile.requesterId }),
  }), [profile]);

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}

export function useIdentity() {
  const context = useContext(IdentityContext);
  if (!context) throw new Error("useIdentity 必须在 IdentityProvider 中使用");
  return context;
}

export const identityLabels: Record<IdentityKind, string> = {
  anonymous: "匿名访客",
  external: "外部用户",
  internal: "内部员工",
};
