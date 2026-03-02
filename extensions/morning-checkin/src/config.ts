export type MorningCheckinConfig = {
  enabled: boolean;
  /** 24h time string, e.g. "08:00" */
  time: string;
  /** IANA timezone, e.g. "America/New_York" */
  tz: string;
  /** Phone number to call (E.164) */
  toNumber?: string;
  /** Max call duration in minutes (safety cap) */
  maxCallDurationMin: number;
};

const DEFAULTS: MorningCheckinConfig = {
  enabled: true,
  time: "08:00",
  tz: "UTC",
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
    maxCallDurationMin:
      typeof obj.maxCallDurationMin === "number" &&
      Number.isFinite(obj.maxCallDurationMin) &&
      obj.maxCallDurationMin >= 1
        ? Math.min(Math.floor(obj.maxCallDurationMin), 60)
        : DEFAULTS.maxCallDurationMin,
  };
}
