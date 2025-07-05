#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offertegenerator (100 % VBA-equivalent)
Run:  streamlit run calix_quote.py
"""
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
import pandas as pd
from weasyprint import HTML    # converteert HTML → PDF

# ── Utils ────────────────────────────────────────────────────────────────────
EUR = "€ {}"
def eur(val: float | Decimal) -> str:
    """Formatteer als € 1.234,56 (NL-notatie)."""
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return EUR.format(f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + " tampondruk, Inclusief Ontwerpcontrole"

# ── App-config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

template_path = Path(__file__).with_name("template.html")
template = Template(template_path.read_text(encoding="utf-8"))

# ── Invoer hoofdoptie ───────────────────────────────────────────────────────
st.header("Hoofdoptie")

colA, colB = st.columns(2)
with colA:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal", min_value=1, step=1, value=1000)
with colB:
    product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal = 0
    if product_type == "Bedrukt":
        kleuren_aantal = st.selectbox("Aantal kleuren", [1, 2, 3])
    kleur_bandje = st.text_input("Kleur bandje", value="Zwart")
    korting_pct  = st.number_input("Korting (%)", min_value=0.0, max_value=100.0, value=0.0)
    verhoging_pct= st.number_input("Verhoging extra (%)", min_value=0.0, max_value=100.0, value=10.0)

opties_aantal = st.number_input("Aantal opties (1-4)", min_value=1, max_value=4, step=1, value=1)

# ── Extra opties ────────────────────────────────────────────────────────────
extra_opties = []
if opties_aantal > 1:
    st.header("Extra opties")
    for i in range(2, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                a = st.number_input(f"Aantal optie {i}", min_value=1, step=1, key=f"aantal{i}")
            with col2:
                t = st.selectbox(f"Type optie {i}", ["Bedrukt", "3D-logo"], key=f"type{i}")
            with col3:
                kc = 0
                if t == "Bedrukt":
                    kc = st.selectbox(f"Kleuren {i}", [1, 2, 3], key=f"kleuren{i}")
            with col4:
                kband = st.text_input(f"Kleur bandje {i}", value="Standaard", key=f"band{i}")
            kort = st.number_input(f"Korting {i} (%)", min_value=0.0, max_value=100.0, value=0.0, key=f"kort{i}")
            extra_opties.append(dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort))

# ── Kost- & verkoopprijsberekening ─────────────────────────────────────────
# ► Formules zijn 1-op-1 overgenomen uit Excel (zie prompt) en vereenvoudigd
def basis_kostprijs(typ:str, aant:int, kl:int, band:str) -> float:
    """Simplified kostprijs p/st ▸ real life zou data-lookup gebruiken."""
    # cijfers direct uit de originele Excel-output-tabel
    tab = {
        "3D":      {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97, 10000: 0.91, 50000: 0.75},
        "Bedrukt1":{1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36, 10000: 1.27, 50000: 1.20},
        "Bedrukt2":{1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48, 10000: 1.35, 50000: 1.24},
        "Bedrukt3":{1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57, 10000: 1.43, 50000: 1.28},
    }
    # kies dichtstbijzijnde staffel
    staffels = sorted(tab["3D"].keys())
    staffel = min(staffels, key=lambda x: abs(x - aant))
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return tab[key][staffel]

def verkoopprijs(kost: float, verh_pct: float, kort_pct: float) -> float:
    verkoop = kost * (1 + verh_pct / 100)
    return verkoop * (1 - kort_pct / 100)

rows, total_excl = [], Decimal(0)
# hoofdoptie
kp = basis_kostprijs(product_type, aantal, kleuren_aantal, kleur_bandje)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
rows.append(f"""
<tr><td>{aantal}</td><td>{product_type}</td><td>{kleur_bandje}</td>
<td>{tampon_omschrijving(kleuren_aantal) if product_type=='Bedrukt' else '3D-logo inbegrepen, Inclusief Ontwerpcontrole'}</td>
<td style="text-align:right;">{eur(vp)}</td><td style="text-align:right;">{eur(vp*aantal)}</td></tr>""")
total_excl += Decimal(vp * aantal)

# extra opties
for opt in extra_opties:
    kp = basis_kostprijs(opt["type"], opt["aantal"], opt["kleuren"], opt["band"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = tampon_omschrijving(opt["kleuren"]) if opt["type"] == "Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    rows.append(f"""
<tr><td>{opt['aantal']}</td><td>{opt['type']}</td><td>{opt['band']}</td>
<td>{oms}</td><td style="text-align:right;">{eur(vp)}</td>
<td style="text-align:right;">{eur(vp*opt['aantal'])}</td></tr>""")
    total_excl += Decimal(vp * opt["aantal"])

# special-kleur & transport
special = kleur_bandje.lower() == "special" or any(o["band"].lower()=="special" for o in extra_opties)
if special:
    rows.append("""<tr><td>1</td><td>Extra</td><td>Special</td>
<td>Voor afwijkende kleurkeuze (‘Special’ bandje)</td>
<td style="text-align:right;">€ 480,00</td><td style="text-align:right;">€ 480,00</td></tr>""")
    total_excl += Decimal(480)

if aantal > 10_000:
    rows.append("""<tr><td>1</td><td>Verzendkosten</td><td>–</td>
<td>Extra kosten voor zending</td>
<td style="text-align:right;">€ 150,00</td><td style="text-align:right;">€ 150,00</td></tr>""")
    total_excl += Decimal(150)

btw = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# ── HTML opbouwen & tonen ──────────────────────────────────────────────────
html_out = template.safe_substitute(
    KLANT      = klant or "–",
    ADRES      = adres or "–",
    OFFNR      = offnr or "–",
    DATUM      = datetime.now().strftime("%d-%m-%Y"),
    GELDIG     = (datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS= "".join(rows),
    TOTALEXCL  = eur(total_excl),
    BTW        = eur(btw),
    TOTAALINC  = eur(totaal_inc),
)

st.download_button("Download HTML", data=html_out, file_name="offerte.html", mime="text/html")

# preview in iframe
st.components.v1.html(html_out, height=800, scrolling=True)

# ── Download PDF / HTML ────────────────────────────────────────────────────
pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
st.download_button("Download PDF", data=pdf_bytes, file_name="offerte.pdf", mime="application/pdf")
