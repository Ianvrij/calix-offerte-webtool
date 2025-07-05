# ---------------- calix_quote.py  (deel 1/3) ----------------
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64, tempfile, os, json
from pathlib import Path

# ─────────────────────────────────────────────────────────── #
# 1. PRIJSTABELLEN (kost & verkoop) – 1 op 1 uit je Excel
# ─────────────────────────────────────────────────────────── #
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

BTWPCT = 0.21
SPECIAL_COLOR_FEE = 480          # € bij “Special” bandje
SHIPPING_SURCHARGE_QTY = 10000
SHIPPING_SURCHARGE_EUR = 150     # € boven 10 000 stuks

# ─────────────────────────────────────────────────────────── #
# 2. Helper-functies
# ─────────────────────────────────────────────────────────── #
def get_tier(qty: int, tiers: dict) -> dict:
    """Kiest de eerste staffel ≥ qty; valt terug op hoogste staffel."""
    for bound in sorted(tiers):
        if qty <= bound:
            return tiers[bound]
    return tiers[max(tiers)]

def calc_unit_prices(qty: int,
                     prod_type: str,
                     colours: int,
                     extra_pct: float,
                     discount_pct: float):
    """Geeft (sell, cost, profit_per_unit) rekening houdend met staffel,
       extra opslag (%) en korting (%).  pct-waarden als % (0-100)."""
    prod_type = prod_type.capitalize()          # ‘3D’ of ‘Bedrukt’
    if prod_type == "3d":
        tier = get_tier(qty, PRICE_TABLE["3D"])
    else:
        tier = get_tier(qty, PRICE_TABLE["Bedrukt"][colours])

    base_sell, cost = tier["sell"], tier["cost"]
    sell = base_sell * (1 + extra_pct / 100) * (1 - discount_pct / 100)
    profit_unit = sell - cost
    return round(sell, 2), round(cost, 2), round(profit_unit, 2)

def money(x):        # nettere weergave
    return f"€ {float(x):,.2f}".replace(",", " ").replace(".", ",")

# ----------------------------------------------------------- #
# Streamlit-pagina-config
st.set_page_config("Calix Offerte-tool", layout="wide")
# ---------------- calix_quote.py  (deel 2/3) ----------------
st.title("Calix Offerte-generator")

# --- Basis-input (hoofdofferte) ----------------------------- #
st.header("Hoofd-berekening")

col_a, col_b = st.columns(2)
with col_a:
    klantnaam   = st.text_input("Naam klant")
    adres       = st.text_input("Adres")
    offnr       = st.text_input("Offertenummer")
    aantal      = st.number_input("Aantal",     min_value=1, value=1000, step=1)
with col_b:
    prod_type   = st.selectbox("Type", ["3D", "Bedrukt"])
    kleuren     = st.selectbox("Aantal kleuren", [1,2,3],
                               disabled = (prod_type == "3D"))
    extra_pct   = st.number_input("Verhoging (Extra %)", 0.0, 100.0, 0.0, 0.1)
    korting_pct = st.number_input("Korting %",           0.0, 100.0, 0.0, 0.1)

optiesAantal = st.number_input("Aantal opties (total)", 1, 5, 1, 1)

# --- Extra opties ----------------------------------------- #
st.subheader("Extra opties")
extra_options = []
for i in range(2, optiesAantal+1):
    expander = st.expander(f"Optie {i}")
    with expander:
        a = st.number_input(f"Aantal optie {i}",     min_value=1, value=aantal,      key=f"aantal_{i}")
        t = st.selectbox   (f"Type", ["3D", "Bedrukt"],                             key=f"type_{i}")
        k = st.selectbox   ("Aantal kleuren", [1,2,3], disabled=(t=="3D"),          key=f"kleuren_{i}")
        band = st.selectbox("Kleur bandje", ["Standaard", "Special"],               key=f"band_{i}")
        disc = st.number_input("Korting %", 0.0, 100.0, 0.0, 0.1,                   key=f"kort_{i}")
    extra_options.append({"qty": a, "type": t, "col": k, "band": band, "kort": disc})
# ---------------- calix_quote.py  (deel 3/3) ----------------
# Berekening hoofd­item
sell, cost, profit_unit = calc_unit_prices(aantal, prod_type, kleuren,
                                           extra_pct, korting_pct)
totaal_excl = sell * aantal
totopt_excl = totaal_excl
html_rows   = []

def add_row(qty, t, col, details, sell_pp, cost_pp):
    total_line = qty * sell_pp
    html_rows.append(
        f"<tr><td>{qty}</td><td>{t}</td><td>{col}</td>"
        f"<td>{details}</td>"
        f"<td style='text-align:right;'>{money(sell_pp)}</td>"
        f"<td style='text-align:right;'>{money(total_line)}</td></tr>"
    )
    return total_line

# beschrijving
details = f"{'3D-logo inbegrepen' if prod_type=='3D' else f'{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole'}"
totopt_excl = add_row(aantal, prod_type, "Special" if False else "Standaard",
                      details, sell, cost)

# Verwerk extra opties
for opt in extra_options:
    s, c, _ = calc_unit_prices(opt["qty"], opt["type"], opt["col"],
                               extra_pct, opt["kort"])
    det = ("3D-logo inbegrepen" if opt["type"]=="3D"
           else f"{opt['col']}-kleur tampondruk, Inclusief Ontwerpcontrole")
    kleurband = "Special" if opt["band"]=="Special" else "Standaard"
    totopt_excl += add_row(opt["qty"], opt["type"], kleurband, det, s, c)
    if opt["band"] == "Special":
        totopt_excl += add_row(1, "Extra", "Special",
                               "Voor afwijkende kleurkeuze (‘Special’ bandje)",
                               SPECIAL_COLOR_FEE, 0)

# Verzend­kosten
if aantal > SHIPPING_SURCHARGE_QTY:
    totopt_excl += add_row(1, "Verzendkosten", "–",
                           "Extra kosten voor zending",
                           SHIPPING_SURCHARGE_EUR, 0)

btw = totopt_excl * BTWPCT
totaal_inc = totopt_excl + btw

# ---- HTML-render ----------------------------------------- #
today = datetime.now().strftime("%d-%m-%Y")
geldigheid = (datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y")

html_rows_str = "".join(html_rows)
html_template = Path(__file__).with_name("template.html").read_text()

html_filled = html_template.format(
    KLANT=klantnaam,
    OFF=offnr,
    DAT=today,
    GELD=geldigheid,
    ADRES=adres,
    PRODUCTROWS=html_rows_str,
    TOTALEXCL=money(totopt_excl),
    BTW=money(btw),
    TOTAALINC=money(totaal_inc)
)

# ---- Toon & download ------------------------------------ #
st.markdown("### Voorvertoning")
st.components.v1.html(html_filled, height=900, scrolling=True)

# Genereer PDF via weasyprint (werkt lokaal / Streamlit Cloud)
if st.button("Download PDF"):
    try:
        from weasyprint import HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            HTML(string=html_filled, base_url=os.getcwd()).write_pdf(tmp.name)
            pdf_bytes = Path(tmp.name).read_bytes()
        st.download_button("⬇️  Offerte PDF", pdf_bytes,
                           file_name=f"Offerte_{offnr}.pdf",
                           mime="application/pdf")
    except Exception as e:
        st.error(f"PDF-generatie mislukt: {e}")
        st.download_button("⬇️  Offerte HTML", html_filled,
                           file_name=f"Offerte_{offnr}.html",
                           mime="text/html")
