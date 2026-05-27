import type { AnalysisPayload, ChatMessage } from "./types";

/** Base URL for API (empty = same origin / Vite proxy in dev). */
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

const apiUrl = (path: string) => `${API_BASE}${path}`;

const qs = (shoebox: string) => `shoebox=${encodeURIComponent(shoebox)}`;

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth(): Promise<{ status: string }> {
  return handle(await fetch(apiUrl("/api/health")));
}

export async function fetchConfig(): Promise<{ default_shoebox: string }> {
  return handle(await fetch(apiUrl("/api/config")));
}

export async function fetchSummary(shoebox: string) {
  return handle<{ receipts: number; statements: number; invoices: number; file_count: number }>(
    await fetch(apiUrl(`/api/shoebox/summary?${qs(shoebox)}`))
  );
}

export async function fetchAnalysis(shoebox: string, force = false): Promise<AnalysisPayload> {
  return handle(await fetch(apiUrl(`/api/analysis?${qs(shoebox)}&force=${force}`)));
}

export async function refreshAnalysis(shoebox: string): Promise<AnalysisPayload> {
  return handle(await fetch(apiUrl(`/api/analysis/refresh?${qs(shoebox)}`), { method: "POST" }));
}

export async function sendChat(
  shoebox: string,
  message: string,
  history: ChatMessage[]
): Promise<{ reply: string }> {
  return handle(
    await fetch(apiUrl(`/api/chat?${qs(shoebox)}`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    })
  );
}

export function receiptImageUrl(shoebox: string, filename: string): string {
  return apiUrl(`/api/receipts/${encodeURIComponent(filename)}?${qs(shoebox)}`);
}

export async function uploadReceipts(shoebox: string, files: FileList) {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append("files", f));
  return handle<{ saved: string[] }>(
    await fetch(apiUrl(`/api/upload/receipts?${qs(shoebox)}`), { method: "POST", body: fd })
  );
}

export async function uploadStatement(shoebox: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return handle(await fetch(apiUrl(`/api/upload/statement?${qs(shoebox)}`), { method: "POST", body: fd }));
}

export async function uploadInvoices(shoebox: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return handle(await fetch(apiUrl(`/api/upload/invoices?${qs(shoebox)}`), { method: "POST", body: fd }));
}

export async function uploadNotes(shoebox: string, text: string, file?: File | null) {
  const fd = new FormData();
  fd.append("text", text);
  if (file) fd.append("file", file);
  return handle(await fetch(apiUrl(`/api/upload/notes?${qs(shoebox)}`), { method: "POST", body: fd }));
}

export async function exportPdf(shoebox: string): Promise<Blob> {
  const res = await fetch(apiUrl(`/api/export/pdf?${qs(shoebox)}`), { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Export failed");
  }
  return res.blob();
}
