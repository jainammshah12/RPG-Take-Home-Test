import { useCallback, useEffect, useState } from "react";
import { fetchAnalysis, fetchConfig, fetchHealth, fetchSummary } from "./api";
import { AlertsTab } from "./components/AlertsTab";
import { ChatWidget } from "./components/ChatWidget";
import { DashboardTab } from "./components/DashboardTab";
import { ReceiptsTab } from "./components/ReceiptsTab";
import { Sidebar } from "./components/Sidebar";
import { TransactionsTab } from "./components/TransactionsTab";
import type { AnalysisPayload } from "./types";
import { fmtMoney, periodLabel } from "./utils";

type TabId = "dashboard" | "transactions" | "receipts" | "alerts";

export default function App() {
  const [shoebox, setShoebox] = useState("");
  const [data, setData] = useState<AnalysisPayload | null>(null);
  const [tab, setTab] = useState<TabId>("dashboard");
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [summary, setSummary] = useState("");

  const load = useCallback(async () => {
    if (!shoebox) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchAnalysis(shoebox);
      setData(payload);
      const sum = await fetchSummary(shoebox);
      setSummary(
        `${sum.receipts} receipt(s) · ${sum.statements} statement PDF(s) · ${sum.invoices} invoice workbook(s)`
      );
      if (payload.meta.parsed_new_files > 0 && !payload.meta.from_disk) {
        setToast(`Parsed ${payload.meta.parsed_new_files} new or updated file(s).`);
        setTimeout(() => setToast(null), 4000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analysis");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [shoebox]);

  useEffect(() => {
    (async () => {
      try {
        await fetchHealth();
        setApiOnline(true);
        const c = await fetchConfig();
        setShoebox(c.default_shoebox);
      } catch {
        setApiOnline(false);
        setError(
          "Cannot reach the API. Start the backend from the backend folder: uvicorn src.api.main:app --reload --port 8000"
        );
      }
    })();
  }, []);

  useEffect(() => {
    if (shoebox && apiOnline) load();
  }, [shoebox, apiOnline, load]);

  const a = data?.analytics;
  const hasTransactions = (data?.transactions?.length ?? 0) > 0;

  return (
    <div className="layout">
      <Sidebar shoebox={shoebox} onShoeboxChange={setShoebox} onRefresh={load} loading={loading} />

      <main className="main">
        {apiOnline === false && (
          <div className="error-banner">
            Backend offline — run <code>uvicorn src.api.main:app --reload --port 8000</code> from{" "}
            <code>backend/</code>, then refresh this page.
          </div>
        )}

        {toast && <div className="toast">{toast}</div>}
        {loading && !data && apiOnline && (
          <div className="loading-overlay">Loading analysis…</div>
        )}
        {error && apiOnline !== false && <div className="error-banner">{error}</div>}

        {a && data && (
          <>
            <div className="hero">
              <h1>LedgerLens</h1>
              <p>Revenue, spend, and receipt-backed insights · {periodLabel(a.monthly)}</p>
            </div>

            {summary && <p className="caption">Shoebox: {summary}</p>}

            {!hasTransactions && (
              <div className="alert alert-warning">
                No transactions found in this shoebox. Check the data folder path in the sidebar points
                to your <code>shoebox/</code> at the project root.
              </div>
            )}

            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-label">Revenue</div>
                <div className="kpi-value">{fmtMoney(a.revenue)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Expenses</div>
                <div className="kpi-value">{fmtMoney(a.expenses)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Net Cash Flow</div>
                <div className={`kpi-value ${a.cash_flow >= 0 ? "positive" : "negative"}`}>
                  {fmtMoney(a.cash_flow, true)}
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Card transactions</div>
                <div className="kpi-value">{a.statement_tx_count}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Invoices paid</div>
                <div className="kpi-value">{fmtMoney(a.invoice_paid_amount)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Invoices pending</div>
                <div className="kpi-value">{fmtMoney(a.invoice_pending_amount)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Receipt spend</div>
                <div className="kpi-value">{fmtMoney(a.receipt_total_spend)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Alerts</div>
                <div className="kpi-value">{a.flags.length}</div>
              </div>
            </div>

            <nav className="tabs">
              {(
                [
                  ["dashboard", "Dashboard"],
                  ["transactions", "Transactions"],
                  ["receipts", "Receipt gallery"],
                  ["alerts", "Alerts"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  className={`tab ${tab === id ? "active" : ""}`}
                  onClick={() => setTab(id)}
                >
                  {label}
                </button>
              ))}
            </nav>

            {tab === "dashboard" && (
              <DashboardTab
                analytics={a}
                shoebox={shoebox}
                validationValid={data.validation.valid}
              />
            )}
            {tab === "transactions" && <TransactionsTab transactions={data.transactions} />}
            {tab === "receipts" && (
              <ReceiptsTab receipts={data.parsed.receipts} shoebox={shoebox} />
            )}
            {tab === "alerts" && <AlertsTab flags={a.flags} />}
          </>
        )}
      </main>

      {shoebox && apiOnline && <ChatWidget shoebox={shoebox} />}
    </div>
  );
}
