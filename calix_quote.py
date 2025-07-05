# ───────────────────────────────────────────────────────────────────────────────
#  Calix – Streamlit offertetool  ·  identicale HTML/PDF-output als VBA-macro
# ───────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import tempfile
import base64
import json

# probeer WeasyPrint; als de nodige GTK/Pango-libs ontbreken, val terug op HTML-download
try:
    from weasyprint import HTML    # type: ignore
    WEASY = True
except Exception:
    WEASY = False

# ── constante data uit de originele Excel-tabellen ────────────────────────────
BRACKETS = [1000, 2000, 5000, 7500, 10000, 50000]

KOSTPRIJS = {
    "3D":              [2.79, 1.63, 1.09, 0.97, 0.91, 0.75],
    "bedrukt_1":       [2.07, 1.94, 1.38, 1.36, 1.27, 1.20],
    "bedrukt_2":       [2.37, 2.15, 1.51, 1.48, 1.35, 1.24],
    "bedrukt_3":       [2.57, 2.31, 1.61, 1.57, 1.43, 1.28],
}

VERKOOPPRIJS = {
    "3D":              [3.00, 2.13, 1.54, 1.65, 1.55, 1.15],
    "bedrukt_1":       [2.80, 2.40, 2.00, 1.80, 1.70, 1.50],
    "bedrukt_2":       [2.90, 2.50, 2.10, 1.90, 1.80, 1.40],
    "bedrukt_3":       [3.00, 2.60, 2.20, 2.00, 1.90, 1.50],
}

KLEUR_KEUZES = ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"]

# ── helpers ────────────────────────────────────────────────────────────────────
def eur(x: float | Decimal) -> str:
    """€-weergave met twee decimalen, NL-notatie."""
    x = Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def bracket_index(aantal: int) -> int:
    """Geeft index 0-5 op basis van aantallen."""
    for i, br in enumerate(BRACKETS):
        if aantal <= br:
            return i
    return len(BRACKETS) - 1

def base_keys(tp: str, kleuren: int) -> tuple[str, str]:
    """Retourneert key voor kost- en verkooptabellen."""
    if tp.lower() == "3d-logo":
        return "3D", "3D"
    return f"bedrukt_{kleuren}", f"bedrukt_{kleuren}"

def pdf_from_html(html: str, filename: str) -> bytes | None:
    if not WEASY:
        return None
    tmp_html = Path(tempfile.mkstemp(suffix=".html")[1])
    tmp_html.write_text(html, encoding="utf-8")
    pdf_bytes = HTML(tmp_html.as_uri()).write_pdf()
    tmp_html.unlink(missing_ok=True)
    return pdf_bytes

# ── Streamlit interface ────────────────────────────────────────────────────────
st.set_page_config("Calix Offertegenerator", layout="wide")
st.title("Calix Offertegenerator")

with st.form("hoofd"):
    st.subheader("Hoofdgegevens")
    col1, col2 = st.columns(2)
    with col1:
        klant = st.text_input("Naam klant")
        adres = st.text_area("Adres (één regel of meerdere)")
        offnr = st.text_input("Offertenummer")
    with col2:
        aantal = st.number_input("Aantal", min_value=1, step=1, value=1000)
        tp = st.selectbox("Type", ["3D-logo", "Bedrukt"])
        kleuren = 0
        if tp == "Bedrukt":
            kleuren = st.selectbox("Aantal kleuren (tampondruk)", [1, 2, 3])
        verhoging = st.number_input("Verhoging Extra % (bijv. 10 = +10 %)", value=0.0)
        korting = st.number_input("Korting % (bijv. 5 = -5 %)", min_value=0.0, value=0.0)
    opties = st.number_input("Aantal opties (extra regels)", min_value=1, max_value=4, value=1)

    st.markdown("---")
    st.subheader("Extra opties")
    extra_opties: list[dict] = []
    for i in range(1, int(opties)):
        st.markdown(f"**Optie {i}**")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            a_opt = st.number_input("Aantal", min_value=1, step=1, key=f"aantal_{i}")
        with c2:
            t_opt = st.selectbox("Type", ["3D-logo", "Bedrukt"], key=f"type_{i}")
        with c3:
            k_opt = 0
            if t_opt == "Bedrukt":
                k_opt = st.selectbox("Kleuren", [1, 2, 3], key=f"kleuren_{i}")
        with c4:
            b_opt = st.selectbox("Kleur bandje", KLEUR_KEUZES, key=f"band_{i}")
        with c5:
            d_opt = st.number_input("Korting %", min_value=0.0, key=f"korting_{i}")
        extra_opties.append(
            {"aantal": a_opt, "type": t_opt, "kleuren": k_opt, "band": b_opt, "korting": d_opt}
        )

    submit = st.form_submit_button("Genereer offerte")

# ── logica & output ────────────────────────────────────────────────────────────
if submit:
    # hoofdregel berekening
    idx = bracket_index(aantal)
    kost_key, verkoop_key = base_keys(tp, kleuren if tp == "Bedrukt" else 0)
    kostprijs = KOSTPRIJS[kost_key][idx]
    verkoop = VERKOOPPRIJS[verkoop_key][idx]

    verkoop *= (1 + verhoging / 100) * (1 - korting / 100)

    regels = [{
        "aantal": aantal,
        "type": tp,
        "kleur": "Standaard" if tp == "3D-logo" else ("Standaard" if kleuren == 0 else f"{kleuren}-clr"),
        "details": (
            "3D-logo inbegrepen, Inclusief Ontwerpcontrole" if tp == "3D-logo"
            else f"{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole"
        ),
        "prijs": verkoop,
        "totaal": verkoop * aantal
    }]

    totaal_excl = verkoop * aantal
    special_toeslag = 0
    verzendkosten = 150 if aantal > 10000 else 0

    # extra opties
    for opt in extra_opties:
        idx = bracket_index(opt["aantal"])
        k_key, v_key = base_keys(opt["type"], opt["kleuren"] if opt["type"] == "Bedrukt" else 0)
        pr = VERKOOPPRIJS[v_key][idx]
        pr *= (1 + verhoging / 100) * (1 - opt["korting"] / 100)
        regels.append({
            "aantal": opt["aantal"],
            "type": opt["type"],
            "kleur": opt["band"],
            "details": (
                "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
                if opt["type"] == "3D-logo"
                else f"{opt['kleuren']}-kleur tampondruk, Inclusief Ontwerpcontrole"
            ),
            "prijs": pr,
            "totaal": pr * opt["aantal"]
        })
        totaal_excl += pr * opt["aantal"]
        if opt["band"].lower() == "special":
            special_toeslag = 480

    totaal_excl += special_toeslag + verzendkosten
    btw = totaal_excl * 0.21
    totaal_inc = totaal_excl + btw

    # HTML-opbouw (precies gelijk aan VBA-string, maar met format-placeholders)
    html_template = Path(__file__).with_name("template.html").read_text(encoding="utf-8")

    def regel_html(r):
        return (
            f"<tr><td>{r['aantal']}</td><td>{r['type']}</td><td>{r['kleur']}</td>"
            f"<td>{r['details']}</td>"
            f"<td style='text-align:right;'>{eur(r['prijs'])}</td>"
            f"<td style='text-align:right;'>{eur(r['totaal'])}</td></tr>"
        )

    product_rows = "\n".join(regel_html(r) for r in regels)
    if special_toeslag:
        product_rows += (
            "<tr><td>1</td><td>Extra</td><td>Special</td>"
            "<td>Voor afwijkende kleurkeuze (‘Special’ bandje)</td>"
            f"<td style='text-align:right;'>{eur(480)}</td>"
            f"<td style='text-align:right;'>{eur(480)}</td></tr>"
        )
    if verzendkosten:
        product_rows += (
            "<tr><td>1</td><td>Verzendkosten</td><td>–</td>"
            "<td>Extra kosten voor zending</td>"
            f"<td style='text-align:right;'>{eur(150)}</td>"
            f"<td style='text-align:right;'>{eur(150)}</td></tr>"
        )

    html_out = html_template.format(
        KLANT=klant or "–",
        ADRES=adres.replace("\n", "<br>") or "–",
        OFFNR=offnr or "–",
        DATUM=datetime.now().strftime("%d-%m-%Y"),
        GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
        PRODUCTROWS=product_rows,
        TOTALEXCL=eur(totaal_excl),
        BTW=eur(btw),
        TOTAALINC=eur(totaal_inc),
    )

    st.success("Offerte gegenereerd!")

    # ── download knoppen ───────────────────────────────────────────────────────
    colA, colB = st.columns(2)
    with colA:
        b64 = base64.b64encode(html_out.encode()).decode()
        st.download_button(
            "Download HTML",
            data=b64,
            file_name=f"Offerte_{offnr or 'calix'}.html",
            mime="text/html",
        )
    with colB:
        if WEASY:
            pdf_bytes = pdf_from_html(html_out, f"Offerte_{offnr}.pdf")
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"Offerte_{offnr or 'calix'}.pdf",
                mime="application/pdf",
            )
        else:
            st.info(
                "PDF-conversie niet beschikbaar (WeasyPrint + GTK/Pango niet geïnstalleerd). "
                "Download de HTML en print die als PDF."
            )

    # ── live preview ──────────────────────────────────────────────────────────
    with st.expander("🔍 Voorbeeldweergave"):
        st.components.v1.html(html_out, height=900, scrolling=True)
