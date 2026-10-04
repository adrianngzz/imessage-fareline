/**
 * Local iMessage sees every chat in Messages. Only answer the ones named in
 * FARELINE_SPACE. Cloud iMessage is the agent's own line, so every inbound
 * chat there is in scope. The terminal is always in scope.
 */

const announced = new Set<string>();

export function acceptSpace(platform: string, spaceId: string): boolean {
  if (platform === "terminal") return true;
  if (platform === "imessage") return true;
  if (platform !== "local_imessage") return false;

  const allowed = (process.env.FARELINE_SPACE ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (allowed.includes(spaceId)) return true;

  const key = `${platform}:${spaceId}`;
  if (!announced.has(key)) {
    announced.add(key);
    console.log(
      `Saw local iMessage chat ${spaceId}. Set FARELINE_SPACE to that id before Fareline replies there.`,
    );
  }
  return false;
}

export function resetAnnouncedSpaces(): void {
  announced.clear();
}
