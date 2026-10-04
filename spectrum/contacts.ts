import { readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";

/** Last 10 digits, so +1 (415) 555-0100 matches +14155550100. */
export function phoneKey(value: string): string | undefined {
  const digits = value.replace(/\D/g, "");
  if (digits.length < 10) return undefined;
  return digits.slice(-10);
}

function databases(root: string): string[] {
  const found: string[] = [];
  const top = join(root, "AddressBook-v22.abcddb");
  found.push(top);
  try {
    for (const source of readdirSync(join(root, "Sources"))) {
      found.push(join(root, "Sources", source, "AddressBook-v22.abcddb"));
    }
  } catch {
    // No Contacts sources directory.
  }
  return found;
}

function columns(db: DatabaseSync, table: string): Set<string> {
  const rows = db.prepare(`PRAGMA table_info(${table})`).all() as { name: string }[];
  return new Set(rows.map((row) => row.name));
}

function has(columns: Set<string>, names: string[]): boolean {
  return names.every((name) => columns.has(name));
}

function displayName(first: unknown, last: unknown): string {
  return [first, last]
    .filter((part): part is string => typeof part === "string" && part.trim() !== "")
    .join(" ")
    .trim();
}

/**
 * Name saved in Contacts for this iMessage handle. Messages itself only stores
 * the phone or email; the name on screen comes from Contacts.
 */
export function contactName(handle: string, root = join(homedir(), "Library/Application Support/AddressBook")): string | undefined {
  const email = handle.includes("@") ? handle.trim().toLowerCase() : undefined;
  const phone = email ? undefined : phoneKey(handle);
  if (!email && !phone) return undefined;

  for (const path of databases(root)) {
    let db: DatabaseSync | undefined;
    try {
      db = new DatabaseSync(path, { readOnly: true });
      const record = columns(db, "ZABCDRECORD");
      if (!has(record, ["Z_PK", "ZFIRSTNAME", "ZLASTNAME"])) continue;

      if (email && has(columns(db, "ZABCDEMAILADDRESS"), ["ZOWNER", "ZADDRESS"])) {
        const row = db
          .prepare(
            `SELECT r.ZFIRSTNAME AS first, r.ZLASTNAME AS last
             FROM ZABCDEMAILADDRESS e
             JOIN ZABCDRECORD r ON r.Z_PK = e.ZOWNER
             WHERE lower(e.ZADDRESS) = ?
             LIMIT 1`,
          )
          .get(email) as { first: unknown; last: unknown } | undefined;
        const name = row ? displayName(row.first, row.last) : "";
        if (name) return name;
      }

      if (phone && has(columns(db, "ZABCDPHONENUMBER"), ["ZOWNER", "ZFULLNUMBER"])) {
        const rows = db
          .prepare(
            `SELECT r.ZFIRSTNAME AS first, r.ZLASTNAME AS last, p.ZFULLNUMBER AS phone
             FROM ZABCDPHONENUMBER p
             JOIN ZABCDRECORD r ON r.Z_PK = p.ZOWNER`,
          )
          .all() as { first: unknown; last: unknown; phone: unknown }[];
        for (const row of rows) {
          if (typeof row.phone !== "string" || phoneKey(row.phone) !== phone) continue;
          const name = displayName(row.first, row.last);
          if (name) return name;
        }
      }
    } catch {
      // Contacts is unreadable, or this file is not an address book.
    } finally {
      db?.close();
    }
  }
  return undefined;
}
