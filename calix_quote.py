#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator (Streamlit)
PDF-export: WeasyPrint  ► xhtml2pdf fallback
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import base64
import io

import streamlit as st


# ──────────────────────────────── PDF back-end ─────────────────────────────
def _detect_pdf_backend() -> str | None:
    """
    'weasy'  |  'pisa'  |  None
    Probeert óók even een dummy-render; zo vangen we ontbrekende
    systeem-libs (pango/cairo) af nog vóór Streamlit crasht.
    """
    try:
        from weasyprint import HTML                           # noqa
        try:                                                 # ← nieuw
            HTML(string="<b>test</b>").write_pdf()           # ← nieuw
        except Exception:                                    # ← nieuw
            raise ImportError                                # ← nieuw
        return "weasy"
    except Exception:                                        # pragma: no cover
        try:
            from xhtml2pdf import pisa  # noqa
            return "pisa"
        except Exception:                                    # pragma: no cover
            return None


PDF_BACKEND = _detect_pdf_backend()


def html_to_pdf_bytes(html: str, base_dir: Path) -> bytes | None:
    """Render HTML → PDF (bytes).  Geeft None terug als geen backend beschikbaar is."""
    if PDF_BACKEND == "weasy":
        from weasyprint import HTML
        try:
            return HTML(string=html, base_url=base_dir.as_uri()).write_pdf()
        except Exception:
            # WeasyPrint faalt alsnog → probeer pisã
            pass                                             # ← nieuw

    if PDF_BACKEND in (None, "pisa"):
        try:
            from xhtml2pdf import pisa
            result = io.BytesIO()

            def _link_cb(uri, rel):
                return (base_dir / uri).resolve().as_posix()

            pisa.CreatePDF(io.StringIO(html), dest=result, encoding="utf-8",
                           link_callback=_link_cb)
            return result.getvalue()
        except Exception:                                    # pragma: no cover
            return None

    return None


# ──────────────────────────────── helpers ───────────────────────────────────
KLEURBANDJE_CHOICES = ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"]

def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"


def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"


# ──────────────────────────────── Streamlit UI ─────────────────────────────
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

SELF_PATH = Path(__file__).resolve()
TEMPLATE_PATH = SELF_PATH.with_name("template.html")
TEMPLATE = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))

# -------------------------- hoofdoptie -------------------------------------
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
    kleur_bandje = st.selectbox("Kleur bandje", KLEURBANDJE_CHOICES,
                                index=KLEURBANDJE_CHOICES.index("Zwart"))
    korting_pct   = st.number_input("Korting (%)",     0.0, 100.0, 0.0)
    verhoging_pct = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal opties (1-4)", 1, 4, 1)

# -------------------------- extra opties -----------------------------------
extra_opties: list[dict] = []
if opties_aantal > 1:
    st.header("Extra opties")
    for i in range(2, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            a = st.number_input("Aantal", 1, key=f"opt_aantal_{i}")
        with c2:
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"], key=f"opt_type_{i}")
        with c3:
            kc = 0
            if t == "Bedrukt":
                kc = st.selectbox("Kleuren", [1, 2, 3], key=f"opt_kc_{i}")
        with c4:
            kband = st.selectbox("Kleur bandje", KLEURBANDJE_CHOICES,
                                 index=0, key=f"opt_band_{i}")
        kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0, key=f"opt_kort_{i}")
        extra_opties.append(dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort))

# -------------------------- prijs­tabel uit Excel --------------------------
tab = {
    "3D":       {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97, 10000: 0.91, 50000: 0.75},
    "Bedrukt1": {1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36, 10000: 1.27, 50000: 1.20},
    "Bedrukt2": {1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48, 10000: 1.35, 50000: 1.24},
    "Bedrukt3": {1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57, 10000: 1.43, 50000: 1.28},
}
staffels = sorted(tab["3D"])

def _staffel(aantal: int) -> int:
    """kies dichtstbijzijnde staffel (zoals ‘benadering’ in Excel)."""
    return min(staffels, key=lambda s: abs(s - aantal))

def kostprijs(typ: str, aant: int, kl: int) -> float:
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return tab[key][_staffel(aant)]

def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh/100) * (1 - kort/100)

# -------------------------- berekeningen -----------------------------------
rows: list[str] = []
total_excl = Decimal("0")

def add_row(a: int, typ: str, kband: str, vp: float, oms: str) -> None:
    global total_excl
    rows.append(f"""
<tr>
  <td>{a}</td><td>{typ}</td><td>{kband}</td>
  <td>{oms}</td>
  <td style="text-align:right;">{eur(vp)}</td>
  <td style="text-align:right;">{eur(vp*a)}</td>
</tr>""")
    total_excl += Decimal(vp * a)

# hoofd­optie
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = tampon_omschrijving(kleuren_aantal) if product_type == "Bedrukt" \
               else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
add_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# extra opties
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = tampon_omschrijving(opt["kleuren"]) if opt["type"] == "Bedrukt" \
         else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    add_row(opt["aantal"], opt["type"], opt["band"], vp, oms)

# special / transport toeslagen
special = kleur_bandje.lower() == "special" or any(o["band"].lower() == "special" for o in extra_opties)
if special:
    add_row(1, "Extra", "Special", 480, "Voor afwijkende kleurkeuze (‘Special’ bandje)")
if aantal > 10000:
    add_row(1, "Verzendkosten", "–", 150, "Extra kosten voor zending")

btw        = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# -------------------------- HTML vullen ------------------------------------
html_out = TEMPLATE.safe_substitute(
    KLANT      = klant or "–",
    ADRES      = adres or "–",
    OFFNR      = offnr or "–",
    DATUM      = datetime.now().strftime("%d-%m-%Y"),
    GELDIG     = (datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS= "".join(rows),
    TOTALEXCL  = eur(total_excl),
    BTW        = eur(btw),
    TOTAALINC  = eur(totaal_inc)
)

# -------------------------- Downloads / preview ----------------------------
st.download_button("Download HTML", data=html_out,
                   file_name="offerte_calix.html", mime="text/html")

st.components.v1.html(html_out, height=800, scrolling=True)

pdf_bytes = html_to_pdf_bytes(html_out, SELF_PATH.parent)
if pdf_bytes:
    st.download_button("Download PDF", data=pdf_bytes,
                       file_name="offerte_calix.pdf", mime="application/pdf")
else:
    st.info("PDF-back-end niet beschikbaar – download de HTML en print die via je browser naar PDF.")
