import base64
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import io

import streamlit as st
from weasyprint import HTML


# ────────────────────────────────────────────────────────────────────────────
# Helpers for WeasyPrint and HTML
# ---------------------------------------------------------------------------
def eur(val: float | Decimal) -> str:
    """€-notation with commas for decimal and periods for thousands."""
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"


def b64_img(filename: str) -> str:
    """Provide a data URI for a local image; works everywhere (also Streamlit Cloud)."""
    p = Path(__file__).with_name(filename)
    mime = "image/png" if filename.lower().endswith("png") else "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        st.write(f"PDF-engine: WeasyPrint")   # Visible in the app log
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)        # Display error message without app crash
        return None


# ────────────────────────────────────────────────────────────────────────────
# Template HTML structure
# ---------------------------------------------------------------------------
html_template = """
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8" />
    <title>Offerte Calix</title>
    <style>
        @page {
            size: A4;
            margin: 0;
        }
        body {
            font-family: 'Clash Display', sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        .page {
            width: 210mm;
            height: 297mm;
            position: relative;
            overflow: hidden;
        }
        .header {
            background: #E4B713;
            color: #fff;
            padding: 10px 30px;
            clip-path: polygon(0 0, 100% 0, 100% 70%, 0 100%);
            position: relative;
        }
        .header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 {
            font-size: 26px;
            font-weight: 600;
            margin: 0;
        }
        .footer-fixed {
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            background: #E4B713;
            color: #fff;
            font-size: 12px;
            padding: 50px 0 30px;
            clip-path: polygon(0 14%, 100% 0%, 100% 100%, 0% 100%);
            z-index: 10;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 12px;
        }
        table.prod tr:nth-child(even) {
            background: #fafafa;
        }
        th, td {
            padding: 6px;
            border-bottom: 1px solid #FFFFFF;
        }
        th {
            background: #f8f8f8;
            font-weight: 600;
            text-align: left;
        }
        .totals td {
            background: none;
            padding: 2px 0;
        }
        .totals .label {
            text-align: right;
            width: 70%;
            padding-right: 0;
        }
        .totals .value {
            text-align: right;
        }
        .total-bold {
            font-weight: bold;
        }
        .totals-separator {
            height: 4px;
            background: #E4B713;
            width: 100%;
            margin: 4px 0;
            border-radius: 2px;
        }
        .totalbar {
            height: 4px;
            background: #E4B713;
            width: 44%;
            margin: 4px 0 8px auto;
            border-radius: 2px;
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="header">
            <div class="header-top">
                <span class="header-brand">CALIX</span>
                <span class="header-text">HANDS FREE DANCING</span>
            </div>
            <h1>Offerte voor: ${KLANT}</h1>
            <p>Offertenummer: ${OFFNR} | Datum: ${DATUM} | Geldig tot: ${GELDIG}</p>
            <p>Adres: ${ADRES}</p>
        </div>
        <div class="section">
            <h2>Welkom!</h2>
            <p>Dank voor je interesse in onze duurzame bekerhouders...</p>
        </div>
        <div class="section">
            <h2>Toelichting op de prijsindicatie</h2>
            <div style="background:#f9f9f9;padding:12px;border-radius:6px;">
                <ul>
                    <li><b>Product:</b> Calix bekerhouder, uitgevoerd in één kleur.</li>
                    <li><b>Kleur:</b> Keuze uit zwart, rood, blauw of off-white.</li>
                    <li><b>Logo:</b> Gepersonaliseerd 3D-logo of tampondruk (logovlak: 6,5 × 2 cm).</li>
                </ul>
                <p><b>Disclaimer:</b> Aan deze prijsindicatie kunnen geen rechten worden ontleend.</p>
            </div>
        </div>
        <div class="section">
            <h2>Productoverzicht</h2>
            <table class="prod">
                <tr>
                    <th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th><th style="text-align:right;">Prijs/stuk</th><th style="text-align:right;">Totaal excl. btw</th>
                </tr>
                ${PRODUCTROWS}
            </table>
            <div class="totals-separator"></div>
            <table class="totals">
                <tr><td class="label">Totaal excl. btw:</td><td class="value">${TOTALEXCL}</td></tr>
                <tr><td class="label">BTW (21%):</td><td class="value">${BTW}</td></tr>
            </table>
            <div class="totalbar"></div>
            <table class="totals">
                <tr><td class="label total-bold">Totaal incl. btw:</td><td class="value total-bold">${TOTAALINC}</td></tr>
            </table>
        </div>
        <div class="footer-fixed">
            <div class="footer-cols">
                <div class="footer-col">
                    <table>
                        <tr><td>Adres</td><td>Bieze 23</td></tr>
                        <tr><td></td><td>5382 KZ Vinkel</td></tr>
                        <tr><td>Telefoon</td><td>+31 (0)6 29 83 0517</td></tr>
                    </table>
                </div>
                <div class="footer-col">
                    <table>
                        <tr><td>E-mail</td><td><a href="mailto:info@handsfreedancing.nl">info@handsfreedancing.nl</a></td></tr>
                        <tr><td>Website</td><td><a href="https://handsfreedancing.nl">handsfreedancing.nl</a></td></tr>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Load and replace placeholders
html_out = Template(html_template).safe_substitute(
    KLANT="Test Klant",
    OFFNR="12345",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
    ADRES="Bieze 23, 5382 KZ Vinkel",
    PRODUCTROWS="..."  # Add product rows here dynamically
)

# Generate PDF
pdf_data = html_to_pdf_bytes(html_out)

# Provide download options in Streamlit
if pdf_data:
    st.download_button("Download PDF", pdf_data, file_name="offerte.pdf", mime="application/pdf")
else:
    st.info("PDF-backend niet beschikbaar. Download de HTML en print die in je browser naar PDF.")

