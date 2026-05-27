import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { exportPdf } from "../api";
import type { Analytics } from "../types";
import {
  categoryLabel,
  chartAxisLabel,
  chartBarHeight,
  chartLeftMargin,
  fmtMoney,
  primaryEntityName,
} from "../utils";

type Props = { analytics: Analytics; shoebox: string; validationValid: boolean };

const COLORS = ["#2563eb", "#0ea5e9", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"];

type TooltipPayload = { fullLabel?: string; revenue?: number; spend?: number };

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: TooltipPayload; value?: number }[];
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const val = payload[0].value;
  const full = row?.fullLabel ?? "";
  return (
    <div className="chart-tooltip">
      {full && <div className="chart-tooltip-title">{full}</div>}
      <div className="chart-tooltip-value">{fmtMoney(val)}</div>
    </div>
  );
}

export function DashboardTab({ analytics, shoebox, validationValid }: Props) {
  const a = analytics;

  const cashFlowData = a.monthly.map((r) => ({
    month: r.month,
    cash_flow: r.cash_flow,
    fill: r.cash_flow >= 0 ? "#10b981" : "#ef4444",
  }));

  const categoryData = [...a.spend_by_category]
    .sort((x, y) => y.spend - x.spend)
    .map((r) => ({
      name: categoryLabel(r.category),
      spend: r.spend,
      category: r.category,
      fullLabel: categoryLabel(r.category),
    }));

  const merchants = [...a.top_merchants]
    .sort((x, y) => x.spend - y.spend)
    .map((r) => ({
      ...r,
      label: chartAxisLabel(r.merchant),
      fullLabel: primaryEntityName(r.merchant),
    }));

  const clients = [...a.top_revenue_clients]
    .sort((x, y) => x.revenue - y.revenue)
    .map((r) => ({
      ...r,
      label: chartAxisLabel(r.client),
      fullLabel: r.client,
    }));

  const merchantMargin = chartLeftMargin(merchants.map((m) => m.label));
  const clientMargin = chartLeftMargin(clients.map((c) => c.label), 24, 6.5, 240);
  const categoryMargin = chartLeftMargin(categoryData.map((c) => c.name), 24, 6.5, 200);

  return (
    <div>
      <div className="chart-row">
        <div className="chart-card">
          <h3>Monthly Net Cash Flow</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={cashFlowData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => fmtMoney(v)} />
              <Bar dataKey="cash_flow" radius={[4, 4, 0, 0]}>
                {cashFlowData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-card">
          <h3>Inflows vs Outflows by Source</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={a.by_source}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="source" tickFormatter={(s) => s.charAt(0).toUpperCase() + s.slice(1)} />
              <YAxis />
              <Tooltip formatter={(v: number) => fmtMoney(v)} />
              <Legend />
              <Bar dataKey="inflow" name="Inflow" fill="#10b981" />
              <Bar dataKey="outflow" name="Outflow" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-row-2">
        <div className="chart-card">
          <h3>Monthly Card Spend</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={a.monthly_card_spend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(v: number) => fmtMoney(v)} />
              <Bar dataKey="card_spend" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-card">
          <h3>Invoices by Status</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={a.invoice_status}>
              <XAxis dataKey="status" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                {a.invoice_status.map((row, i) => (
                  <Cell
                    key={i}
                    fill={row.status.toLowerCase() === "paid" ? "#10b981" : "#f59e0b"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-card">
        <h3>Top Merchants (Card Statement)</h3>
        <ResponsiveContainer width="100%" height={chartBarHeight(merchants.length)}>
          <BarChart data={merchants} layout="vertical" margin={{ left: merchantMargin, right: 16, top: 8, bottom: 8 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="label"
              width={merchantMargin - 8}
              tick={{ fontSize: 11, fill: "#475569" }}
              interval={0}
            />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="spend" fill="#2563eb" radius={[0, 4, 4, 0]} barSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h3 className="section-title">Expense categories</h3>
      <p className="caption">
        Rule-based labels from merchant names; ambiguous or unmatched rows stay UNKNOWN.
      </p>
      <div className="chart-card">
        <ResponsiveContainer width="100%" height={chartBarHeight(categoryData.length)}>
          <BarChart
            data={categoryData}
            layout="vertical"
            margin={{ left: categoryMargin, right: 16, top: 8, bottom: 8 }}
          >
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              width={categoryMargin - 8}
              tick={{ fontSize: 11, fill: "#475569" }}
              interval={0}
            />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="spend" radius={[0, 4, 4, 0]} barSize={22}>
              {categoryData.map((row, i) => (
                <Cell
                  key={i}
                  fill={row.category === "UNKNOWN" ? "#94a3b8" : COLORS[i % COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {clients.length > 0 && (
        <div className="chart-card">
          <h3>Revenue by Client</h3>
          <p className="caption">Hover a bar for the full invoice description.</p>
          <ResponsiveContainer width="100%" height={chartBarHeight(clients.length, 44, 220)}>
            <BarChart
              data={clients}
              layout="vertical"
              margin={{ left: clientMargin, right: 16, top: 8, bottom: 8 }}
            >
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="label"
                width={clientMargin - 8}
                tick={{ fontSize: 11, fill: "#475569" }}
                interval={0}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="revenue" fill="#10b981" radius={[0, 4, 4, 0]} barSize={24} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <h3 className="section-title">Export</h3>
      <button
        className="btn btn-primary"
        style={{ maxWidth: 280 }}
        disabled={!validationValid}
        onClick={async () => {
          try {
            const blob = await exportPdf(shoebox);
            const url = URL.createObjectURL(blob);
            const el = document.createElement("a");
            el.href = url;
            el.download = "financial_report.pdf";
            el.click();
            URL.revokeObjectURL(url);
          } catch (e) {
            alert(e instanceof Error ? e.message : "Export failed");
          }
        }}
      >
        Download PDF report
      </button>
      {!validationValid && (
        <p className="caption">Fix validation issues before generating a report.</p>
      )}
    </div>
  );
}
