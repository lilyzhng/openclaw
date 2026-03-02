import type { MorningCheckinConfig } from "./config.js";

/**
 * Build the agent-turn prompt for the morning check-in cron job.
 *
 * The agent will:
 * 1. Call the user via voice_call in conversation mode
 * 2. Conduct a morning planning conversation
 * 3. After the call, summarize the conversation in chat
 */
export function buildCheckinPrompt(config: MorningCheckinConfig, dateStr: string): string {
  const callTarget = config.toNumber
    ? `Call the user at ${config.toNumber}.`
    : "Call the user at the default configured number.";

  const timeLimit = `Keep the call under ${config.maxCallDurationMin} minutes.`;

  return `You are conducting a morning check-in call. Today is ${dateStr}.

## Step 1: Make the call

Use the voice_call tool to initiate a call in "conversation" mode.
${callTarget}

Your opening message should be a warm, brief greeting followed by asking about the day ahead.

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

## Step 3: Summarize

After the call ends, post a brief summary in chat with:
- Key priorities discussed
- Action items
- Any decisions made
`;
}
