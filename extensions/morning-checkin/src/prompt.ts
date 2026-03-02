import type { MorningCheckinConfig } from "./config.js";

/**
 * Build the agent-turn prompt for the morning check-in cron job.
 *
 * The agent will:
 * 1. Call the user via voice_call in conversation mode
 * 2. Conduct a morning briefing / planning conversation
 * 3. After the call, write a cleaned markdown note to the Obsidian vault
 * 4. Optionally git commit+push the vault
 */
export function buildCheckinPrompt(config: MorningCheckinConfig, dateStr: string): string {
  const custom = config.briefingPrompt;
  const vaultInstruction = config.vaultPath ? buildVaultInstruction(config, dateStr) : "";

  const callTarget = config.toNumber
    ? `Call the user at ${config.toNumber}.`
    : "Call the user at the default configured number.";

  const timeLimit = `Keep the call under ${config.maxCallDurationMin} minutes.`;

  return `You are conducting a morning check-in call. Today is ${dateStr}.

## Step 1: Make the call

Use the voice_call tool to initiate a call in "conversation" mode.
${callTarget}

Your opening message should be a warm, brief greeting and then a concise morning briefing.
${custom ? `\nCustom briefing instructions: ${custom}` : ""}

## Step 2: Have the conversation

Have a focused conversation about the user's day:
- What are the priorities and tasks for today?
- Are there any blockers or things they need help with?
- Any follow-ups from yesterday?
- Any decisions that need to be made?

Be conversational and natural. Listen actively. Ask follow-up questions.
Use continue_call to keep the conversation going (speak, then listen for their response).
${timeLimit}

When the conversation feels complete, summarize the key points, confirm action items,
and say goodbye. Then use end_call to hang up.

## Step 3: Write the daily note
${vaultInstruction || `
After the call ends, output a structured summary of the conversation as your final response.
Format it as a clean daily note with these sections:

# Daily Check-in — ${dateStr}

## Summary
(2-3 sentence overview of the conversation)

## Action Items
- [ ] (each action item as a checkbox)

## Decisions Made
- (any decisions reached)

## Notes
- (any other important points discussed)

## Raw Highlights
(key quotes or moments from the conversation)
`}`;
}

function buildVaultInstruction(config: MorningCheckinConfig, dateStr: string): string {
  const vaultDir = config.vaultPath!;
  const subdir = config.vaultSubdir;
  const notePath = `${vaultDir}/${subdir}/${dateStr}.md`;
  const gitSync = config.gitSync;

  return `
After the call ends, write a structured daily note to the Obsidian vault.

File path: ${notePath}
Create the directory if it doesn't exist.

Format the note as clean markdown:

---
date: ${dateStr}
type: morning-checkin
---

# Daily Check-in — ${dateStr}

## Summary
(2-3 sentence overview of the conversation)

## Action Items
- [ ] (each action item as a checkbox)

## Decisions Made
- (any decisions reached during the call)

## Notes
- (any other important points discussed)

## Raw Highlights
(key quotes or moments from the conversation)

Write this file using the bash tool (mkdir -p for the directory, then write the file).
${gitSync ? `\nAfter writing the file, sync the vault:\n\`\`\`bash\ncd "${vaultDir}" && git add "${subdir}/${dateStr}.md" && git commit -m "checkin: ${dateStr}" && git push\n\`\`\`` : ""}`;
}
