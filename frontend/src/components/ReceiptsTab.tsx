import { receiptImageUrl } from "../api";
import type { Receipt } from "../types";
import { fmtMoney } from "../utils";

type Props = { receipts: Receipt[]; shoebox: string };

function badge(row: Receipt) {
  const merchant = row.merchant_raw || "Unknown merchant";
  const amt = row.amount;
  const isError = String(row.ocr_mode || "").toLowerCase() === "error";
  if (isError) return <span className="badge badge-err">Failed</span>;
  if (row.confidence === "low" || merchant === "Unknown merchant" || amt == null)
    return <span className="badge badge-warn">Low confidence</span>;
  return <span className="badge badge-ok">Parsed</span>;
}

export function ReceiptsTab({ receipts, shoebox }: Props) {
  if (!receipts.length) {
    return <p className="caption">No receipts yet — upload images in the sidebar.</p>;
  }

  return (
    <div className="receipt-grid">
      {receipts.map((row, i) => {
        const file = row.source_file || "";
        const src = file ? receiptImageUrl(shoebox, file) : "";
        return (
          <div key={i} className="receipt-card">
            {src && <img src={src} alt={file} loading="lazy" />}
            <div className="receipt-body">
              <strong>
                {row.merchant_raw || "Unknown merchant"}
                {badge(row)}
              </strong>
              <div className="caption" style={{ margin: "0.35rem 0 0" }}>
                {row.date_raw || "—"} · {fmtMoney(row.amount != null ? Number(row.amount) : null)}{" "}
                {row.currency || "CAD"}
              </div>
              {row.notes && !String(row.notes).startsWith("ERROR") && (
                <p className="caption">{String(row.notes).slice(0, 200)}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
