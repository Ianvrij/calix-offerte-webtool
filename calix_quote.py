import base64
import io
from pathlib import Path
import streamlit as st
from weasyprint import HTML


# Hulpfunctie voor base64 afbeeldingen (voor inline afbeeldingen)
def b64_img(filename: str) -> str:
    """Geef data-URI voor lokaal plaatje; werkt overal (ook Streamlit Cloud)."""
    p = Path(__file__).with_name(filename)
    mime = "image/png" if filename.lower().endswith("png") else "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"

# Functie om HTML naar PDF om te zetten
@st.cache_resource
def html_to_pdf_bytes(html: str) -> bytes | None:
    try:
        from weasyprint import HTML, __version__ as WV
        st.write(f"PDF-engine: WeasyPrint {WV}")  # zichtbaar in de app
        return HTML(string=html, base_url=".").write_pdf()
    except Exception as e:
        st.exception(e)  # toont fout in UI, geen app-crash
        return None

# Functie om EUR weer te geven in de juiste opmaak
def eur(val: float) -> str:
    """€-notatie met , als decimaalteken en . als duizend-scheiding."""
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Streamlit UI voor offerte-invoer
st.set_page_config(page_title="Calix Offertegenerator", layout="centered")
st.title("Calix – Offertegenerator")

# Hoofdopties van de klant
klant = st.text_input("Naam klant")
adres = st.text_input("Adres")
offnr = st.text_input("Offertenummer")
aantal = st.number_input("Aantal", min_value=1, value=1000)
product_type = st.selectbox("Type", ["Bedrukt", "3D-logo"])

# Kleurinstellingen
kleur_bandje = st.selectbox("Kleur bandje", ["Zwart", "Off White", "Blauw", "Rood"])

# Extra opties
extra_opties = []
opties_aantal = st.number_input("Aantal extra opties (0–3)", 0, 3, 0)
for i in range(opties_aantal):
    st.subheader(f"Optie {i + 1}")
    opt_aantal = st.number_input(f"Aantal (Optie {i + 1})", 1)
    extra_opties.append(opt_aantal)

# Prijsinstellingen
prijs = 2.5  # voorbeeldprijs

# HTML-template met placeholders voor klant en producten
html_template = """
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8" />
    <title>Offerte Calix</title>
    <style>
        @page{ size: A4; margin: 0; }
        body { font-family: Arial, sans-serif; font-size: 12px; margin: 0; padding: 0; }
        .header { background-color: #E4B713; color: white; padding: 10mm; text-align: center; }
        .footer { background-color: #E4B713; color: white; padding: 10mm; text-align: center; position: fixed; bottom: 0; width: 100%; }
        .section { margin: 15mm; }
        table { width: 100%; border-collapse: collapse; margin-top: 10mm; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .totals { margin-top: 10mm; }
        .footer-note { font-size: 11px; margin-top: 10px; }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>Offerte voor ${KLANT}</h1>
        <p>Offertenummer: ${OFFNR} | Datum: ${DATUM} | Geldig tot: ${GELDIG}</p>
    </div>

    <!-- Productenlijst -->
    <div class="section">
        <h2>Productenoverzicht</h2>
        <table>
            <tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Prijs per stuk</th><th>Totaal</th></tr>
            ${PRODUCTROWS}
        </table>
    </div>

    <!-- Totals -->
    <div class="totals">
        <table>
            <tr><td>Totaal excl. btw:</td><td>${TOTALEXCL}</td></tr>
            <tr><td>BTW (21 %):</td><td>${BTW}</td></tr>
            <tr><td><strong>Totaal incl. btw:</strong></td><td><strong>${TOTAALINC}</strong></td></tr>
        </table>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>Calix - Bieze 23, 5382 KZ Vinkel | Tel: +31 (0)6 29 83 0517 | Email: info@handsfreedancing.nl</p>
        <p class="footer-note">Leveringsvoorwaarden zijn van toepassing. <a href="https://handsfreedancing.nl/voorwaarden">Bekijk voorwaarden</a></p>
    </div>
</body>
</html>
"""

# Placeholder voor de producttabellen
product_rows = ""
product_rows += f"<tr><td>{aantal}</td><td>{product_type}</td><td>{kleur_bandje}</td><td>{eur(prijs)}</td><td>{eur(prijs * aantal)}</td></tr>"

# Vul de template in met de waarden
html_content = html_template.replace("${KLANT}", klant).replace("${OFFNR}", offnr).replace("${DATUM}", datetime.now().strftime("%d-%m-%Y"))
html_content = html_content.replace("${GELDIG}", (datetime.now() + timedelta(days=14)).strftime("%d-%m-%Y"))
html_content = html_content.replace("${PRODUCTROWS}", product_rows)
html_content = html_content.replace("${TOTALEXCL}", eur(prijs * aantal))
html_content = html_content.replace("${BTW}", eur(prijs * aantal * 0.21))
html_content = html_content.replace("${TOTAALINC}", eur(prijs * aantal * 1.21))

# PDF generatie
pdf_data = html_to_pdf_bytes(html_content)
if pdf_data:
    st.download_button("Download PDF", pdf_data, file_name=f"offerte_{klant}.pdf", mime="application/pdf")

# HTML preview in Streamlit
st.components.v1.html(html_content, height=800, scrolling=True)
