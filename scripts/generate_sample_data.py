"""Generate demo shoebox files for the financial pipeline."""

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
SHOEBOX = ROOT / "shoebox"
RECEIPTS = SHOEBOX / "receipts"


def write_notes():
    SHOEBOX.mkdir(parents=True, exist_ok=True)
    (SHOEBOX / "notes.txt").write_text(
        """# Expense notes — pipe format: date | merchant | amount | category
2025-03-12 | Client Payment - Acme Corp | 2500.00 | Revenue
2025-03-18 | AWS Monthly | 89.50 | Software & Cloud
Uber - $24.75 on 2025-03-20
""",
        encoding="utf-8",
    )


def write_invoices():
    df = pd.DataFrame(
        [
            {
                "invoice_id": "INV-1001",
                "date": "2025-03-10",
                "vendor": "Staples Canada",
                "amount": 156.40,
                "status": "paid",
            },
            {
                "invoice_id": "INV-1002",
                "date": "2025-03-15",
                "vendor": "Microsoft 365",
                "amount": 22.99,
                "status": "paid",
            },
            {
                "invoice_id": "INV-1003",
                "date": "2025-03-22",
                "vendor": "Amazon Web Services",
                "amount": 89.50,
                "status": "pending",
            },
        ]
    )
    df.to_excel(SHOEBOX / "invoices.xlsx", index=False)


def write_statement():
    pdf_path = SHOEBOX / "card_statement.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 750, "Business Card Statement — March 2025")
    c.setFont("Helvetica", 10)
    y = 720
    c.drawString(72, y, "Date          Description                    Amount")
    y -= 20
    lines = [
        ("2025-03-05", "STARBUCKS #239", -6.45),
        ("2025-03-08", "Starbucks Ottawa", -8.20),
        ("2025-03-10", "STAPLES #4421", -156.40),
        ("2025-03-12", "CLIENT PAYMENT ACME", 2500.00),
        ("2025-03-15", "MSFT*365", -22.99),
        ("2025-03-18", "AMZN WEB SERVICES", -89.50),
        ("2025-03-20", "UBER TRIP", -24.75),
        ("2025-03-22", "TIM HORTONS #881", -4.95),
    ]
    for date, desc, amt in lines:
        c.drawString(72, y, f"{date}  {desc:<30}  ${amt:,.2f}")
        y -= 16
    c.save()


def _receipt_image(path: Path, lines: list[str]):
    img = Image.new("RGB", (400, 520), color=(248, 248, 248))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_lg = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
        font_lg = font

    y = 40
    for i, line in enumerate(lines):
        f = font_lg if i == 0 else font
        draw.text((30, y), line, fill=(20, 20, 20), font=f)
        y += 36 if i == 0 else 28

    img.save(path)


def write_receipts():
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    samples = [
        (
            "receipt_starbucks_239.png",
            [
                "STARBUCKS #239",
                "123 Main St",
                "Date: 2025-03-05",
                "Latte          $4.95",
                "Tax            $1.50",
                "TOTAL: $6.45",
            ],
        ),
        (
            "receipt_staples.png",
            [
                "STAPLES STORE",
                "Date: 2025-03-10",
                "Office supplies",
                "TOTAL: $156.40",
            ],
        ),
        (
            "receipt_uber.png",
            [
                "UBER",
                "Trip receipt",
                "Date: 2025-03-20",
                "TOTAL: $24.75",
            ],
        ),
    ]
    for filename, lines in samples:
        _receipt_image(RECEIPTS / filename, lines)


def main():
    write_notes()
    write_invoices()
    write_statement()
    write_receipts()
    print(f"Sample shoebox created at {SHOEBOX}")


if __name__ == "__main__":
    main()
