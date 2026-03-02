import type { GatewayRequestHandlerOptions, OpenClawPluginApi } from "openclaw/plugin-sdk";
import { parseConfig } from "./src/config.js";
import { buildCheckinPrompt } from "./src/prompt.js";

/** Convert "HH:MM" to a cron expression "M H * * *". */
function timeToCron(time: string): string {
  const [h, m] = time.split(":").map(Number);
  return `${m} ${h} * * *`;
}

function todayDateStr(tz: string): string {
  try {
    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: tz,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return formatter.format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

const CRON_JOB_NAME = "morning-checkin";

const morningCheckinPlugin = {
  id: "morning-checkin",
  name: "Morning Check-in",
  description: "Scheduled morning voice call check-in with Obsidian vault transcript logging.",
  register(api: OpenClawPluginApi) {
    const config = parseConfig(api.pluginConfig);

    // -----------------------------------------------------------------------
    // Gateway RPC: morning-checkin.setup — creates/updates the cron job
    // -----------------------------------------------------------------------
    api.registerGatewayMethod(
      "morning-checkin.setup",
      async ({ respond }: GatewayRequestHandlerOptions) => {
        try {
          if (!config.enabled) {
            respond(false, { error: "morning-checkin plugin is disabled" });
            return;
          }

          const cronExpr = timeToCron(config.time);
          const dateStr = todayDateStr(config.tz);
          const prompt = buildCheckinPrompt(config, dateStr);

          const job = {
            name: CRON_JOB_NAME,
            enabled: true,
            schedule: {
              kind: "cron" as const,
              expr: cronExpr,
              tz: config.tz,
            },
            sessionTarget: "isolated" as const,
            wakeMode: "now" as const,
            payload: {
              kind: "agentTurn" as const,
              message: prompt,
              timeoutSeconds: config.maxCallDurationMin * 60 + 120,
            },
          };

          respond(true, {
            job,
            instructions:
              "Use the cron tool to add this job. " +
              "If a job named 'morning-checkin' already exists, update it instead.",
          });
        } catch (err) {
          respond(false, {
            error: err instanceof Error ? err.message : String(err),
          });
        }
      },
    );

    // -----------------------------------------------------------------------
    // Gateway RPC: morning-checkin.run — trigger a check-in call now
    // -----------------------------------------------------------------------
    api.registerGatewayMethod(
      "morning-checkin.run",
      async ({ respond }: GatewayRequestHandlerOptions) => {
        try {
          if (!config.enabled) {
            respond(false, { error: "morning-checkin plugin is disabled" });
            return;
          }

          const dateStr = todayDateStr(config.tz);
          const prompt = buildCheckinPrompt(config, dateStr);

          respond(true, {
            prompt,
            instructions:
              "Run this prompt as an isolated agent turn now. " +
              "The agent should use the voice_call and cron tools.",
          });
        } catch (err) {
          respond(false, {
            error: err instanceof Error ? err.message : String(err),
          });
        }
      },
    );

    // -----------------------------------------------------------------------
    // Gateway RPC: morning-checkin.config — show current config
    // -----------------------------------------------------------------------
    api.registerGatewayMethod(
      "morning-checkin.config",
      async ({ respond }: GatewayRequestHandlerOptions) => {
        respond(true, {
          enabled: config.enabled,
          time: config.time,
          tz: config.tz,
          toNumber: config.toNumber ? `${config.toNumber.slice(0, 6)}...` : "(default)",
          vaultPath: config.vaultPath ?? "(not configured)",
          vaultSubdir: config.vaultSubdir,
          gitSync: config.gitSync,
          maxCallDurationMin: config.maxCallDurationMin,
          cronExpr: timeToCron(config.time),
          hasBriefingPrompt: Boolean(config.briefingPrompt),
        });
      },
    );

    // -----------------------------------------------------------------------
    // CLI: openclaw morning-checkin [setup|run|config]
    // -----------------------------------------------------------------------
    api.registerCli(
      ({ program }) => {
        const cmd = program
          .command("morning-checkin")
          .description("Morning voice check-in with Obsidian vault sync");

        cmd
          .command("setup")
          .description("Create or update the morning check-in cron job")
          .action(async () => {
            if (!config.enabled) {
              console.log("morning-checkin plugin is disabled.");
              return;
            }

            const cronExpr = timeToCron(config.time);
            const dateStr = todayDateStr(config.tz);
            const prompt = buildCheckinPrompt(config, dateStr);

            console.log("Morning Check-in Configuration:");
            console.log(`  Time:     ${config.time} (${config.tz})`);
            console.log(`  Cron:     ${cronExpr}`);
            console.log(`  Phone:    ${config.toNumber ?? "(uses voice-call default)"}`);
            console.log(`  Vault:    ${config.vaultPath ?? "(not configured)"}`);
            console.log(`  Git sync: ${config.gitSync}`);
            console.log("");
            console.log("To activate, run:");
            console.log(`  openclaw cron add --name "${CRON_JOB_NAME}" \\`);
            console.log(`    --cron "${cronExpr}" --tz "${config.tz}" \\`);
            console.log('    --session-target isolated \\');
            console.log(`    --message '<the generated prompt>'`);
            console.log("");
            console.log("Or use the gateway RPC: morning-checkin.setup");
            console.log("");
            console.log("Generated prompt preview (first 500 chars):");
            console.log(prompt.slice(0, 500));
          });

        cmd
          .command("run")
          .description("Trigger a morning check-in call right now")
          .action(async () => {
            if (!config.enabled) {
              console.log("morning-checkin plugin is disabled.");
              return;
            }

            const dateStr = todayDateStr(config.tz);
            const prompt = buildCheckinPrompt(config, dateStr);

            console.log("Triggering morning check-in...");
            console.log(`Date: ${dateStr}`);
            console.log(`Phone: ${config.toNumber ?? "(uses voice-call default)"}`);
            console.log("");
            console.log(
              "To run manually, use the cron wake command or send this prompt to the agent:",
            );
            console.log("");
            console.log(prompt);
          });

        cmd
          .command("config")
          .description("Show current morning check-in configuration")
          .action(() => {
            console.log("Morning Check-in Config:");
            console.log(`  enabled:           ${config.enabled}`);
            console.log(`  time:              ${config.time}`);
            console.log(`  tz:                ${config.tz}`);
            console.log(`  toNumber:          ${config.toNumber ?? "(not set, uses voice-call default)"}`);
            console.log(`  vaultPath:         ${config.vaultPath ?? "(not configured)"}`);
            console.log(`  vaultSubdir:       ${config.vaultSubdir}`);
            console.log(`  gitSync:           ${config.gitSync}`);
            console.log(`  maxCallDurationMin: ${config.maxCallDurationMin}`);
            console.log(`  briefingPrompt:    ${config.briefingPrompt ? "(custom)" : "(default)"}`);
          });
      },
      { commands: ["morning-checkin"] },
    );
  },
};

export default morningCheckinPlugin;
