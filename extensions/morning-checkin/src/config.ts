export type MorningCheckinConfig = {
  enabled: boolean;
  /** 24h time string, e.g. "08:00" */
  time: string;
  /** IANA timezone, e.g. "America/New_York" */
  tz: string;
  /** Phone number to call (E.164) */
  toNumber?: string;
  /** Absolute path to Obsidian vault git repo */
  vaultPath?: string;
  /** Subdirectory inside vault for daily check-in notes */
  vaultSubdir: string;
  /** Auto git commit+push after writing notes */
  gitSync: boolean;
  /** Custom system prompt for the morning briefing agent turn */
  briefingPrompt?: string;
  /** Max call duration in minutes (safety cap) */
  maxCallDurationMin: number;
};

const DEFAULTS: MorningCheckinConfig = {
  enabled: true,
  time: "08:00",
  tz: "UTC",
  vaultSubdir: "daily-checkins",
  gitSync: true,
  maxCallDurationMin: 15,
};

export function parseConfig(raw: unknown): MorningCheckinConfig {
  const obj =
    raw && typeof raw === "object" && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};

  return {
    enabled: typeof obj.enabled === "boolean" ? obj.enabled : DEFAULTS.enabled,
    time: typeof obj.time === "string" && obj.time.trim() ? obj.time.trim() : DEFAULTS.time,
    tz: typeof obj.tz === "string" && obj.tz.trim() ? obj.tz.trim() : DEFAULTS.tz,
    toNumber: typeof obj.toNumber === "string" && obj.toNumber.trim() ? obj.toNumber.trim() : undefined,
    vaultPath: typeof obj.vaultPath === "string" && obj.vaultPath.trim() ? obj.vaultPath.trim() : undefined,
    vaultSubdir:
      typeof obj.vaultSubdir === "string" && obj.vaultSubdir.trim()
        ? obj.vaultSubdir.trim()
        : DEFAULTS.vaultSubdir,
    gitSync: typeof obj.gitSync === "boolean" ? obj.gitSync : DEFAULTS.gitSync,
    briefingPrompt:
      typeof obj.briefingPrompt === "string" && obj.briefingPrompt.trim()
        ? obj.briefingPrompt.trim()
        : undefined,
    maxCallDurationMin:
      typeof obj.maxCallDurationMin === "number" &&
      Number.isFinite(obj.maxCallDurationMin) &&
      obj.maxCallDurationMin >= 1
        ? Math.min(Math.floor(obj.maxCallDurationMin), 60)
        : DEFAULTS.maxCallDurationMin,
  };
}
