#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – Streamlit offerte-generator
PDF-export via pyppeteer (eigen Chromium, geen system-libs nodig)
"""

# ────────────────────────────────────────────────────────────────────────────
# -- Imports
# ────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import asyncio, io, json, sys

import streamlit as st
import pandas as pd
from pyppeteer import launch       # installeert/gebruik eigen Chromium

SELF_PATH = Path(__file__).resolve()

# ────────────────────────────────────────────────────────────────────────────
# -- Hulpfuncties
# ────────────────────────────────────────────────────────────────────────────
def eur(val: float | Decimal) -> str:
    """Formatteer als € 1.234,56 (NL-notatie)"""
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"

def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"

STAFFELS = [1000, 2000, 5000, 7500, 10000, 50000]
def _staffel(a: int) -> int:
    """Geef Excel-achtig staffel-breakpoint terug (IF a<2000 → 1000 …)"""
    if a < 2000:   return 1000
    if a < 5000:   return 2000
    if a < 7500:   return 5000
    if a < 10000:  return 7500
    if a < 50000:  return 10000
    return 50000

# Kostprijs-tabel (exact overgenomen):
TAB_COST = {
    "3D": {
        1000: 2.79, 2000: 1.63, 5000: 1.09,
        7500: 0.97, 10000: 0.91, 50000: 0.75,
    },
    "B1": {                       # Bedrukt - 1 kleur
        1000: 2.07, 2000: 1.94, 5000: 1.38,
        7500: 1.36, 10000: 1.27, 50000: 1.20,
    },
    "B2": {                       # Bedrukt - 2 kleuren
        1000: 2.37, 2000: 2.15, 5000: 1.51,
        7500: 1.48, 10000: 1.35, 50000: 1.24,
    },
    "B3": {                       # Bedrukt - 3 kleuren
        1000: 2.57, 2000: 2.31, 5000: 1.61,
        7500: 1.57, 10000: 1.43, 50000: 1.28,
    },
}

def kostprijs(typ: str, aant: int, kleuren: int = 0) -> float:
    key = "3D" if typ == "3D-logo" else f"B{kleuren}"
    return TAB_COST[key][_staffel(aant)]

def verkoopprijs(kost: float, verh_pct: float, kort_pct: float) -> float:
    return kost * (1 + verh_pct / 100) * (1 - kort_pct / 100)

# PDF-helper  ───────────────────────────────────────────────────────────────
async def _html2pdf_async(html: str) -> bytes:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setContent(html, waitUntil="networkidle0")
    pdf = await page.pdf(
        format="A4",
        printBackground=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    await browser.close()
    return pdf

def html_to_pdf_bytes(html: str) -> bytes:
    return asyncio.get_event_loop().run_until_complete(_html2pdf_async(html))

# ────────────────────────────────────────────────────────────────────────────
# -- Streamlit UI
# ────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# Hoofdoptie ---------------------------------------------------------------
st.header("Hoofdoptie")
c1, c2 = st.columns(2)
with c1:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal", 1, value=1000, step=50)

with c2:
    product_type   = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal = st.selectbox("Aantal kleuren", [1, 2, 3],
                                  disabled=(product_type != "Bedrukt"))
    kleur_bandje = st.selectbox(
        "Kleur bandje",
        ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"],
        index=2  # default Zwart
    )
    korting_pct   = st.number_input("Korting (%)", 0.0, 100.0, 0.0, step=0.5)
    verhoging_pct = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0,
                                    step=0.5)

opties_aantal = st.number_input("Aantal opties (1-4)", 1, 4, 1, step=1)

# Extra opties ------------------------------------------------------------
extra_opties = []
if opties_aantal > 1:
    st.header("Extra opties")
    for i in range(2, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            a = st.number_input("Aantal", 1, value=500, key=f"ex_aantal_{i}")
        with d2:
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"],
                             key=f"ex_type_{i}")
        with d3:
            kc = 0
            if t == "Bedrukt":
                kc = st.selectbox("Kleuren", [1, 2, 3], key=f"ex_kc_{i}")
        with d4:
            kband = st.selectbox(
                "Kleur bandje",
                ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"],
                key=f"ex_band_{i}",
            )
        kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0, 0.5,
                               key=f"ex_kort_{i}")
        extra_opties.append(
            dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort)
        )

# ────────────────────────────────────────────────────────────────────────────
# -- Berekeningen
# ────────────────────────────────────────────────────────────────────────────
rows: list[str] = []
total_excl = Decimal(0)

def add_row(a: int, t: str, band: str, oms: str, prijs: float) -> None:
    global total_excl
    rows.append(
        f"<tr><td>{a}</td><td>{t}</td><td>{band}</td>"
        f"<td>{oms}</td>"
        f"<td style='text-align:right;'>{eur(prijs)}</td>"
        f"<td style='text-align:right;'>{eur(Decimal(prijs)*a)}</td></tr>"
    )
    total_excl += Decimal(prijs) * a

# hoofdoptie
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
oms = tampon_omschrijving(kleuren_aantal) if product_type == "Bedrukt" \
      else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
add_row(aantal, product_type, kleur_bandje, oms, vp)

# extra opties
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = tampon_omschrijving(opt["kleuren"]) if opt["type"] == "Bedrukt" \
          else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    add_row(opt["aantal"], opt["type"], opt["band"], oms, vp)

# Speciale kleur of transport
special = kleur_bandje.lower() == "special" or any(
    o["band"].lower() == "special" for o in extra_opties
)
if special:
    add_row(1, "Extra", "Special",
            "Voor afwijkende kleurkeuze (‘Special’ bandje)", 480)
if aantal > 10000:
    add_row(1, "Verzendkosten", "–", "Extra kosten voor zending", 150)

btw        = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# ────────────────────────────────────────────────────────────────────────────
# -- HTML template (volledige VBA-layout)
# ────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = (SELF_PATH.parent / "template_calix.html")
if not HTML_TEMPLATE.exists():
    # Eerste run: schrijf template naar disk zodat je ’m kunt aanpassen
    HTML_TEMPLATE.write_text(
        """<!DOCTYPE html><html lang='nl'><head>
<meta charset='utf-8'><title>Offerte Calix</title>
<!-- VOLLEDIGE CSS UIT JE VBA  -->
<style>
@page{size:A4;margin:0;}
/* … alle CSS uit de VBA-macro (header, footer, tables, etc.) … */
</style></head><body>

<!-- ====== Pagina 1 ====== -->
<div class='page'>
<div class='header'>
<div class='header-top'><span class='header-brand'>CALIX</span>
<span class='header-text'>HANDS FREE DANCING</span></div>
<div class='header-divider'></div>
<img src='Tilted SIO 2 - PNG.png' style='position:absolute;top:23px;right:40px;width:220px;'>
<h1>Cupholder voor: ${KLANT}</h1>
<p>Offertenummer: ${OFFNR}<br>Datum: ${DATUM} | Geldig tot: ${GELDIG}<br>Adres: ${ADRES}</p>
</div>

<div class='section'><h2>Welkom!</h2>
<p>Dank voor je interesse … enz.</p></div>

<!-- prijsindicatie tekst, identiek VBA -->
<div class='section'><h2>Toelichting op de prijsindicatie</h2>
<div style='background:#f9f9f9;padding:12px;border-radius:6px;'>
<ul>
<li><b>Product:</b> Calix bekerhouder, uitgevoerd in één kleur.</li>
<!-- … vul hier je volledige bullets in … -->
</ul>
<p><b>Disclaimer:</b> Aan deze prijsindicatie kunnen …</p>
</div></div>

<!-- Productoverzicht -->
<div class='section'><h2>Productoverzicht</h2>
<table class='prod'>
<tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
<th style='text-align:right;'>Prijs/stuk</th><th style='text-align:right;'>Totaal excl. btw</th></tr>
${PRODUCTROWS}
</table>

<div class='totals-separator'></div>
<table class='totals'>
<tr><td class='label'>Totaal excl. btw:</td><td class='value'>${TOTALEXCL}</td></tr>
<tr><td class='label'>BTW (21&nbsp;%):</td><td class='value'>${BTW}</td></tr>
</table>
<div class='totalbar'></div>
<table class='totals'>
<tr><td class='label total-bold'>Totaal incl. btw:</td>
<td class='value total-bold'>${TOTAALINC}</td></tr></table>
</div>

<!-- footer pagina 1 (identiek VBA) -->
<div class='footer-fixed'>
<!-- … -->
</div></div>

<!-- ====== Pagina 2 (visuals, extra opties, QR, footer) ====== -->
<!-- Plaats hier exact je tweede pagina HTML uit VBA … -->

</body></html>""",
        encoding="utf-8"
    )
    st.warning("Template is aangemaakt als 'template_calix.html'. "
               "Pas daar je volledige HTML/CSS aan en herlaad.")
    st.stop()

template_src = HTML_TEMPLATE.read_text(encoding="utf-8")
from string import Template as StrTemplate
html_out = StrTemplate(template_src).safe_substitute(
    KLANT=klant or "–",
    ADRES=adres or "–",
    OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl),
    BTW=eur(btw),
    TOTAALINC=eur(totaal_inc),
)

# ────────────────────────────────────────────────────────────────────────────
# -- Download-knoppen en preview
# ────────────────────────────────────────────────────────────────────────────
st.download_button("Download HTML", data=html_out,
                   file_name="offerte_calix.html", mime="text/html")
st.components.v1.html(html_out, height=900, scrolling=True)

try:
    pdf_bytes = html_to_pdf_bytes(html_out)
    st.download_button("Download PDF", data=pdf_bytes,
                       file_name="offerte_calix.pdf", mime="application/pdf")
except Exception as e:
    st.warning(
        f"Kon PDF niet genereren ({e}). "
        "Download de HTML en print die als PDF in je browser."
    )
