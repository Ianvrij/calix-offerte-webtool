# 📄 app.py - DEEL 1

import streamlit as st
from datetime import date, timedelta
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
import base64

# Pad naar de templates (HTML)
TEMPLATE_DIR = "templates"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def html_to_file(html_string, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_string)



# Functie om PDF downloadbaar te maken in Streamlit
def get_pdf_download_link(pdf_path, filename="offerte_calix.pdf"):
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    href = f'<a href="data:application/pdf;base64,{base64_pdf}" download="{filename}">📥 Download offerte als PDF</a>'
    return href
# 📄 app.py - DEEL 2 (vanaf DEEL 1)

st.set_page_config(page_title="Calix Offerte Generator", layout="centered")
st.title("📄 Calix Offerte Generator")

st.markdown("Vul de onderstaande gegevens in om een offerte te genereren:")

# === Klant- en offertegegevens ===
with st.form("offerte_form"):
    klantnaam = st.text_input("Naam klant", "TEST")
    adres = st.text_input("Adres", "Oude Kijk in Het Jatstraat 5, 9712 EA Groningen")
    offertenummer = st.text_input("Offertenummer", "3241234")
    datumVandaag = date.today().strftime("%d-%m-%Y")
    geldigheid = (date.today() + timedelta(days=14)).strftime("%d-%m-%Y")

    aantal = st.number_input("Aantal stuks", min_value=1, value=10001)
    productType = st.selectbox("Type product", ["Bedrukt", "3D-logo"])
    kleur = st.selectbox("Kleur bandje", ["Zwart", "Rood", "Blauw", "Off-white", "Special"])
    
    if productType == "Bedrukt":
        aantal_kleuren = st.selectbox("Aantal kleuren (tampondruk)", [1, 2, 3])
    else:
        aantal_kleuren = 0

    prijs_per_stuk = st.number_input("Prijs per stuk (excl. btw)", min_value=0.0, value=2.85)
    aantal_opties = st.number_input("Aantal extra opties", min_value=1, max_value=4, value=1)

    verzendtoeslag = 150 if aantal > 10000 else 0
    specialekleur_toeslag = 480 if kleur.lower() == "special" else 0

    submit = st.form_submit_button("✅ Genereer offerte")
# 📄 app.py - DEEL 3 (na form submit)

if submit:
    totaal_excl = aantal * prijs_per_stuk
    optierijen = []

    for i in range(1, aantal_opties + 1):
        st.markdown(f"### ➕ Optie {i}")
        opt_aantal = st.number_input(f"Aantal optie {i}", min_value=1, value=aantal, key=f"aantal_optie_{i}")
        opt_type = st.selectbox(f"Type optie {i}", ["Bedrukt", "3D-logo"], key=f"type_optie_{i}")
        opt_kleur = st.selectbox(f"Kleur optie {i}", ["Standaard", "Special"], key=f"kleur_optie_{i}")
        opt_prijs = st.number_input(f"Prijs per stuk optie {i}", min_value=0.0, value=prijs_per_stuk, key=f"prijs_optie_{i}")

        if opt_type == "Bedrukt":
            opt_kleuren = st.selectbox(f"Aantal kleuren optie {i}", [1, 2, 3], key=f"kleuren_optie_{i}")
            details = f"{opt_kleuren}-kleuren Tampondruk, Inclusief Ontwerpcontrole"
        else:
            details = "3D-logo inbegrepen, Inclusief Ontwerpcontrole"

        optierijen.append({
            "aantal": opt_aantal,
            "type": opt_type,
            "kleur": opt_kleur,
            "details": details,
            "prijs": opt_prijs,
            "totaal": opt_aantal * opt_prijs
        })
        totaal_excl += opt_aantal * opt_prijs

    if kleur.lower() == "special":
        totaal_excl += specialekleur_toeslag
        optierijen.append({
            "aantal": 1,
            "type": "Extra",
            "kleur": "Special",
            "details": "Voor afwijkende kleurkeuze (‘Special’ bandje)",
            "prijs": 480.0,
            "totaal": 480.0
        })

    if aantal > 10000:
        totaal_excl += verzendtoeslag
        optierijen.append({
            "aantal": 1,
            "type": "Verzendkosten",
            "kleur": "–",
            "details": "Extra kosten voor zending",
            "prijs": 150.0,
            "totaal": 150.0
        })

    btw = totaal_excl * 0.21
    totaal_inc = totaal_excl + btw

    # 🧠 Hier begint de HTML-structuur – in Deel 4 maken we deze af
    html_string = f"""
    <!DOCTYPE html>
    <html lang="nl">
    <head>
        <meta charset="utf-8">
        <title>Offerte Calix</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; font-size: 13px; }}
            h1, h2 {{ color: #E4B713; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f8f8f8; }}
            .footer {{ margin-top: 40px; font-size: 11px; color: #777; }}
        </style>
    </head>
    <body>
        <h1>Offerte voor {klantnaam}</h1>
        <p><b>Offertenummer:</b> {offertenummer} <br>
           <b>Datum:</b> {datumVandaag} | <b>Geldig tot:</b> {geldigheid} <br>
           <b>Adres:</b> {adres}</p>
        <h2>Productoverzicht</h2>
        <table>
            <tr>
                <th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th><th>Prijs/stuk</th><th>Totaal excl. btw</th>
            </tr>
    """

    for optie in optierijen:
        html_string += f"""
        <tr>
            <td>{optie['aantal']}</td>
            <td>{optie['type']}</td>
            <td>{optie['kleur']}</td>
            <td>{optie['details']}</td>
            <td>€ {optie['prijs']:.2f}</td>
            <td>€ {optie['totaal']:.2f}</td>
        </tr>
        """

    html_string += f"""
        </table>
        <h2>Samenvatting</h2>
        <p><b>Totaal excl. btw:</b> € {totaal_excl:.2f}<br>
           <b>BTW (21%):</b> € {btw:.2f}<br>
           <b>Totaal incl. btw:</b> <b>€ {totaal_inc:.2f}</b></p>
        <div class="footer">
            Calix Promotie Producten V.O.F. | info@handsfreedancing.nl | handsfreedancing.nl
        </div>
    </body>
    </html>
    """
# 📄 app.py - DEEL 4 (vervolg op Deel 3)
# 📄 DEEL 4 – HTML-bestand opslaan i.p.v. PDF
from pathlib import Path
import tempfile

temp_dir = tempfile.gettempdir()
klantnaam_schoon = klantnaam.lower().replace(" ", "_").replace(",", "").replace(".", "")
html_filename = f"offerte_{klantnaam_schoon}_{offertenummer}.html"
html_path = os.path.join(temp_dir, html_filename)

try:
    html_to_file(html_string, html_path)
    st.success("✅ Offerte succesvol gegenereerd als HTML-bestand.")
except Exception as e:
    st.error(f"❌ Fout bij genereren van offerte: {e}")

# 📄 app.py - DEEL 5 (vervolg op Deel 4)
def get_html_download_link(file_path, filename="offerte.html"):
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    b64 = base64.b64encode(html_content.encode("utf-8")).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Download offerte als HTML-bestand</a>'
    return href

    # Toon downloadlink
    st.markdown("---")
    st.markdown("### 📥 Download Offerte")
    st.markdown(get_pdf_download_link(pdf_path, bestandsnaam_pdf), unsafe_allow_html=True)

    # Optioneel: toon preview in iframe (werkt niet in alle browsers!)
    with st.expander("📄 Voorbeeld van offerte (HTML-render)", expanded=False):
        st.components.v1.html(html_string, height=600, scrolling=True)
