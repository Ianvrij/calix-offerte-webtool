import streamlit as st
from datetime import datetime, timedelta
from string import Template
from decimal import Decimal, ROUND_HALF_UP
import base64
from pathlib import Path

@st.cache_resource
def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from weasyprint import HTML, __version__ as WV
        st.write(f"PDF-engine: WeasyPrint {WV}")
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)
        return None

def eur(val: float | Decimal) -> str:
    """€-notatie met , als decimaalteken en . als duizend-scheiding."""
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return f"€ {q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def b64_img(filename: str) -> str:
    """Geef data-URI voor lokaal plaatje; werkt overal (ook Streamlit Cloud)."""
    p = Path(__file__).with_name(filename)
    mime = "image/png" if filename.lower().endswith("png") else "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"

# Streamlit Interface
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# Input voor klantgegevens
klant = st.text_input("Naam klant")
adres = st.text_input("Adres")
offnr = st.text_input("Offertenummer")
aantal = st.number_input("Aantal", min_value=1, value=1000)
product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])
kleuren_aantal = st.selectbox("Aantal kleuren", [1, 2, 3], disabled=(product_type != "Bedrukt"))
kleur_bandje = st.selectbox("Kleur bandje", ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"])
korting_pct = st.number_input("Korting (%)", 0.0, 100.0, 0.0)
verhoging_pct = st.number_input("Verhoging extra (%)", 0.0, 100.0, 10.0)

opties_aantal = st.number_input("Aantal extra opties (0–3)", 0, 3, 0)

# Extra opties
extra_opties = []
if opties_aantal:
    for i in range(1, opties_aantal + 1):
        a = st.number_input(f"Aantal voor optie {i}", 1, key=f"opt_aantal_{i}")
        t = st.selectbox(f"Type voor optie {i}", ["Bedrukt", "3D-logo"], key=f"opt_type_{i}")
        kc = st.selectbox(f"Kleuren voor optie {i}", [1, 2, 3], disabled=(t != "Bedrukt"), key=f"opt_kc_{i}")
        kband = st.selectbox(f"Bandje-kleur voor optie {i}", ["Standaard", "Special", "Zwart", "Off White", "Blauw", "Rood"], key=f"opt_band_{i}")
        kort = st.number_input(f"Korting voor optie {i} (%)", 0.0, 100.0, 0.0, key=f"opt_kort_{i}")
        extra_opties.append(dict(aantal=a, type=t, kleuren=kc, band=kband, korting=kort))

# Prijsberekeningen
def kostprijs(typ: str, aant: int, kl: int) -> float:
    prijs = {
        "3D": {1000: 2.79, 2000: 1.63, 5000: 1.09, 7500: 0.97, 10000: 0.91, 50000: 0.75},
        "Bedrukt1": {1000: 2.07, 2000: 1.94, 5000: 1.38, 7500: 1.36, 10000: 1.27, 50000: 1.20},
    }
    key = "3D" if typ == "3D-logo" else f"Bedrukt{kl}"
    staffels = sorted(prijs["3D"])
    return prijs[key][min(staffels, key=lambda x: abs(x - aant))]

def verkoopprijs(kost: float, verh: float, kort: float) -> float:
    return kost * (1 + verh / 100) * (1 - kort / 100)

# Vul HTML-template in
template_path = Path(__file__).with_name("template.html")
template = Template(template_path.read_text(encoding="utf-8"))

# Berekeningen voor de hoofdlijn
rows = []
total_excl = Decimal(0)

def append_row(aantal, t, kband, stprijs, oms):
    global total_excl
    rows.append(f"""
<tr><td>{aantal}</td><td>{t}</td><td>{kband}</td>
<td>{oms}</td><td style="text-align:right;">{eur(stprijs)}</td>
<td style="text-align:right;">{eur(stprijs * aantal)}</td></tr>""")
    total_excl += Decimal(stprijs * aantal)

# Hoofdoptie toevoegen
kp = kostprijs(product_type, aantal, kleuren_aantal)
vp = verkoopprijs(kp, verhoging_pct, korting_pct)
omschrijving = "1-kleur tampondruk" if product_type == "Bedrukt" else "3D-logo inbegrepen"
append_row(aantal, product_type, kleur_bandje, vp, omschrijving)

# HTML genereren
html_out = template.safe_substitute(
    KLANT=klant or "–",
    ADRES=adres or "–",
    OFFNR=offnr or "–",
    DATUM=datetime.now().strftime("%d-%m-%Y"),
    GELDIG=(datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"),
    PRODUCTROWS="".join(rows),
    TOTALEXCL=eur(total_excl),
    BTW=eur(total_excl * Decimal("0.21")),
    TOTAALINC=eur(total_excl + total_excl * Decimal("0.21")),
    **img_dict,
)

# HTML-weergave en download
st.download_button("Download HTML", html_out, file_name="offerte.html", mime="text/html")
st.components.v1.html(html_out, height=800, scrolling=True)

pdf_data = html_to_pdf_bytes(html_out)
if pdf_data:
    st.download_button("Download PDF", pdf_data, file_name="offerte.pdf", mime="application/pdf")
else:
    st.info("PDF-backend niet beschikbaar.")
