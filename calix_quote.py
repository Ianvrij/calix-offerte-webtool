# calix_quote.py
# --------------------------------------------------------
# Streamlit-webtool om Calix-offertes te maken (HTML + PDF)
# VBA-logica 1-op-1 overgenomen – alleen de UI is Streamlit
# --------------------------------------------------------
from __future__ import annotations
import json
import math
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
from jinja2 import Template

# ─────────────────────────────────────────────────────────
# CONSTANTEN
# ─────────────────────────────────────────────────────────
TEMPLATE_PATH = Path(__file__).with_name("template.html")

KLEUR_KEUZES = ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"]
TYPE_KEUZES  = ["3D-logo", "Bedrukt"]
KLEUR_AANTAL = [1, 2, 3]

# Excel-achtige prijs-tabellen ------------------------------------------------
# (Eenvoudig gehouden; vervang dit door exacte lookup-tabellen indien nodig)
SPUITGIET_PRIJZEN = [
    (2000, 2.79),
    (5000, 1.63),
    (10000, 1.09),
    (float("inf"), 0.75),
]
TAMPON_PRIJZEN = {               # per aantal kleuren
    1: [(2000, 2.07), (5000, 1.94), (10000, 1.38), (float("inf"), 1.20)],
    2: [(2000, 2.37), (5000, 2.15), (10000, 1.51), (float("inf"), 1.24)],
    3: [(2000, 2.57), (5000, 2.31), (10000, 1.61), (float("inf"), 1.28)],
}
TRANSPORT_KOSTEN = 150          # bij > 9 999 stuks
SPECIAL_TOESLAG = 480           # per offerte (niet per stuk)

def lookup(prijstabel: list[tuple[int, float]], aantal: int) -> float:
    """Zoek prijs/stuk op in een eenvoudig (max)-intervaltabel."""
    for grens, prijs in prijstabel:
        if aantal <= grens:
            return prijs
    return prijstabel[-1][1]  # fallback (zou niet voorkomen)


# ─────────────────────────────────────────────────────────
# HULPFUNCTIES
# ─────────────────────────────────────────────────────────
def eur(x: float) -> str:
    return f"€ {x:,.2f}".replace(",", " ").replace(".", ",")

def bereken_kost_verkoop(
    aantal: int,
    prodtype: str,
    kleuren: int|None,
    extra_pct: float,
    korting_pct: float,
    special: bool,
) -> dict[str, float]:
    """Geeft kostprijs, verkoopprijs en winst (per stuk) + totaal terug."""
    if prodtype.lower() == "3d-logo":
        cost = lookup(SPUITGIET_PRIJZEN, aantal)
    else:  # Bedrukt
        cost = lookup(TAMPON_PRIJZEN[kleuren], aantal)

    sell = cost * (1 + extra_pct/100)       # verhoging
    sell *= (1 - korting_pct/100)           # korting

    winst = sell - cost
    totaal_cost = cost * aantal
    totaal_sell = sell * aantal
    totaal_winst = winst * aantal

    return dict(
        kost=cost, verkoop=sell, winst=winst,
        tot_kost=totaal_cost, tot_sell=totaal_sell, tot_winst=totaal_winst,
        special=special,
    )

def gen_html(context: dict) -> str:
    """Vul het Jinja2-sjabloon met alle waarden."""
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.render(**context)

def build_pdf(html: str) -> bytes:
    """Converteer HTML → PDF via wkhtmltopdf."""
    import pdfkit                                    # lazy-import
    pdf_bin = pdfkit.configuration()                 # laat pdfkit zelf wkhtmltopdf zoeken
    return pdfkit.from_string(html, False, configuration=pdf_bin)


# ─────────────────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────────────────
st.set_page_config("Calix offerte", "🧾", layout="wide")
st.title("🧾 Calix offertegenerator")

with st.form("offerte_hoofding"):
    st.subheader("Hoofdgegevens")
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")

    col1, col2, col3 = st.columns(3)
    with col1:
        aantal = st.number_input("Aantal", min_value=1, value=1000, step=1)
    with col2:
        prodtype = st.selectbox("Type", TYPE_KEUZES, index=0)
    with col3:
        kleuren = None
        if prodtype == "Bedrukt":
            kleuren = st.selectbox("Aantal kleuren (alleen bij Bedrukt)", KLEUR_AANTAL)

    kleur_bandje = st.selectbox("Kleur bandje", KLEUR_KEUZES, index=2)

    col1, col2, col3 = st.columns(3)
    with col1:
        extra_pct = st.number_input("Verhoging (Extra %)", min_value=0.0, value=10.0, step=0.1)
    with col2:
        korting_pct = st.number_input("Korting %", min_value=0.0, value=0.0, step=0.1)
    with col3:
        opties_aantal = st.number_input("Aantal opties (extra offertes)", 1, 4, 1, 1)

    st.form_submit_button("Bewaar hoofding", type="primary")

# ── Extra opties ────────────────────────────────────────────────────────────
extra_opties: list[dict] = []
if opties_aantal > 1:
    st.subheader("Extra opties")
    for i in range(2, int(opties_aantal)+1):
        with st.expander(f"Optie {i}", expanded=False):
            col = st.columns(4)
            with col[0]:
                a = st.number_input(f"Aantal optie {i}", min_value=1, value=5000, key=f"a_{i}")
            with col[1]:
                t = st.selectbox(f"Type optie {i}", TYPE_KEUZES, key=f"t_{i}")
            with col[2]:
                kclr = None
                if t == "Bedrukt":
                    kclr = st.selectbox(f"Kleuren {i}", KLEUR_AANTAL, key=f"kclr_{i}")
            with col[3]:
                kband = st.selectbox(f"Kleur bandje {i}", KLEUR_KEUZES, key=f"band_{i}")
            krt = st.number_input(f"Korting % optie {i}", 0.0, 100.0, 0.0, 0.1, key=f"kr_{i}")

            extra_opties.append(dict(aantal=a, type=t, kleuren=kclr,
                                     band=kband, korting=krt))

# ── Berekeningen ────────────────────────────────────────────────────────────
special_main   = kleur_bandje.lower() == "special"
all_rows       = []

main_res = bereken_kost_verkoop(
    aantal, prodtype, kleuren, extra_pct, korting_pct, special_main
)
all_rows.append(dict(row=1, **main_res,
                     aantal=aantal, type=prodtype, kleuren=kleuren,
                     band=kleur_bandje))

for idx, opt in enumerate(extra_opties, start=2):
    res = bereken_kost_verkoop(
        opt["aantal"], opt["type"], opt["kleuren"],
        extra_pct, opt["korting"], opt["band"].lower()=="special"
    )
    all_rows.append(dict(row=idx, **res,
                         aantal=opt["aantal"], type=opt["type"],
                         kleuren=opt["kleuren"], band=opt["band"]))

# ── Totalen & toeslagen ─────────────────────────────────────────────────────
total_excl = sum(r["tot_sell"] for r in all_rows)
btw        = total_excl * 0.21
totaal_inc = total_excl + btw

special_toeslag = SPECIAL_TOESLAG if any(r["special"] for r in all_rows) else 0
transport       = TRANSPORT_KOSTEN if any(r["aantal"] > 9_999 for r in all_rows) else 0

total_excl += special_toeslag + transport
btw         = total_excl * 0.21
totaal_inc  = total_excl + btw

# ── HTML-generatie ──────────────────────────────────────────────────────────
context = dict(
    KLANT=klant,
    ADRES=adres,
    OFFNR=offnr,
    DATUM=datetime.today().strftime("%d-%m-%Y"),
    GELDIG=(datetime.today()+timedelta(days=14)).strftime("%d-%m-%Y"),
    RIJEN=all_rows,
    SPECIAL_TOESLAG=special_toeslag,
    TRANSPORT=transport,
    TOTALEXCL=eur(total_excl),
    BTW=eur(btw),
    TOTAALINC=eur(totaal_inc),
)
html_out = gen_html(context)

st.download_button("Download HTML", html_out, "offerte.html", "text/html")

try:
    pdf_bytes = build_pdf(html_out)
    st.download_button("Download PDF", pdf_bytes, "offerte.pdf", "application/pdf")
except Exception as e:
    st.info("PDF-generatie niet beschikbaar – download HTML en print als PDF.")
    st.exception(e)
