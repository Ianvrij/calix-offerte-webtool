# --------------- calix_quote.py  (deel 2/5) ---------------
from __future__ import annotations
import os, tempfile
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd       # (later handig)

##############################################################################
# CONSTANTEN – exact overgenomen uit je Excel-sheet
##############################################################################
PRICE_TABLE = {
    "3D": {
        1000:  {"cost": 2.79, "sell": 3.00},
        2000:  {"cost": 1.63, "sell": 2.13},
        5000:  {"cost": 1.09, "sell": 1.54},
        7500:  {"cost": 0.97, "sell": 1.65},
        10000: {"cost": 0.91, "sell": 1.55},
        50000: {"cost": 0.75, "sell": 1.15},
    },
    "Bedrukt": {
        1: {   # 1-kleur
            1000:  {"cost": 2.07, "sell": 2.80},
            2000:  {"cost": 1.94, "sell": 2.40},
            5000:  {"cost": 1.38, "sell": 2.00},
            7500:  {"cost": 1.36, "sell": 1.80},
            10000: {"cost": 1.27, "sell": 1.70},
            50000: {"cost": 1.20, "sell": 1.50},
        },
        2: {   # 2-kleuren
            1000:  {"cost": 2.37, "sell": 2.90},
            2000:  {"cost": 2.15, "sell": 2.50},
            5000:  {"cost": 1.51, "sell": 2.10},
            7500:  {"cost": 1.48, "sell": 1.90},
            10000: {"cost": 1.35, "sell": 1.80},
            50000: {"cost": 1.24, "sell": 1.40},
        },
        3: {   # 3-kleuren
            1000:  {"cost": 2.57, "sell": 3.00},
            2000:  {"cost": 2.31, "sell": 2.60},
            5000:  {"cost": 1.61, "sell": 2.20},
            7500:  {"cost": 1.57, "sell": 2.00},
            10000: {"cost": 1.43, "sell": 1.90},
            50000: {"cost": 1.28, "sell": 1.50},
        },
    },
}

BTWPCT               = 0.21
SPECIAL_COLOR_FEE    = 480     # € extra bij ‘Special’ bandje
SHIPPING_MIN_QTY     = 10000
SHIPPING_SURCHARGE   = 150

##############################################################################
# HELPERS
##############################################################################
def pick_tier(qty: int, tiers: dict[int, dict]) -> dict:
    """Selecteer juiste staffel op basis van aantal."""
    for bound in sorted(tiers):
        if qty <= bound:
            return tiers[bound]
    return tiers[max(tiers)]

def calc_unit_price(qty: int, prod_type: str, colours: int,
                    extra_pct: float, discount_pct: float) -> tuple[float,float]:
    """Geef (verkoop, kost) per stuk."""
    prod_type = prod_type.capitalize()
    if prod_type == "3d":                      # 3D-logo
        tier = pick_tier(qty, PRICE_TABLE["3D"])
    else:                                     # bedrukt
        tier = pick_tier(qty, PRICE_TABLE["Bedrukt"][colours])

    base_sell, cost = tier["sell"], tier["cost"]
    sell = base_sell * (1 + extra_pct/100) * (1 - discount_pct/100)
    return round(sell, 2), round(cost, 2)

def eur(val: float) -> str:
    """Formatteer als € 1.234,56 (EU-notatie)."""
    return f"€ {val:,.2f}".replace(",", " ").replace(".", ",")
# --------------- calix_quote.py  (deel 3/5) ---------------
st.set_page_config(page_title="Calix Offerte-tool", layout="wide")
st.title("📄 Calix Offerte-generator")

# ── Hoofdgegevens ───────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    qty     = st.number_input("Aantal", 1, 1000000, 1000, 1)
with col2:
    prod    = st.selectbox("Type", ["3D", "Bedrukt"])
    kleuren = st.selectbox("Aantal kleuren", [1, 2, 3], disabled=(prod=="3D"))
    extra   = st.number_input("Verhoging (Extra %)", 0.0, 100.0, 0.0, 0.1)
    korting = st.number_input("Korting %",             0.0, 100.0, 0.0, 0.1)

n_opties = st.number_input("Aantal opties (totaal)", 1, 5, 1, 1)

# ── Opties 2..n ────────────────────────────────────────────
extra_opts: list[dict] = []
st.subheader("📦 Extra opties")
for idx in range(2, n_opties + 1):
    exp = st.expander(f"Optie {idx}")
    with exp:
        q   = st.number_input("Aantal", 1, 1000000, qty, 1, key=f"q{idx}")
        t   = st.selectbox("Type", ["3D", "Bedrukt"], key=f"t{idx}")
        kc  = st.selectbox("Kleuren (indien bedrukt)", [1,2,3],
                           disabled=(t=="3D"), key=f"k{idx}")
        band= st.selectbox("Kleur bandje", ["Standaard", "Special"], key=f"b{idx}")
        disc= st.number_input("Korting %", 0.0, 100.0, 0.0, 0.1, key=f"d{idx}")
    extra_opts.append({"qty": q, "type": t, "col": kc, "band": band, "kort": disc})
# --------------- calix_quote.py  (deel 4/5) ---------------
# ── Bereken hoofdproduct ───────────────────────────────────
rows_html: list[str] = []
tot_excl: float      = 0.0

def add_row(q, t, kleur, details, price_pp):
    global tot_excl
    subt = q * price_pp
    rows_html.append(
        f"<tr><td>{q}</td><td>{t}</td><td>{kleur}</td><td>{details}</td>"
        f"<td style='text-align:right;'>{eur(price_pp)}</td>"
        f"<td style='text-align:right;'>{eur(subt)}</td></tr>"
    )
    tot_excl += subt

sell_main, _ = calc_unit_price(qty, prod, kleuren, extra, korting)
details_main = ("3D-logo inbegrepen, Inclusief Ontwerpcontrole"
                if prod == "3D"
                else f"{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole")
add_row(qty, prod, "Standaard", details_main, sell_main)

# ── Verwerk extra opties ───────────────────────────────────
for opt in extra_opts:
    sell, _ = calc_unit_price(opt["qty"], opt["type"], opt["col"],
                              extra, opt["kort"])
    det = ("3D-logo inbegrepen, Inclusief Ontwerpcontrole"
           if opt["type"] == "3D"
           else f"{opt['col']}-kleur tampondruk, Inclusief Ontwerpcontrole")
    kleurband = "Special" if opt["band"]=="Special" else "Standaard"
    add_row(opt["qty"], opt["type"], kleurband, det, sell)

    if opt["band"] == "Special":
        add_row(1, "Extra", "Special",
                "Voor afwijkende kleurkeuze (‘Special’ bandje)",
                SPECIAL_COLOR_FEE)

# Verzendkosten
if qty > SHIPPING_MIN_QTY:
    add_row(1, "Verzendkosten", "–",
            "Extra kosten voor zending", SHIPPING_SURCHARGE)

# ── BTW & totaaltelling ───────────────────────────────────
btw        = tot_excl * BTWPCT
totaal_inc = tot_excl + btw

# ── HTML genereren ─────────────────────────────────────────
template_html = Path(__file__).with_name("template.html").read_text(encoding="utf-8")

html_out = template_html.format(
    KLANT=klant or "–",
    ADRES=adres or "–",
    OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows_html),
    TOTALEXCL=eur(tot_excl),
    BTW=eur(btw),
    TOTAALINC=eur(totaal_inc)
)

# ── Voorvertoning ─────────────────────────────────────────
components.html(html_out, height=950, scrolling=True)

# ── Download knoppen ─────────────────────────────────────
if st.button("Genereer PDF"):
    try:
        from weasyprint import HTML
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fp:
            HTML(string=html_out, base_url=os.getcwd()).write_pdf(fp.name)
            pdf_bytes = Path(fp.name).read_bytes()
        st.download_button("⬇️ Download offerte (PDF)",
                           pdf_bytes, file_name=f"Offerte_{offnr or 'Calix'}.pdf",
                           mime="application/pdf")
    except Exception as err:
        st.error(f"PDF-generatie mislukt – download HTML als fallback.\n{err}")
        st.download_button("⬇️ Download offerte (HTML)",
                           html_out.encode("utf-8"),
                           file_name=f"Offerte_{offnr or 'Calix'}.html",
                           mime="text/html")
<!-- template.html  (deel 5/5) -->
<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8">
<title>Offerte Calix</title>
<style>
/* … 100 % identiek aan VBA-versie – zie vorige antwoord … */
@page{size:A4;margin:0;}
@font-face{font-family:'Clash Display';src:url('ClashDisplay-Regular.otf') format('opentype');}
@font-face{font-family:'Clash Display';src:url('ClashDisplay-Bold.otf') format('opentype');font-weight:bold;}
@font-face{font-family:'Sansation';src:url('Sansation-Bold.ttf') format('truetype');font-weight:bold;}
body{margin:0;font-family:'Clash Display',sans-serif;font-size:12px;line-height:1.4;color:#333;}
/* —— layout, header, footer, tables … —— (ongewijzigd) —— */
.page{width:210mm;height:297mm;position:relative;overflow:hidden;}
.section{padding:0 60px 8px;margin-bottom:0;}
.header{background:#E4B713;color:#fff;padding:10px 30px 80px;
        clip-path:polygon(0 0,100% 0,100% 70%,0 100%);position:relative;}
.header-top{display:flex;align-items:center;justify-content:space-between;}
.header-brand{font-size:18px;font-weight:700;letter-spacing:.5px;color:#fff;text-transform:uppercase;font-family:'Sansation',sans-serif;}
.header-text{font-size:18px;font-weight:600;letter-spacing:.5px;color:#fff;text-transform:uppercase;font-family:'Sansation',sans-serif;}
.header-divider{height:3px;background:#fff;width:100%;margin:0 0 30px;border-radius:2px;}
.header h1{font-size:26px;margin:0;font-weight:600;}
footer,h2,h3{margin:0;}
.footer-fixed{position:absolute;left:0;bottom:0;width:100%;background:#E4B713;color:#fff;
              font-size:12px;padding:50px 0 30px;clip-path:polygon(0 14%,100% 0%,100% 100%,0% 100%);}
.footer-cols{display:flex;justify-content:space-between;max-width:960px;margin:0 auto;padding:0 40px;gap:40px;}
.footer-col{flex:1;} .footer-col table{width:100%;border-spacing:0;}
.footer-col td{padding:2px 0;color:#fff;font-size:12px;} .footer-col td:first-child{font-weight:600;padding-right:6px;white-space:nowrap;}
.footer-note{text-align:center;font-size:11px;color:#fff;line-height:1.4;margin-top:10px;}
.footer-note a{color:#fff;text-decoration:none;border-bottom:1px solid #fff;}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:12px;}
table.prod tr:nth-child(even){background:#fafafa;} th,td{padding:6px;border-bottom:1px solid #FFFFFF;}
th{background:#f8f8f8;font-weight:600;text-align:left;}
.totals-separator{height:4px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px;}
.totalbar{height:4px;background:#E4B713;width:44%;margin:4px 0 8px auto;border-radius:2px;}
.totals td{padding:2px 0;}.totals .label{text-align:right;width:70%;}.totals .value{text-align:right;font-weight:600;}
.flex-row-3{display:flex;gap:20px;justify-content:space-between;margin-top:14px;}
.flex-row-3>div{flex:1;padding:12px;border-radius:6px;font-size:10px;}
.flex-yellow{background:#fff3cd;}.flex-gray{background:#f4f4f4;}
</style></head><body>

<div class="page">
  <!-- HEADER -------------------------------------------------------------->
  <div class="header">
    <div class="header-top"><span class="header-brand">CALIX</span><span class="header-text">HANDS FREE DANCING</span></div>
    <div class="header-divider"></div>
    <img src="Tilted SIO 2 - PNG.png" alt="Calix" style="position:absolute;top:23px;right:40px;width:220px;">
    <h1>Cupholder voor: {KLANT}</h1>
    <p>Offertenummer: {OFFNR}<br>Datum: {DATUM} | Geldig tot: {GELDIG}<br>Adres: {ADRES}</p>
  </div>

  <!-- BODY --------------------------------------------------------------->
  <div class="section"><h2>Welkom!</h2>
    <p>Dank voor je interesse in onze duurzame bekerhouders. Met deze oplossing verlaag je de afvalstroom én geef je bezoekers een handige gadget als blijvende herinnering.</p>
  </div>

  <div class="section"><h2>Productoverzicht</h2>
    <table class="prod"><tr>
      <th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
      <th style="text-align:right;">Prijs/stuk</th>
      <th style="text-align:right;">Totaal excl. btw</th></tr>
      {PRODUCTROWS}
    </table>
    <div class="totals-separator"></div>
    <table class="totals">
      <tr><td class="label">Totaal excl. btw:</td><td class="value">{TOTALEXCL}</td></tr>
      <tr><td class="label">BTW (21 %):</td><td class="value">{BTW}</td></tr>
    </table>
    <div class="totalbar"></div>
    <table class="totals">
      <tr><td class="label total-bold">Totaal incl. btw:</td><td class="value total-bold">{TOTAALINC}</td></tr>
    </table>
  </div>

  <!-- FOOTER ------------------------------------------------------------->
  <div class="footer-fixed">
    <div class="footer-cols">
      <div class="footer-col"><table>
        <tr><td>Adres</td><td>Bieze 23</td></tr><tr><td></td><td>5382 KZ Vinkel</td></tr>
        <tr><td>Telefoon</td><td>+31 (0)6 29 83 0517</td></tr>
      </table></div>

      <div class="footer-col"><table>
        <tr><td>E-mail</td><td><a href="mailto:info@handsfreedancing.nl">info@handsfreedancing.nl</a></td></tr>
        <tr><td>Website</td><td><a href="https://handsfreedancing.nl">handsfreedancing.nl</a></td></tr>
      </table></div>

      <div class="footer-col"><table>
        <tr><td>BTW</td><td>NL86614472B01</td></tr>
        <tr><td>IBAN</td><td>NL04 RABO 0383 2726 88</td></tr>
      </table></div>
    </div>
    <div class="footer-note">
      Calix is een handelsnaam van Calix Promotie Producten V.O.F. Op deze aanbieding zijn onze leveringsvoorwaarden van toepassing.
      <a href="https://handsfreedancing.nl/voorwaarden">Bekijk voorwaarden</a>
    </div>
  </div>
</div>

</body></html>
