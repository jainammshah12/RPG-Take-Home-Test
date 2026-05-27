import type { Transaction } from "../types";
import { fmtMoney } from "../utils";

type Props = { transactions: Transaction[] };

export function TransactionsTab({ transactions }: Props) {
  return (
    <div>
      <h2 className="section-title">All transactions</h2>
      <p className="caption">Unified ledger across statements, invoices, receipts, and notes.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Merchant</th>
              <th>Status</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Currency</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((row, i) => (
              <tr key={i}>
                <td>{row.date || "—"}</td>
                <td>{row.merchant || "—"}</td>
                <td>
                  <span className={`status-pill status-${(row.status || "unknown").toLowerCase()}`}>
                    {row.status || "Unknown"}
                  </span>
                </td>
                <td>{row.category || "—"}</td>
                <td>{row.amount != null ? fmtMoney(Number(row.amount)) : "—"}</td>
                <td>{row.currency || "—"}</td>
                <td>{row.source || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
