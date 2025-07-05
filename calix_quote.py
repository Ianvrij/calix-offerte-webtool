#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator met PDF-fallback
Streamlit Cloud-proof: • WeasyPrint (als libCairo aanwezig) • anders xhtml2pdf
"""
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import io
import streamlit as st
import pandas as pd

# ── PDF helpers ────────────────────────────────────────────────────────────
def load_pdf_backend():
    """Probeer WeasyPrint, anders val terug op xhtml2pdf."""
    try:
        from weasyprint import HTML  # noqa: F401
        return "weasy"
    except Exception:
        try:
            from xhtml2pdf import pisa  # noqa: F401
            return "pisa"
        except Exception:                     # pragma: no cover
            return None

PDF_BACKEND = load_pdf_backend()

def html_to_pdf_bytes(html: str) -> bytes | None:
    """Render HTML → bytes(PDF) met beschikbare backend."""
    if PDF_BACKEND == "weasy":
        from weasyprint import HTML
        return HTML(string=html, base_url=".").write_pdf()
    if PDF_BACKEND == "pisa":
        from xhtml2pdf import pisa
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html), dest=result, encoding="utf-8")
        return result.getvalue()
    # geen backend
    return None


# ── Formatters ─────────────────────────────────────────────────────────────
EUR = "€ {}"
def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return EUR.format(f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"

# ── Streamlit-UI ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

template_path = Path(__file__).with_name("template.html")
template = Template(template_path.read_text(encoding="utf-8"))

# ── Invoer (hoofdoptie) ────────────────────────────────────────────────────
st.header("Hoofdoptie")
colA, colB = st.columns(2)
with colA:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal", 1, value=1000)
with colB:
    product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal = 0
    if product_type == "Bedrukt":
        kleuren_aantal = st.selectbox("Aantal kleuren", [1, 2, 3])
    kleur_bandje = st.text_input("Kleur bandje", value="Zwart")
    korting_pct  = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
    verhoging_pct= st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal opties (1-4)", 1, 4, 1)

# ── Extra opties ───────────────────────────────────────────────────────────
extra_opties = []
if opties_aantal > 1:
    st.header("Extra opties")
    for i in range(2, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            a = st.number_input(f"Aantal", 1, key=f"opt_aantal_{i}")
        with c2:
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"], key=f"opt_type_{i}")
        with c3:
            kc = 0
            if t == "Bedrukt":
                kc = st.selectbox("Kleuren", [1, 2, 3], key=f"opt_kc_{i}")
        with c4:
            kband = st.text_input("Kleur bandje", value="Standaard", key=f"opt_band_{i}")
        kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0, key=f"opt_kort_{i}")
        extra_opties.append(dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort))

# ── Prijs­tabellen (uit Excel) ─────────────────────────────────────────────
tab = {
    "3D":      {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97, 10000: 0.91, 50000: 0.75},
    "Bedrukt1":{1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36, 10000: 1.27, 50000: 1.20},
    "Bedrukt2":{1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48, 10000: 1.35, 50000: 1.24},
    "Bedrukt3":{1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57, 10000: 1.43, 50000: 1.28},
}
staffels = sorted(tab["3D"])

def kostprijs(typ:str, aant:int, kl:int) -> float:
    staf = min(staffels, key=lambda x: abs(x - aant))
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return tab[key][staf]

def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh/100) * (1 - kort/100)

# ── Berekeningen ───────────────────────────────────────────────────────────
rows, total_excl = [], Decimal(0)

def append_row(a, t, kband, vp, oms):
    global rows, total_excl
    rows.append(f"""
<tr><td>{a}</td><td>{t}</td><td>{kband}</td>
<td>{oms}</td><td style="text-align:right;">{eur(vp)}</td>
<td style="text-align:right;">{eur(vp*a)}</td></tr>""")
    total_excl += Decimal(vp * a)

# hoofd
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = tampon_omschrijving(kleuren_aantal) if product_type=="Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
append_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# extras
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = tampon_omschrijving(opt["kleuren"]) if opt["type"]=="Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    append_row(opt["aantal"], opt["type"], opt["band"], vp, oms)

# special & transport
special = kleur_bandje.lower()=="special" or any(o["band"].lower()=="special" for o in extra_opties)
if special:
    append_row(1, "Extra", "Special", 480, "Voor afwijkende kleurkeuze (‘Special’ bandje)")
if aantal > 10000:
    append_row(1, "Verzendkosten", "–", 150, "Extra kosten voor zending")

btw        = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# ── HTML samenstellen ──────────────────────────────────────────────────────
html_out = template.safe_substitute(
    KLANT=klant or "–", ADRES=adres or "–", OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl), BTW=eur(btw), TOTAALINC=eur(totaal_inc)
)

# ── Downloads / preview ────────────────────────────────────────────────────
st.download_button("Download HTML", html_out, "offerte.html", "text/html")
st.components.v1.html(html_out, height=800, scrolling=True)

pdf_data = html_to_pdf_bytes(html_out)
if pdf_data:
    st.download_button("Download PDF", pdf_data, "offerte.pdf", "application/pdf")
else:
    st.info("PDF-backend niet beschikbaar op dit platform. Download de HTML en print deze in je browser naar PDF.")

