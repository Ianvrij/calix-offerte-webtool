#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator (Streamlit)
• HTML-preview in de app
• PDF-download (WeasyPrint of xhtml2pdf fallback)
Alle afbeeldingen worden inline (Base-64) in de HTML gezet → nooit meer
‘File not found’.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import base64
import io

import streamlit as st               #  pip install streamlit
# pandas heb je (nu) niet meer nodig – laat staan om data in te lezen

import pdfkit

@st.cache_resource
def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from weasyprint import HTML, __version__ as wv
        st.write(f"PDF-engine: WeasyPrint {wv}")   # zichtbaar in de app
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)   # toont fout in UI, geen app-crash
        return None



# ────────────────────────────────────────────────────────────────────────────
# PDF-helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from weasyprint import HTML, __version__ as WV
        st.write(f"PDF-engine: WeasyPrint {WV}")   # verschijnt in je app
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)        # nette foutmelding i.p.v. crash
        return None
                     # geen backend – user kan HTML printen


# ────────────────────────────────────────────────────────────────────────────
# Formatters & helpers
# ---------------------------------------------------------------------------
def eur(val: float | Decimal) -> str:
    """€-notatie met , als decimaalteken en . als duizend-scheiding."""
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"


def b64_img(filename: str) -> str:
    """Geef data-URI voor lokaal plaatje; werkt overal (ook Streamlit Cloud)."""
    p = Path(__file__).with_name(filename)
    mime = "image/png" if filename.lower().endswith("png") else "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


# ────────────────────────────────────────────────────────────────────────────
# Streamlit-UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# HTML-template laden (de placeholders worden straks ingevuld)
template_path = Path(__file__).with_name("template.html")
template = Template(template_path.read_text(encoding="utf-8"))

# ▸ Hoofdoptie
st.header("Hoofdoptie")
cA, cB = st.columns(2)
with cA:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal", min_value=1, value=1000)
with cB:
    product_type     = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal   = st.selectbox("Aantal kleuren", [1, 2, 3],
                                     disabled=(product_type != "Bedrukt"))
    kleurkeuzes      = ["Standaard", "Special", "Zwart",
                        "Off White", "Blauw", "Rood"]
    kleur_bandje     = st.selectbox("Kleur bandje", kleurkeuzes, index=2)
    korting_pct      = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
    verhoging_pct    = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal extra opties (0–3)", 0, 3, 0)

# ▸ Extra opties
extra_opties: list[dict] = []
if opties_aantal:
    st.header("Extra opties")
    for i in range(1, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            a = st.number_input("Aantal", 1, key=f"opt_aantal_{i}")
        with c2:
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"],
                             key=f"opt_type_{i}")
        with c3:
            kc = st.selectbox("Kleuren", [1, 2, 3],
                              disabled=(t != "Bedrukt"), key=f"opt_kc_{i}")
        with c4:
            kband = st.selectbox("Bandje-kleur", kleurkeuzes,
                                 index=0, key=f"opt_band_{i}")
        kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0,
                               key=f"opt_kort_{i}")
        extra_opties.append(dict(aantal=a, type=t,
                                 kleuren=kc, band=kband, korting=kort))

st.divider()

# ────────────────────────────────────────────────────────────────────────────
# Prijstabellen – rechtstreeks uit Excel overgenomen
# ---------------------------------------------------------------------------
prijs = {
    "3D": {
        1000: 2.79, 2000: 1.63, 5000: 1.09,
        7500: 0.97, 10000: 0.91, 50000: 0.75,
    },
    "Bedrukt1": {
        1000: 2.07, 2000: 1.94, 5000: 1.38,
        7500: 1.36, 10000: 1.27, 50000: 1.20,
    },
    "Bedrukt2": {
        1000: 2.37, 2000: 2.15, 5000: 1.51,
        7500: 1.48, 10000: 1.35, 50000: 1.24,
    },
    "Bedrukt3": {
        1000: 2.57, 2000: 2.31, 5000: 1.61,
        7500: 1.57, 10000: 1.43, 50000: 1.28,
    },
}
staffels = sorted(prijs["3D"])


def _staffel(a: int) -> int:
    """Pak dichtsbijzijnde staffel uit de tabel."""
    return min(staffels, key=lambda x: abs(x - a))


def kostprijs(typ: str, aant: int, kl: int) -> float:
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return prijs[key][_staffel(aant)]


def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh / 100) * (1 - kort / 100)


# ────────────────────────────────────────────────────────────────────────────
# Berekeningen
# ---------------------------------------------------------------------------
rows: list[str] = []
total_excl: Decimal = Decimal(0)


def append_row(a: int, t: str, kband: str, stprijs: float, oms: str) -> None:
    """Voeg een rij aan de product-tabel toe + tel op bij totaal."""
    global total_excl
    rows.append(f"""
<tr><td>{a}</td><td>{t}</td><td>{kband}</td>
<td>{oms}</td><td style="text-align:right;">{eur(stprijs)}</td>
<td style="text-align:right;">{eur(stprijs * a)}</td></tr>""")
    total_excl += Decimal(stprijs * a)


# ▸ hoofdoptie
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = tampon_omschrijving(kleuren_aantal) \
    if product_type == "Bedrukt" else \
    "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
append_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# ▸ extra opties
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = tampon_omschrijving(opt["kleuren"]) \
        if opt["type"] == "Bedrukt" else \
        "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    append_row(opt["aantal"], opt["type"], opt["band"], vp, oms)

# ▸ toeslagen
special = (kleur_bandje.lower() == "special" or
           any(o["band"].lower() == "special" for o in extra_opties))
if special:
    append_row(1, "Extra", "Special", 480,
               "Voor afwijkende kleurkeuze (‘Special’ bandje)")

if aantal > 10000:
    append_row(1, "Verzendkosten", "–", 150, "Extra kosten voor zending")

# totaal & BTW
btw        = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# ────────────────────────────────────────────────────────────────────────────
# HTML genereren
# ---------------------------------------------------------------------------
img_dict = {
    "IMG_SIO2": b64_img("Tilted SIO 2 - PNG.png"),
    "IMG_SIO1": b64_img("Tilted SIO 1 - PNG.png"),
    "IMG_PROD": b64_img("product.jpg"),
}

html_out = template.safe_substitute(
    KLANT=klant or "–",
    ADRES=adres or "–",
    OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl),
    BTW=eur(btw),
    TOTAALINC=eur(totaal_inc),
    **img_dict,
)

# ────────────────────────────────────────────────────────────────────────────
# Downloads & Preview
# ---------------------------------------------------------------------------
st.download_button("Download HTML", html_out,
                   file_name=f"offerte_{klant or 'calix'}.html",
                   mime="text/html")
st.components.v1.html(html_out, height=800, scrolling=True)

pdf_data = html_to_pdf_bytes(html_out)
if pdf_data:
    st.download_button("Download PDF", pdf_data,
                       file_name=f"offerte_{klant or 'calix'}.pdf",
                       mime="application/pdf")
else:
    st.info("PDF-backend niet beschikbaar. "
            "Download de HTML en print die in je browser naar PDF.")
