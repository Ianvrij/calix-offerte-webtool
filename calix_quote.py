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

