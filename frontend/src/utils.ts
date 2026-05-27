const CATEGORY_LABELS: Record<string, string> = {
  SOFTWARE: "Software",
  TRAVEL: "Travel",
  MEALS_AND_ENTERTAINMENT: "Meals & Entertainment",
  OFFICE_SUPPLIES: "Office Supplies",
  PROFESSIONAL_SERVICES: "Professional Services",
  EQUIPMENT: "Equipment",
  SUBSCRIPTIONS: "Subscriptions",
  BANKING_AND_FEES: "Banking & Fees",
  CLIENT_EXPENSES: "Client Expenses",
  UTILITIES: "Utilities",
  OTHER: "Other",
  UNKNOWN: "Unknown",
};

export function categoryLabel(cat: string): string {
  return CATEGORY_LABELS[cat] || cat.replace(/_/g, " ");
}

export function fmtMoney(n: number | undefined | null, signed = false): string {
  if (n == null || Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  const s = `$${abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (!signed) return s;
  return n >= 0 ? `+${s}` : `-${s}`;
}

export function periodLabel(monthly: { month: string }[]): string {
  if (!monthly.length) return "All periods";
  if (monthly.length === 1) return monthly[0].month;
  return `${monthly[0].month} → ${monthly[monthly.length - 1].month}`;
}

/** Primary name before em-dash / double-dash description (invoice line items). */
export function primaryEntityName(full: string): string {
  const trimmed = full.trim();
  const parts = trimmed.split(/\s*[—–]\s*|\s+--\s+/);
  return (parts[0] || trimmed).trim();
}

/** Short label for chart Y-axis; full string goes in tooltip. */
export function chartAxisLabel(full: string, maxLen = 32): string {
  const name = primaryEntityName(full);
  if (name.length <= maxLen) return name;
  return `${name.slice(0, maxLen - 1)}…`;
}

export function chartBarHeight(rowCount: number, perRow = 40, min = 200): number {
  return Math.max(min, rowCount * perRow);
}

export function chartLeftMargin(labels: string[], base = 24, perChar = 6.5, max = 220): number {
  const longest = labels.reduce((m, s) => Math.max(m, s.length), 0);
  return Math.min(max, Math.max(base, Math.ceil(longest * perChar)));
}

/** User-friendly chat error (never show raw API dumps). */
export function formatChatError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  const lower = raw.toLowerCase();
  if (lower.includes("429") || lower.includes("quota") || lower.includes("resource_exhausted")) {
    return "I'm temporarily rate-limited by the Groq API. Please wait a minute and try again, or check your quota at [Groq Console](https://console.groq.com).";
  }
  if (lower.includes("api_key") || lower.includes("groq_api_key")) {
    return "Chat needs a **GROQ_API_KEY** in your `.env` file. Get one at https://console.groq.com/keys";
  }
  if (lower.includes("fetch") || lower.includes("network") || lower.includes("failed to fetch")) {
    return "Couldn't reach the server. Make sure the backend is running on port 8000.";
  }
  if (raw.length > 180) {
    return "Something went wrong while generating a reply. Please try again in a moment.";
  }
  return raw.startsWith("Sorry") ? raw : `Sorry, I couldn't answer that. ${raw}`;
}
