# -------- calix_quote.py  (deel 2/5) --------
from __future__ import annotations
import os, tempfile
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

##############################################################################
# CONSTANTEN — exact uit je Excel-staffels
##############################################################################
PRICE_TABLE = {          # ingekort voorbeeld; vul evt. uit
    "3D": {
        1000:  {"cost": 2.79, "sell": 3.00},
        2000:  {"cost": 1.63, "sell": 2.13},
        5000:  {"cost": 1.09, "sell": 1.54},
        7500:  {"cost": 0.97, "sell": 1.65},
        10000: {"cost": 0.91, "sell": 1.55},
        50000: {"cost": 0.75, "sell": 1.15},
    },
    "Bedrukt": {
        1: {1000: {"cost": 2.07, "sell": 2.80}, 2000: {"cost": 1.94, "sell": 2.40},
            5000: {"cost": 1.38, "sell": 2.00}, 7500: {"cost": 1.36, "sell": 1.80},
            10000: {"cost": 1.27, "sell": 1.70}, 50000: {"cost": 1.20, "sell": 1.50}},
        2: {1000: {"cost": 2.37, "sell": 2.90}, 2000: {"cost": 2.15, "sell": 2.50},
            5000: {"cost": 1.51, "sell": 2.10}, 7500: {"cost": 1.48, "sell": 1.90},
            10000: {"cost": 1.35, "sell": 1.80}, 50000: {"cost": 1.24, "sell": 1.40}},
        3: {1000: {"cost": 2.57, "sell": 3.00}, 2000: {"cost": 2.31, "sell": 2.60},
            5000: {"cost": 1.61, "sell": 2.20}, 7500: {"cost": 1.57, "sell": 2.00},
            10000: {"cost": 1.43, "sell": 1.90}, 50000: {"cost": 1.28, "sell": 1.50}},
    },
}
BTWPCT               = 0.21
SPECIAL_COLOR_FEE    = 480
SHIPPING_MIN_QTY     = 10000
SHIPPING_SURCHARGE   = 150

def pick_tier(qty: int, tiers: dict[int, dict]) -> dict:
    for bound in sorted(tiers):
        if qty <= bound:
            return tiers[bound]
    return tiers[max(tiers)]

def calc_unit_price(qty: int, prod_type: str, colours: int,
                    extra_pct: float, discount_pct: float) -> tuple[float, float]:
    prod_type = prod_type.capitalize()
    if prod_type == "3d":
        tier = pick_tier(qty, PRICE_TABLE["3D"])
    else:
        tier = pick_tier(qty, PRICE_TABLE["Bedrukt"][colours])
    sell = tier["sell"] * (1 + extra_pct/100) * (1 - discount_pct/100)
    return round(sell, 2), round(tier["cost"], 2)

def eur(x: float) -> str:
    return f"€ {x:,.2f}".replace(",", " ").replace(".", ",")
# -------- calix_quote.py  (deel 3/5) --------
st.set_page_config(page_title="Calix Offerte-tool", layout="wide")
st.title("📄 Calix Offerte-generator")

col1, col2 = st.columns(2)
with col1:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    qty     = st.number_input("Aantal", 1, 1000000, 1000)
with col2:
    prod    = st.selectbox("Type", ["3D", "Bedrukt"])
    kleuren = st.selectbox("Aantal kleuren", [1,2,3], disabled=(prod=="3D"))
    extra   = st.number_input("Verhoging (Extra %)", 0.0, 100.0, 0.0)
    korting = st.number_input("Korting %", 0.0, 100.0, 0.0)

n_opties = st.number_input("Aantal opties (totaal)", 1, 5, 1)

extra_opts = []
for i in range(2, n_opties+1):
    with st.expander(f"Optie {i}"):
        q   = st.number_input("Aantal", 1, 1000000, qty, key=f"q{i}")
        t   = st.selectbox("Type", ["3D", "Bedrukt"], key=f"t{i}")
        kc  = st.selectbox("Kleuren (bij bedrukt)", [1,2,3],
                           disabled=(t=="3D"), key=f"kc{i}")
        band= st.selectbox("Kleur bandje", ["Standaard", "Special"], key=f"b{i}")
        disc= st.number_input("Korting %", 0.0, 100.0, 0.0, key=f"d{i}")
    extra_opts.append({"qty": q, "type": t, "col": kc, "band": band, "kort": disc})
# -------- calix_quote.py  (deel 4/5) --------
rows, total_excl = [], 0.0
def add_row(a, t, clr, det, price):
    global total_excl
    subt = a * price
    rows.append(f"<tr><td>{a}</td><td>{t}</td><td>{clr}</td><td>{det}</td>"
                f"<td style='text-align:right;'>{eur(price)}</td>"
                f"<td style='text-align:right;'>{eur(subt)}</td></tr>")
    total_excl += subt

# hoofdproduct
sell_main, _ = calc_unit_price(qty, prod, kleuren, extra, korting)
detail_main  = ("3D-logo inbegrepen, Inclusief Ontwerpcontrole"
                if prod=="3D" else f"{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole")
add_row(qty, prod, "Standaard", detail_main, sell_main)

# extra opties
for o in extra_opts:
    sell, _ = calc_unit_price(o["qty"], o["type"], o["col"], extra, o["kort"])
    det = ("3D-logo inbegrepen, Inclusief Ontwerpcontrole"
           if o["type"]=="3D" else f"{o['col']}-kleur tampondruk, Inclusief Ontwerpcontrole")
    band = "Special" if o["band"]=="Special" else "Standaard"
    add_row(o["qty"], o["type"], band, det, sell)
    if o["band"]=="Special":
        add_row(1, "Extra", "Special",
                "Voor afwijkende kleurkeuze (‘Special’ bandje)", SPECIAL_COLOR_FEE)

if qty > SHIPPING_MIN_QTY:
    add_row(1, "Verzendkosten", "–", "Extra kosten voor zending", SHIPPING_SURCHARGE)

btw        = total_excl * BTWPCT
totaal_inc = total_excl + btw

template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
html_out = template.format(
    KLANT=klant or "–", ADRES=adres or "–", OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl), BTW=eur(btw), TOTAALINC=eur(totaal_inc)
)

components.html(html_out, height=950, scrolling=True)

if st.button("Genereer PDF"):
    from weasyprint import HTML
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fp:
        HTML(string=html_out, base_url=os.getcwd()).write_pdf(fp.name)
        st.download_button("⬇️ Download PDF",
                           Path(fp.name).read_bytes(),
                           file_name=f"Offerte_{offnr or 'Calix'}.pdf",
                           mime="application/pdf")
