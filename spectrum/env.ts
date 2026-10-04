import { readFileSync } from "node:fs";

/** Same rules as the Python ledger: fill unset vars from .env, do not override the shell. */
export function loadEnv(path = ".env"): void {
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch {
    return;
  }
  for (const line of text.split("\n")) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith("#") || !stripped.includes("=")) continue;
    const eq = stripped.indexOf("=");
    const name = stripped.slice(0, eq).trim();
    const value = stripped.slice(eq + 1).trim().replace(/^['"]|['"]$/g, "");
    if (name && process.env[name] === undefined) process.env[name] = value;
  }
}
