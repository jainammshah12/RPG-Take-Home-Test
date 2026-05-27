import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import * as api from "../api";
import type { AnalysisPayload } from "../types";

const mockPayload: AnalysisPayload = {
  analytics: {
    revenue: 3500,
    expenses: 500,
    cash_flow: 3000,
    flags: [],
    monthly: [{ month: "2025-03", cash_flow: 3000 }],
    monthly_card_spend: [{ month: "2025-03", card_spend: 400 }],
    by_source: [{ source: "statement", count: 5, inflow: 0, outflow: 400, net: -400 }],
    top_merchants: [{ merchant: "Staples", spend: 150 }],
    top_revenue_clients: [],
    invoice_status: [{ status: "Paid", count: 1, amount: 3500 }],
    spend_by_category: [{ category: "OFFICE_SUPPLIES", spend: 150 }],
    receipt_count: 2,
    receipt_errors: 0,
    receipt_total_spend: 200,
    statement_tx_count: 5,
    invoice_count: 1,
    invoice_paid_amount: 3500,
    invoice_pending_amount: 0,
  },
  transactions: [
    {
      date: "2025-03-10",
      merchant: "Staples",
      category: "OFFICE_SUPPLIES",
      amount: -45.99,
      currency: "CAD",
      source: "statement",
    },
  ],
  parsed: { receipts: [], statement: [], invoices: [], notes: [] },
  validation: { valid: true, errors: [], warnings: [] },
  chat_context: "test",
  signature: "abc",
  meta: { from_disk: true, parsed_new_files: 0 },
};

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders dashboard KPIs when analysis loads", async () => {
    vi.spyOn(api, "fetchHealth").mockResolvedValue({ status: "ok" });
    vi.spyOn(api, "fetchConfig").mockResolvedValue({ default_shoebox: "C:/shoebox" });
    vi.spyOn(api, "fetchAnalysis").mockResolvedValue(mockPayload);
    vi.spyOn(api, "fetchSummary").mockResolvedValue({
      receipts: 2,
      statements: 1,
      invoices: 1,
      file_count: 5,
    });

    render(<App />);

    await waitFor(
      () => {
        expect(screen.getAllByText("Revenue").length).toBeGreaterThan(0);
        expect(screen.getAllByText("$3,500.00").length).toBeGreaterThan(0);
      },
      { timeout: 3000 }
    );

    expect(screen.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("shows offline message when health check fails", async () => {
    vi.spyOn(api, "fetchHealth").mockRejectedValue(new Error("Network"));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend offline/i)).toBeInTheDocument();
    });
  });
});
