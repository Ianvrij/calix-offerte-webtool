#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator (Streamlit)
PDF-uitvoer: ❶ WeasyPrint ❷ wkhtmltopdf/pdfkit ❸ headless-Chrome (pyppeteer) ❹ xhtml2pdf
De eerste backend die beschikbaar is wordt gebruikt; zo werkt het óók
op Streamlit Cloud waar libpango/wkhtmltopdf ontbreken.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from string import Template
import tempfile, asyncio, io, sys

import streamlit as st

# ──────────────────────────  BACKEND-DETECTIE  ────────────────────────── #
_BACKENDS: list[str] = []

try:                       # 1 – WeasyPrint (beste kwaliteit)
    from weasyprint import HTML  # noqa: F401
    _BACKENDS.append("weasy")
except Exception:
    pass

try:                       # 2 – wkhtmltopdf via pdfkit
    import pdfkit          # noqa: F401
    _BACKENDS.append("pdfkit")
except Exception:
    pass

try:                       # 3 – headless Chrome (pyppeteer)
    import pyppeteer       # noqa: F401
    _BACKENDS.append("chrome")
except Exception:
    pass

try:                       # 4 – xhtml2pdf (val tót slot)
    from xhtml2pdf import pisa  # noqa: F401
    _BACKENDS.append("pisa")
except Exception:
    pass


def html_to_pdf_bytes(html: str, base_dir: Path) -> bytes | None:
    """
    Render HTML → bytes(PDF) met de eerste beschikbare backend.
    `base_dir` is nodig voor WeasyPrint (relative URLs).
    """
    if not _BACKENDS:
        return None

    backend = _BACKENDS[0]

    # 1 WeasyPrint
    if backend == "weasy":
        from weasyprint import HTML
        return HTML(string=html, base_url=str(base_dir)).write_pdf()

    # 2 wkhtmltopdf / pdfkit
    if backend == "pdfkit":
        import pdfkit
        cfg = pdfkit.configuration()   # wkhtmltopdf moet in PATH staan
        return pdfkit.from_string(html, False,
                                  options={"quiet": ""}, configuration=cfg)

    # 3 headless Chrome via pyppeteer (werkt altijd, downloadt eigen Chrome)
    if backend == "chrome":
        import pyppeteer

        async def _do(html_str: str) -> bytes:
            # tijdelijke HTML-file → file:// URL (anders geen local CSS)
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                f.write(html_str.encode("utf-8"))
                url = f"file://{f.name}"

            browser = await pyppeteer.launch(args=["--no-sandbox"])
            page = await browser.newPage()
            await page.goto(url, {"waitUntil": "networkidle0"})
            pdf_bytes = await page.pdf(
                {"format": "A4", "printBackground": True})
            await browser.close()
            return pdf_bytes

        return asyncio.new_event_loop().run_until_complete(_do(html))

    # 4 xhtml2pdf (laatste redmiddel)
    if backend == "pisa":
        from xhtml2pdf import pisa
        result = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html), dest=result, encoding="utf-8")
        return result.getvalue()

    return None


# ─────────────────────────────  FORMATTERS  ────────────────────────────── #
EUR = "€ {}"


def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    txt = f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return EUR.format(txt)


def tampon_omschrijving(k: int) -> str:
    return ("1-kleur" if k == 1 else f"{k}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"


# ───────────────────────────  STREAMLIT  UI  ──────────────────────────── #
SELF_PATH = Path(__file__).resolve()
TEMPLATE = Template((SELF_PATH.parent / "template.html")
                    .read_text(encoding="utf-8"))

st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# == Hoofd­optie =========================================================== #
st.header("Hoofdoptie")
c1, c2 = st.columns(2)
with c1:
    klant = st.text_input("Naam klant")
    adres = st.text_input("Adres")
    offnr = st.text_input("Offertenummer")
    aantal = st.number_input("Aantal", 1, value=1000)

with c2:
    product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleuren_aantal = st.selectbox("Aantal kleuren", [0, 1, 2, 3],
                                  disabled=(product_type == "3D-logo"))
    kleur_bandje = st.selectbox(
        "Kleur bandje",
        ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"]
    )
    korting_pct = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
    verhoging_pct = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal extra opties (0-3)", 0, 3, 0)

# == Extra opties ========================================================== #
extra_opties: list[dict] = []
if opties_aantal:
    st.header("Extra opties")
    for i in range(1, opties_aantal + 1):
        st.subheader(f"Optie {i}")
        cc1, cc2, cc3 = st.columns(3)

        with cc1:
            a = st.number_input("Aantal", 1, key=f"aantal_{i}")
            t = st.selectbox("Type", ["Bedrukt", "3D-logo"],
                             key=f"type_{i}")
        with cc2:
            kc = st.selectbox("Kleuren", [0, 1, 2, 3],
                              key=f"kc_{i}", disabled=(t == "3D-logo"))
            band = st.selectbox("Kleur bandje",
                                ["Standaard", "Special", "Zwart",
                                 "Off White", "Blauw", "Rood"],
                                key=f"band_{i}")
        with cc3:
            kort = st.number_input("Korting (%)", 0.0, 100.0, 0.0,
                                   key=f"kort_{i}")

        extra_opties.append(
            dict(aantal=a, type=t, kleuren=kc, band=band, korting=kort)
        )

# == Prijs­tabellen (vast) ================================================= #
tab = {
    "3D": {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97,
           10000: 0.91, 50000: 0.75},
    "Bedrukt1": {1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36,
                 10000: 1.27, 50000: 1.20},
    "Bedrukt2": {1000: 2.37, 2000: 2.15, 5000: 1.51, 7500: 1.48,
                 10000: 1.35, 50000: 1.24},
    "Bedrukt3": {1000: 2.57, 2000: 2.31, 5000: 1.61, 7500: 1.57,
                 10000: 1.43, 50000: 1.28},
}
staffels = sorted(tab["3D"])


def _staf(a: int) -> int:
    """Dichtstbijzijnde staffel."""
    return min(staffels, key=lambda x: abs(x - a))


def kostprijs(typ: str, aant: int, kl: int) -> float:
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    return tab[key][_staf(aant)]


def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh / 100) * (1 - kort / 100)


# == Berekeningen ========================================================== #
rows: list[str] = []
total_excl = Decimal(0)

def add_row(a: int, t: str, band: str, vp: float, oms: str):
    global total_excl
    rows.append(
        f"<tr><td>{a}</td><td>{t}</td><td>{band}</td>"
        f"<td>{oms}</td>"
        f"<td style='text-align:right;'>{eur(vp)}</td>"
        f"<td style='text-align:right;'>{eur(vp * a)}</td></tr>"
    )
    total_excl += Decimal(vp * a)


# hoofd-product
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = (tampon_omschrijving(kleuren_aantal)
                if product_type == "Bedrukt"
                else "3D-logo inbegrepen, Inclusief Ontwerpcontrole")
add_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# extra opties
for opt in extra_opties:
    kp = kostprijs(opt["type"], opt["aantal"], opt["kleuren"])
    vp = verkoopprijs(kp, verhoging_pct, opt["korting"])
    oms = (tampon_omschrijving(opt["kleuren"])
           if opt["type"] == "Bedrukt"
           else "3D-logo inbegrepen, Inclusief Ontwerpcontrole")
    add_row(opt["aantal"], opt["type"], opt["band"], vp, oms)

# special / transport
special = (kleur_bandje.lower() == "special" or
           any(o["band"].lower() == "special" for o in extra_opties))
if special:
    add_row(1, "Extra", "Special", 480,
            "Voor afwijkende kleurkeuze (‘Special’ bandje)")

if aantal > 10000:
    add_row(1, "Verzendkosten", "–", 150, "Extra kosten voor zending")

btw = total_excl * Decimal("0.21")
totaal_inc = total_excl + btw

# == HTML genereren ======================================================== #
html_out = TEMPLATE.safe_substitute(
    KLANT=klant or "–",
    ADRES=adres or "–",
    OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl),
    BTW=eur(btw),
    TOTAALINC=eur(totaal_inc)
)

# == Streamlit-output ====================================================== #
st.download_button("Download HTML", html_out,
                   file_name="offerte_calix.html",
                   mime="text/html")

st.components.v1.html(html_out, height=900, scrolling=True)

pdf_bytes = html_to_pdf_bytes(html_out, SELF_PATH.parent)
if pdf_bytes:
    st.download_button("Download PDF", pdf_bytes,
                       file_name="offerte_calix.pdf",
                       mime="application/pdf")
else:
    st.warning(
        "Geen PDF-engine beschikbaar.\n"
        "Download de HTML en print naar PDF vanuit je browser."
    )
