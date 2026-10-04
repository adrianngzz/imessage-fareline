const ACT_URL = process.env.FARELINE_ACT_URL ?? "http://127.0.0.1:8787/act";

export function ledgerUrl(): string {
  return ACT_URL;
}

export async function act(speaker: string, text: string): Promise<string> {
  const response = await fetch(ACT_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ speaker, text }),
  });
  if (!response.ok) {
    return "The tab rejected that message. Check that the ledger is running.";
  }
  const body = (await response.json()) as { reply?: string };
  return body.reply || "No reply.";
}
