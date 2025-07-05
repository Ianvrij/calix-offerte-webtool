#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator met PDF-fallback
Streamlit Cloud-proof:  WeasyPrint ▸ pdfkit ▸ xhtml2pdf
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import io
import tempfile
import subprocess
import streamlit as st

# ────────────────────────────── PDF BACKEND DETECTIE ──────────────────────
def _detect_backends() -> list[str]:
    order: list[str] = []

    # 1) WeasyPrint  ────────────────────────────────────────────────────────
    try:
        from weasyprint import HTML  # noqa: F401
        # dummy probeert ≈ 1 kB PDF te renderen – mis je libpango, dan crasht het hier
        HTML(string="<b>test</b>").write_pdf()
        order.append("weasy")
    except Exception:
        pass

    # 2) pdfkit + wkhtmltopdf  ─────────────────────────────────────────────
    try:
        import pdfkit  # noqa: F401
        # check of binary aanwezig
        subprocess.run(["wkhtmltopdf", "-V"], check=True, capture_output=True)
        order.append("pdfkit")
    except Exception:
        pass

    # 3) xhtml2pdf  ────────────────────────────────────────────────────────
    try:
        from xhtml2pdf import pisa  # noqa: F401
        order.append("pisa")
    except Exception:
        pass
    return order


BACKENDS = _detect_backends()


def html_to_pdf_bytes(html: str, base_dir: Path) -> bytes | None:
    """Geef bytes(PDF) terug of None als geen enkele backend lukt."""
    for backend in BACKENDS:
        try:
            if backend == "weasy":
                from weasyprint import HTML
                return HTML(string=html,
                            base_url=base_dir.as_uri()).write_pdf()

            if backend == "pdfkit":
                import pdfkit
                with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                    pdfkit.from_string(html, tmp.name,
                                       options={"enable-local-file-access": ""})
                    return Path(tmp.name).read_bytes()

            if backend == "pisa":
                from xhtml2pdf import pisa
                result = io.BytesIO()

                def _link_cb(uri, rel):
                    return (base_dir / uri).resolve().as_posix()

                pisa.CreatePDF(io.StringIO(html), dest=result, encoding="utf-8",
                               link_callback=_link_cb)
                return result.getvalue()
        except Exception:
            continue  # probeer volgende backend
    return None


# ────────────────────────────── FORMATTERS ────────────────────────────────
def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {q:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def tampon_omschrijving(kleuren: int) -> str:
    return ("1-kleur" if kleuren == 1 else f"{kleuren}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"


# ────────────────────────────── STREAMLIT UI ──────────────────────────────
SELF_PATH = Path(__file__).resolve()
BASE_DIR  = SELF_PATH.parent
TEMPLATE  = Template((BASE_DIR / "template.html").read_text(encoding="utf-8"))

st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# ── Invoer – hoofdoptie ────────────────────────────────────────────────────
st.header("Hoofdoptie")
c1, c2 = st.columns(2)
with c1:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal", 1, value=1000)
with c2:
    typ     = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren = st.selectbox("Aantal kleuren", [0, 1, 2, 3],
                           index=0 if typ == "3D-logo" else 1,
                           disabled=(typ != "Bedrukt"))
    bandje  = st.selectbox("Kleur bandje",
                           ["Standaard", "Special", "Zwart",
                            "Off White", "Blauw", "Rood"])
    korting = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
    verhog  = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal extra opties (0-3)", 0, 3, 0)

# ── Extra opties ───────────────────────────────────────────────────────────
extra = []
if opties_aantal:
    st.header("Extra opties")
    for i in range(1, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            oaantal = st.number_input("Aantal", 1, key=f"oa_{i}")
        with d2:
            otyp    = st.selectbox("Type", ["Bedrukt", "3D-logo"], key=f"ot_{i}")
        with d3:
            okleur  = st.selectbox("Kleuren", [0, 1, 2, 3],
                                   index=0 if otyp == "3D-logo" else 1,
                                   disabled=(otyp != "Bedrukt"), key=f"ok_{i}")
        with d4:
            oband   = st.selectbox("Bandje",
                                   ["Standaard", "Special", "Zwart",
                                    "Off White", "Blauw", "Rood"],
                                   key=f"ob_{i}")
        okort   = st.number_input("Korting (%)", 0.0, 100.0, 0.0, key=f"oko_{i}")
        extra.append(dict(aantal=oaantal, typ=otyp,
                          kleuren=okleur, band=oband, korting=okort))

# ── Prijstabellen (uit Excel) ──────────────────────────────────────────────
PRIJSTABEL = {
    "3D":      {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97,
                10000: 0.91, 50000: 0.75},
    "B1":      {1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36,
                10000: 1.27, 50000: 1.20},
    "B2":      {1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48,
                10000: 1.35, 50000: 1.24},
    "B3":      {1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57,
                10000: 1.43, 50000: 1.28},
}
STAFFELS = sorted(PRIJSTABEL["3D"])


def _staffel(a: int) -> int:
    return min(STAFFELS, key=lambda s: abs(s - a))


def kost(typ_: str, a: int, kl: int) -> float:
    key = "3D" if typ_ == "3D-logo" else f"B{kl}"
    return PRIJSTABEL[key][_staffel(a)]


def vp(kp: float, vh: float, ko: float) -> float:
    return kp * (1 + vh/100) * (1 - ko/100)


# ── Berekening + tabelrijen ────────────────────────────────────────────────
rows, total_excl = [], Decimal(0)

def add_row(a: int, t: str, b: str, price: float, oms: str):
    global total_excl
    rows.append(f"""
<tr><td>{a}</td><td>{t}</td><td>{b}</td>
<td>{oms}</td>
<td style="text-align:right;">{eur(price)}</td>
<td style="text-align:right;">{eur(price*a)}</td></tr>""")
    total_excl += Decimal(price * a)

# hoofdoptie
kp = kost(typ, aantal, kleuren)
vprijs = vp(kp, verhog, korting)
oms = tampon_omschrijving(kleuren) if typ == "Bedrukt" else \
      "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
add_row(aantal, typ, bandje, vprijs, oms)

# extra
for ex in extra:
    kp = kost(ex["typ"], ex["aantal"], ex["kleuren"])
    vprijs = vp(kp, verhog, ex["korting"])
    oms = tampon_omschrijving(ex["kleuren"]) if ex["typ"] == "Bedrukt" else \
          "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    add_row(ex["aantal"], ex["typ"], ex["band"], vprijs, oms)

# special & transport
special = bandje.lower() == "special" or any(e["band"].lower() == "special" for e in extra)
if special:
    add_row(1, "Extra", "Special", 480,
            "Voor afwijkende kleurkeuze (‘Special’ bandje)")

if aantal > 10000:
    add_row(1, "Verzendkosten", "–", 150, "Extra kosten voor zending")

btw        = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# ── HTML vullen ────────────────────────────────────────────────────────────
html = TEMPLATE.safe_substitute(
    KLANT=klant or "–", ADRES=adres or "–", OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl), BTW=eur(btw), TOTAALINC=eur(totaal_inc)
)

# ── Downloads & preview ────────────────────────────────────────────────────
st.download_button("Download HTML", html, "offerte.html", "text/html")
st.components.v1.html(html, height=800, scrolling=True)

pdf_bytes = html_to_pdf_bytes(html, BASE_DIR)
if pdf_bytes:
    st.download_button("Download PDF", pdf_bytes,
                       f"offerte_{datetime.now():%Y%m%d}.pdf",
                       "application/pdf")
else:
    st.warning("PDF-backend ontbreekt.  Download de HTML en druk af naar PDF.")
