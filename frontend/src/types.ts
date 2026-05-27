export type Flag = { level: string; message: string };

export type Analytics = {
  revenue: number;
  expenses: number;
  cash_flow: number;
  flags: Flag[];
  monthly: { month: string; cash_flow: number }[];
  monthly_card_spend: { month: string; card_spend: number }[];
  by_source: { source: string; count: number; inflow: number; outflow: number; net: number }[];
  top_merchants: { merchant: string; spend: number }[];
  top_revenue_clients: { client: string; revenue: number }[];
  invoice_status: { status: string; count: number; amount: number }[];
  spend_by_category: { category: string; spend: number }[];
  receipt_count: number;
  receipt_errors: number;
  receipt_total_spend: number;
  statement_tx_count: number;
  invoice_count: number;
  invoice_paid_amount: number;
  invoice_pending_amount: number;
};

export type Transaction = {
  date?: string;
  merchant?: string;
  merchant_group?: string;
  category?: string;
  status?: string;
  amount?: number;
  currency?: string;
  source?: string;
};

export type Receipt = {
  source_file?: string;
  merchant_raw?: string;
  amount?: number;
  currency?: string;
  date_raw?: string;
  confidence?: string;
  ocr_mode?: string;
  notes?: string;
  line_items?: unknown;
};

export type AnalysisPayload = {
  analytics: Analytics;
  transactions: Transaction[];
  parsed: {
    receipts: Receipt[];
    statement: unknown[];
    invoices: unknown[];
    notes: unknown[];
  };
  validation: { valid: boolean; errors: string[]; warnings: string[] };
  chat_context: string;
  signature: string;
  meta: { from_disk: boolean; parsed_new_files: number };
};

export type ChatMessage = { role: "user" | "assistant"; content: string };
