import { useRef, useState, type ReactNode } from "react";
import {
  refreshAnalysis,
  uploadInvoices,
  uploadNotes,
  uploadReceipts,
  uploadStatement,
} from "../api";

type Props = {
  shoebox: string;
  onShoeboxChange: (v: string) => void;
  onRefresh: () => void;
  loading: boolean;
};

function UploadExpander({
  title,
  caption,
  children,
  defaultOpen = false,
}: {
  title: string;
  caption: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`upload-expander${open ? " open" : ""}`}>
      <button
        type="button"
        className="upload-expander-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="upload-expander-chevron">{open ? "▾" : "▸"}</span>
        <span className="upload-expander-title">{title}</span>
      </button>
      {open && (
        <div className="upload-expander-body">
          <p className="upload-expander-caption">{caption}</p>
          {children}
        </div>
      )}
    </div>
  );
}

function HiddenFileButton({
  label,
  accept,
  multiple,
  disabled,
  onFiles,
}: {
  label: string;
  accept: string;
  multiple?: boolean;
  disabled?: boolean;
  onFiles: (files: FileList) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        className="hidden-file-input"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={(e) => {
          if (e.target.files?.length) {
            onFiles(e.target.files);
            e.target.value = "";
          }
        }}
      />
      <button
        type="button"
        className="btn btn-upload"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        {label}
      </button>
    </>
  );
}

export function Sidebar({ shoebox, onShoeboxChange, onRefresh, loading }: Props) {
  const [noteText, setNoteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const notesFileRef = useRef<HTMLInputElement>(null);

  const afterUpload = async (fn: () => Promise<unknown>, successMsg: string) => {
    setBusy(true);
    setStatus(null);
    try {
      await fn();
      setStatus(successMsg);
      onRefresh();
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="sidebar">
      <h2>LedgerLens</h2>

      <section>
        <label>Data folder</label>
        <input
          className="input"
          value={shoebox}
          onChange={(e) => onShoeboxChange(e.target.value)}
        />
        <button
          className="btn btn-primary"
          disabled={loading || busy}
          onClick={async () => {
            setBusy(true);
            setStatus(null);
            try {
              await refreshAnalysis(shoebox);
              onRefresh();
              setStatus("Analysis refreshed.");
            } catch (e) {
              setStatus(e instanceof Error ? e.message : "Refresh failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          Refresh analysis
        </button>
      </section>

      <section className="upload-section">
        <h3 className="upload-section-title">Add documents</h3>
        <p className="upload-section-caption">
          Expand a section, attach files, then save to your shoebox.
        </p>

        <UploadExpander
          title="Receipt images"
          caption="Photos / scans (JPG, PNG, WEBP…)"
        >
          <HiddenFileButton
            label="Choose receipt images"
            accept="image/*"
            multiple
            disabled={busy}
            onFiles={(files) =>
              afterUpload(() => uploadReceipts(shoebox, files), `Saved ${files.length} receipt(s).`)
            }
          />
        </UploadExpander>

        <UploadExpander title="Card statement" caption="PDF statement">
          <HiddenFileButton
            label="Choose statement PDF"
            accept=".pdf,application/pdf"
            disabled={busy}
            onFiles={(files) =>
              afterUpload(() => uploadStatement(shoebox, files[0]!), "Statement saved.")
            }
          />
        </UploadExpander>

        <UploadExpander title="Invoices" caption="Excel workbook (.xlsx, .xls)">
          <HiddenFileButton
            label="Choose invoice workbook"
            accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
            disabled={busy}
            onFiles={(files) =>
              afterUpload(() => uploadInvoices(shoebox, files[0]!), "Invoices saved.")
            }
          />
        </UploadExpander>

        <UploadExpander title="Notes" caption="Paste notes or upload .txt / .md">
          <textarea
            className="input"
            rows={4}
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="e.g. Petco charge was $47 — personal, move to personal card"
          />
          <input
            ref={notesFileRef}
            type="file"
            className="hidden-file-input"
            accept=".txt,.md,text/plain"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                afterUpload(() => uploadNotes(shoebox, noteText, f), "Notes updated.").then(
                  () => setNoteText("")
                );
                e.target.value = "";
              }
            }}
          />
          <div className="upload-actions">
            <button
              type="button"
              className="btn btn-upload"
              disabled={busy}
              onClick={() => notesFileRef.current?.click()}
            >
              Attach notes file
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy || !noteText.trim()}
              onClick={() =>
                afterUpload(() => uploadNotes(shoebox, noteText), "Notes saved.").then(() =>
                  setNoteText("")
                )
              }
            >
              Save notes
            </button>
          </div>
        </UploadExpander>

        {status && <p className={`upload-status${status.includes("fail") ? " error" : ""}`}>{status}</p>}
      </section>

      <p className="caption sidebar-footer">Use Ask LedgerLens (bottom-right) for questions.</p>
    </aside>
  );
}
