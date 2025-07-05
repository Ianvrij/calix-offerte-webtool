# calix_offerte_app.py – DEEL 1
import streamlit as st
import base64
import tempfile
import os
from datetime import datetime

# HTML-bestand opslaan
def html_to_file(html_string, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_string)

# Downloadlink genereren
def get_html_download_link(file_path, filename="offerte.html"):
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Download offerte als HTML-bestand</a>'
    return href

st.set_page_config(page_title="Calix Offerte Tool", layout="wide")
st.title("🧾 Calix Offerte Generator")

# Offerte-informatie
st.header("📋 Algemene gegevens")
col1, col2 = st.columns(2)
with col1:
    klantnaam = st.text_input("Naam klant", "TU/e Go Green Office")
    offertenummer = st.text_input("Offertenummer", "CALX-2025-001")
with col2:
    datum = st.date_input("Datum offerte", value=datetime.today())
    aantal_opties = st.selectbox("Aantal productopties", [1, 2, 3, 4], index=1)
    verzendkosten = st.number_input("Verzendkosten (€)", value=15.0)

toelichting = st.text_area("Toelichting offerte", "Bedankt voor jullie interesse in onze herbruikbare producten...")
# calix_offerte_app.py – DEEL 2

st.header("🎨 Productopties")
productopties = []

for i in range(1, aantal_opties + 1):
    st.subheader(f"🔹 Optie {i}")
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    with col1:
        product = st.text_input(f"Producttype optie {i}", key=f"product_{i}", value=f"Herbruikbare bekerhouder")
    with col2:
        kleur = st.text_input(f"Kleur optie {i}", key=f"kleur_{i}", value="Zwart")
    with col3:
        aantal = st.number_input(f"Aantal optie {i}", key=f"aantal_{i}", min_value=1, step=1, value=100)
    with col4:
        prijs_per_stuk = st.number_input(f"Prijs/stuk optie {i} (€)", key=f"prijs_{i}", value=2.95)

    # Kleurtoeslag indien niet zwart
    kleurtoeslag = 0.20 if kleur.lower() != "zwart" else 0.00
    totaalprijs = aantal * (prijs_per_stuk + kleurtoeslag)

    productopties.append({
        "product": product,
        "kleur": kleur,
        "aantal": aantal,
        "prijs_per_stuk": prijs_per_stuk,
        "kleurtoeslag": kleurtoeslag,
        "subtotaal": totaalprijs
    })

# Totaalprijs berekenen
totaal_ex_btw = sum(p["subtotaal"] for p in productopties) + verzendkosten
btw = 0.21 * totaal_ex_btw
totaal_incl_btw = totaal_ex_btw + btw
# calix_offerte_app.py – DEEL 3

# HTML-offerte samenstellen
html_string = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; padding: 40px; }}
        h1 {{ color: #2B2B2B; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .footer {{ font-size: 10px; text-align: center; margin-top: 50px; color: gray; }}
    </style>
</head>
<body>
    <h1>Offerte</h1>
    <p><strong>Klant:</strong> {klantnaam}<br>
    <strong>Offertenummer:</strong> {offertenummer}<br>
    <strong>Datum:</strong> {datum.strftime('%d-%m-%Y')}</p>

    <h2>Toelichting</h2>
    <p>{toelichting}</p>

    <h2>Productopties</h2>
    <table>
        <tr>
            <th>Optie</th>
            <th>Product</th>
            <th>Kleur</th>
            <th>Aantal</th>
            <th>Prijs/stuk (€)</th>
            <th>Kleurtoeslag (€)</th>
            <th>Subtotaal (€)</th>
        </tr>
"""

for i, optie in enumerate(productopties, start=1):
    html_string += f"""
    <tr>
        <td>Optie {i}</td>
        <td>{optie['product']}</td>
        <td>{optie['kleur']}</td>
        <td>{optie['aantal']}</td>
        <td>{optie['prijs_per_stuk']:.2f}</td>
        <td>{optie['kleurtoeslag']:.2f}</td>
        <td>{optie['subtotaal']:.2f}</td>
    </tr>
    """

html_string += f"""
    </table>

    <h2>Prijsopbouw</h2>
    <p>Verzendkosten: € {verzendkosten:.2f}<br>
    Totaal excl. BTW: € {totaal_ex_btw:.2f}<br>
    BTW (21%): € {btw:.2f}<br>
    <strong>Totaal incl. BTW: € {totaal_incl_btw:.2f}</strong></p>

    <div class="footer">
        Calix Promotie Producten – Samen naar een circulaire festivalbeleving
    </div>
</body>
</html>
"""
# calix_offerte_app.py – DEEL 4

st.header("📄 Offerte genereren")

# Tijdelijke HTML-bestand opslaan
temp_dir = tempfile.gettempdir()
klantnaam_schoon = klantnaam.lower().replace(" ", "_").replace(",", "").replace(".", "")
html_filename = f"offerte_{klantnaam_schoon}_{offertenummer}.html"
html_path = os.path.join(temp_dir, html_filename)

try:
    html_to_file(html_string, html_path)
    st.success("✅ Offerte succesvol gegenereerd!")
except Exception as e:
    st.error(f"❌ Fout bij genereren: {e}")

# Downloadlink + Preview
st.markdown("---")
st.markdown("### 📥 Download Offerte")
st.markdown(get_html_download_link(html_path, html_filename), unsafe_allow_html=True)

with st.expander("📄 Bekijk voorbeeld", expanded=False):
    st.components.v1.html(html_string, height=600, scrolling=True)
