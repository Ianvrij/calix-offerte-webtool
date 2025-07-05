import streamlit as st
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from string import Template
import base64
from pathlib import Path
import io
import weasyprint

# Cache for PDF conversion
@st.cache_resource
def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from weasyprint import HTML, __version__ as WV
        st.write(f"PDF-engine: WeasyPrint {WV}")  # Visible in app
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)  # Shows error message in app
        return None


# Helper function for Euro formatting
def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Streamlit UI components
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# Input fields
st.header("Hoofdoptie")
cA, cB = st.columns(2)
with cA:
    klant = st.text_input("Naam klant")
    adres = st.text_input("Adres")
    offnr = st.text_input("Offertenummer")
    aantal = st.number_input("Aantal", min_value=1, value=1000)
with cB:
    product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal = st.selectbox("Aantal kleuren", [1, 2, 3], disabled=(product_type != "Bedrukt"))
    kleurkeuzes = ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"]
    kleur_bandje = st.selectbox("Kleur bandje", kleurkeuzes, index=2)
    korting_pct = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
    verhoging_pct = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal extra opties (0–3)", 0, 3, 0)

# Extra opties input
extra_opties = []
if opties_aantal:
    st.header("Extra opties")
    for i in range(1, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            a = st.number_input("Aantal", 1, key=f"opt_aantal_{i}")
        with c2:
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"], key=f"opt_type_{i}")
        with c3:
            kc = st.selectbox("Kleuren", [1, 2, 3], disabled=(t != "Bedrukt"), key=f"opt_kc_{i}")
        with c4:
            kband = st.selectbox("Bandje-kleur", kleurkeuzes, index=0, key=f"opt_band_{i}")
        kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0, key=f"opt_kort_{i}")
        extra_opties.append(dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort))

st.divider()

# Price and cost calculations
prijs = {
    "3D": {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97, 10000: 0.91, 50000: 0.75},
    "Bedrukt1": {1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36, 10000: 1.27, 50000: 1.20},
    "Bedrukt2": {1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48, 10000: 1.35, 50000: 1.24},
    "Bedrukt3": {1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57, 10000: 1.43, 50000: 1.28},
}

staffels = sorted(prijs["3D"])

def _staffel(a: int) -> int:
    return min(staffels, key=lambda x: abs(x - a))

def kostprijs(typ: str, aant: int, kl: int) -> float:
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return prijs[key][_staffel(aant)]

def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh / 100) * (1 - kort / 100)

# Create HTML content dynamically
rows = []
total_excl = Decimal(0)

def append_row(a: int, t: str, kband: str, stprijs: float, oms: str) -> None:
    global total_excl
    rows.append(f"""
<tr><td>{a}</td><td>{t}</td><td>{kband}</td><td>{oms}</td><td style="text-align:right;">{eur(stprijs)}</td><td style="text-align:right;">{eur(stprijs * a)}</td></tr>""")
    total_excl += Decimal(stprijs * a)

# Main product calculations
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = f"{kleuren_aantal}-kleuren tampondruk, Inclusief Ontwerpcontrole" if product_type == "Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
append_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# Extra options calculations
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = f"{opt['kleuren']}-kleuren tampondruk, Inclusief Ontwerpcontrole" if opt["type"] == "Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    append_row(opt["aantal"], opt["type"], opt["band"], vp, oms)

# Calculate taxes and total
btw = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# HTML content generation
html_out = f"""
<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Offerte Calix</title>
<style>
body {{ font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4; }}
.page {{ width: 210mm; height: 297mm; padding: 20mm; }}
.header {{ background: #E4B713; padding: 10mm; color: #fff; }}
.footer {{ background: #E4B713; padding: 10mm; color: #fff; text-align: center; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10mm; }}
th, td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
th {{ background: #f8f8f8; font-weight: bold; }}
.totals {{ text-align: right; font-weight: bold; }}
</style>
</head>
<body>

<div class="page">
  <div class="header">
    <h1>Offerte voor: {klant}</h1>
    <p>Offertenummer: {offnr} | Datum: {datetime.now().strftime('%d-%m-%Y')} | Geldig tot: {datetime.now() + timedelta(days=14)}</p>
  </div>

  <div class="section">
    <h2>Welkom!</h2>
    <p>Dank voor je interesse in onze duurzame bekerhouders...</p>
  </div>

  <div class="section">
    <h2>Productoverzicht</h2>
    <table>
      <tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th><th>Prijs/stuk</th><th>Totaal excl. btw</th></tr>
      {''.join(rows)}
    </table>
    <div class="totals">
      <p>Totaal excl. btw: {eur(total_excl)}</p>
      <p>BTW (21%): {eur(btw)}</p>
      <p>Totaal incl. btw: {eur(totaal_inc)}</p>
    </div>
  </div>

  <div class="footer">
    <p>Calix – Hands Free Dancing</p>
  </div>
</div>

</body>
</html>
"""

# PDF and HTML download options
st.download_button("Download HTML", html_out, file_name="offerte.html", mime="text/html")

pdf_data = html_to_pdf_bytes(html_out)
if pdf_data:
    st.download_button("Download PDF", pdf_data, file_name="offerte.pdf", mime="application/pdf")
else:
    st.info("PDF-backend niet beschikbaar. Download de HTML en print die naar PDF in je browser.")
