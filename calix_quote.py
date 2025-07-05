# calix_quote.py  –  DEEL 1
import streamlit as st
import pandas as pd
import base64, tempfile, os
from datetime import date, timedelta, datetime

st.set_page_config(page_title="Calix Offerte Tool", layout="wide")
st.title("🧾 Calix Offerte Generator")

# ---------- helpers ----------
SPECIAL_KLEUR_TOESLAG = 480.0
VERZEND_TOESLAG       = 150.0          # bij > 9 999 stuks
BTW_PCT               = 0.21

def save_html(html: str, path: str):
    with open(path, "w", encoding="utf-8") as f: f.write(html)

def dl_link(path: str, fname: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        b64 = base64.b64encode(f.read().encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{fname}">📥 Download offerte</a>'

# ---------- Hoofdgegevens ----------
st.header("📋 Hoofd­berekening")
col1, col2 = st.columns(2)
with col1:
    klantnaam  = st.text_input("Naam klant")
    adres      = st.text_input("Adres")
    off_nr     = st.text_input("Offertenummer")
with col2:
    aantal_h   = st.number_input("Aantal (optie 1)",  min_value=1, value=1000)
    type_h     = st.selectbox("Type", ["Bedrukt", "3D-logo"])
    kleur_h    = st.text_input("Kleur bandje", "Zwart")
    kleuren_h  = st.selectbox("Aantal kleuren (bij Bedrukt)", [1,2,3], disabled=(type_h!="Bedrukt"))

opties_aantal = st.selectbox("Aantal opties (1–4)", [1,2,3,4], index=0)
extra_pct     = st.number_input("Verhoging (Extra %)", 0.0, 1.0, 0.10, 0.01)
korting_pct   = st.number_input("Korting (%)",         0.0, 1.0, 0.00, 0.01)
# calix_quote.py  –  DEEL 2
st.header("🔄 Extra opties")
opties = []
for i in range(2, opties_aantal+1):
    st.subheader(f"Optie {i}")
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        aant = st.number_input(f"Aantal optie {i}", min_value=1, value=500, key=f"a_{i}")
    with c2:
        t    = st.selectbox(f"Type optie {i}", ["Bedrukt","3D-logo"], key=f"t_{i}")
    with c3:
        clr  = st.text_input(f"Kleur optie {i}", "Standaard", key=f"k_{i}")
    with c4:
        kls  = st.selectbox(f"Kleuren optie {i}", [1,2,3], key=f"c_{i}", disabled=(t!="Bedrukt"))
    with c5:
        krn  = st.number_input(f"Korting optie {i} (%)", 0.0,1.0,0.0,0.01, key=f"disc_{i}")
    opties.append(dict(aantal=aant, type=t, kleur=clr, kleuren=kls, korting=krn))
# calix_quote.py  –  DEEL 3
# 1) helpers voor regels
def prijsregel(aantal, type_, kleur, kleuren, verhoging, korting):
    """geeft tuple (beschrijving, prijs_stuk, subtotal_excl)"""
    # ↓ sterk vereenvoudigde kostprijs → verkoopprijs formule
    base = 2.0 if type_=="3D-logo" else 2.2 + 0.2*(kleuren-1)
    verkoop = base * (1+verhoging) * (1-korting)
    toeslag  = SPECIAL_KLEUR_TOESLAG if kleur.lower()=="special" else 0
    subtotal = aantal * verkoop + toeslag
    detail   = (f"{kleuren}-kleur tampondruk" if type_.lower()=="bedrukt"
                else "3D-logo inbegrepen") + ", Inclusief ontwerpcontrole"
    return detail, verkoop, subtotal, toeslag

# 2) eerste (hoofd) optie
producten = []
detail, prijs_stuk, subtotal, toeslag  = prijsregel(
        aantal_h, type_h, kleur_h, int(kleuren_h or 0),
        extra_pct, korting_pct)
producten.append(dict(aantal=aantal_h, type=type_h, kleur=kleur_h,
                      detail=detail, prijs=prijs_stuk, subt=subtotal,
                      toeslag=toeslag))

# 3) extra opties
for o in opties:
    d,p,s,t = prijsregel(o["aantal"], o["type"], o["kleur"], o["kleuren"],
                         extra_pct, o["korting"])
    producten.append(dict(aantal=o["aantal"], type=o["type"], kleur=o["kleur"],
                          detail=d, prijs=p, subt=s, toeslag=t))

# 4) verzend­toeslag
verzend = VERZEND_TOESLAG if any(p["aantal"]>9999 for p in producten) else 0

totaal_ex  = sum(p["subt"] for p in producten) + verzend
btw        = totaal_ex * BTW_PCT
totaal_in  = totaal_ex + btw
geldigheid = (date.today()+timedelta(days=14)).strftime("%d-%m-%Y")
vandaag    = date.today().strftime("%d-%m-%Y")

# ---------- HTML ----------
rows_html = ""
for p in producten:
    rows_html += f"""
       <tr><td>{p['aantal']}</td><td>{p['type']}</td><td>{p['kleur']}</td>
           <td>{p['detail']}</td><td style='text-align:right'>€ {p['prijs']:.2f}</td>
           <td style='text-align:right'>€ {p['subt']:.2f}</td></tr>"""

if verzend:
    rows_html += f"""
       <tr><td>1</td><td>Verzendkosten</td><td>–</td>
           <td>Extra kosten voor zending</td>
           <td style='text-align:right'>€ {verzend:.2f}</td>
           <td style='text-align:right'>€ {verzend:.2f}</td></tr>"""

html_body = f"""
<!DOCTYPE html><html lang='nl'><head><meta charset='utf-8'>
<title>Offerte Calix</title>
<style>
@page{{size:A4;margin:0;}}
body{{margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;}}
.page{{width:210mm;height:297mm;position:relative;overflow:hidden;}}
.header{{background:#E4B713;color:#fff;padding:20px 40px;clip-path:polygon(0 0,100% 0,100% 75%,0 100%);}}
.section{{padding:20px 60px;}}
.footer-fixed{{position:absolute;bottom:0;width:100%;background:#E4B713;color:#fff;padding:25px 0;font-size:10px;text-align:center;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{border-bottom:1px solid #ddd;padding:6px;}}
th{{background:#f2f2f2;text-align:left;}}
</style></head><body>

<div class='page'>
 <div class='header'>
   <h1>CALIX | Hands Free Dancing</h1>
   <h2 style='margin:0'>Cupholder voor: {klantnaam}</h2>
   Offertenummer {off_nr} | Datum {vandaag} | Geldig tot {geldigheid}<br>
   Adres: {adres}
 </div>

 <div class='section'><h2>Welkom!</h2>
   Dank voor je interesse in onze duurzame bekerhouders.<br>
   Met deze oplossing verlaag je de afvalstroom én geef je bezoekers een blijvende herinnering.
 </div>

 <div class='section'><h2>Productoverzicht</h2>
   <table><tr>
        <th>Aantal</th><th>Type</th><th>Kleur</th>
        <th>Details</th><th style='text-align:right'>Prijs/stuk</th>
        <th style='text-align:right'>Totaal excl.</th></tr>
        {rows_html}
   </table>
   <p style='text-align:right;margin-top:15px'>
      Verzendkosten: € {verzend:.2f}<br>
      <b>Totaal excl. btw: € {totaal_ex:.2f}</b><br>
      BTW 21 %: € {btw:.2f}<br>
      <span style='font-size:14px'><b>Totaal incl. btw: € {totaal_in:.2f}</b></span>
   </p>
 </div>

 <div class='footer-fixed'>
   Calix Promotie Producten V.O.F. – Bieze 23, 5382 KZ Vinkel – info@handsfreedancing.nl
 </div>
</div>

<!-- Pagina 2 -->
<div class='page'>
 <div class='header'><h1>Visualisatie & Extra opties</h1></div>
 <div class='section' style='text-align:center'>
   <img src='https://via.placeholder.com/240x240?text=Mock-up+1' width='240'>
   <img src='https://via.placeholder.com/240x240?text=Mock-up+2' width='240'>
 </div>
 <div class='footer-fixed'>
   Calix Promotie Producten – KvK 86614472 | IBAN NL04 RABO 0383 2726 88
 </div>
</div>

</body></html>
"""
# calix_quote.py  –  DEEL 4
# 1) opslaan
tmpdir   = tempfile.gettempdir()
fname    = f"offerte_{klantnaam.lower().replace(' ','_')}_{off_nr}.html"
fpath    = os.path.join(tmpdir, fname)
save_html(html_body, fpath)

# 2) UI
st.success("Offerte berekend ✔")
st.markdown(dl_link(fpath, fname), unsafe_allow_html=True)

with st.expander("📄 HTML-voorbeeld"):
    st.components.v1.html(html_body, height=700, scrolling=True)
