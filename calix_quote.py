# calix_quote.py  –  DEEL 1
import streamlit as st, base64, tempfile, os
from datetime import date, timedelta

# ---------- helpers ----------
SPECIAL_COLOR_SURCHARGE = 480.0
SHIPPING_SURCHARGE      = 150.0
BTW_PCT                 = 0.21

def save_html(html: str, path: str):
    with open(path, "w", encoding="utf-8") as f: f.write(html)

def download_link(path: str, fname: str):
    with open(path, "r", encoding="utf-8") as f:
        b64 = base64.b64encode(f.read().encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{fname}">📥 Download offerte (HTML)</a>'

# ---------- Streamlit lay-out ----------
st.set_page_config(page_title="Calix Offerte Tool", layout="wide")
st.title("🧾 Calix Offerte Generator")
st.caption("De output is visueel identiek aan de VBA-offerte.")

# ---------- Hoofd-gegevens ----------
st.header("📋 Hoofdgegevens")
c1, c2 = st.columns(2)
with c1:
    klantnaam   = st.text_input("Naam klant")
    adres       = st.text_input("Adres")
    off_nr      = st.text_input("Offertenummer")
with c2:
    aantal_1    = st.number_input("Aantal (optie 1)",  1, step=1, value=1000)
    type_1      = st.selectbox("Type (optie 1)", ["Bedrukt", "3D-logo"])
    kleur_1     = st.text_input("Kleur bandje (optie 1)", "Zwart")
    kleuren_1   = st.selectbox("Aantal kleuren (indien bedrukt)", [1,2,3],
                               disabled=(type_1!="Bedrukt"))

extra_pct      = st.number_input("Verhoging (Extra %)", 0.0, 1.0, 0.10, 0.01)
korting_pct    = st.number_input("Korting (%)",          0.0, 1.0, 0.00, 0.01)
optie_count    = st.selectbox("Aantal opties (1–4)", [1,2,3,4], index=0)
# calix_quote.py  –  DEEL 2
st.header("🔄 Extra opties")
extra_opties = []
for i in range(2, optie_count+1):
    st.subheader(f"Optie {i}")
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        aant = st.number_input(f"Aantal", 1, step=1, value=500, key=f"a{i}")
    with c2:
        t    = st.selectbox("Type", ["Bedrukt","3D-logo"], key=f"t{i}")
    with c3:
        clr  = st.text_input("Kleur", "Standaard", key=f"k{i}")
    with c4:
        kls  = st.selectbox("Kleuren", [1,2,3], key=f"c{i}", disabled=(t!="Bedrukt"))
    with c5:
        disc = st.number_input("Korting (%)", 0.0, 1.0, 0.0, 0.01, key=f"d{i}")
    extra_opties.append(dict(aantal=aant, type=t, kleur=clr, kleuren=kls, korting=disc))
# calix_quote.py  –  DEEL 3
# ---------- prijsregel ----------
def regel(aantal, type_, kleur, kleuren, opslag, korting):
    base = 2.0 if type_.lower()=="3d-logo" else 2.2 + 0.2*(kleuren-1)
    verkoop = base*(1+opslag)*(1-korting)
    subt    = aantal*verkoop
    detail  = (f"{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole"
               if type_.lower()=="bedrukt"
               else "3D-logo inbegrepen, Inclusief Ontwerpcontrole")
    return detail, verkoop, subt

# ---------- eerste optie ----------
items=[]
d,p,s = regel(aantal_1, type_1, kleur_1, int(kleuren_1 or 0), extra_pct, korting_pct)
items.append(dict(aantal=aantal_1,type=type_1,kleur=kleur_1,detail=d,prijs=p,sub=s))

# ---------- extra opties ----------
for o in extra_opties:
    d,p,s = regel(o["aantal"], o["type"], o["kleur"], o["kleuren"],
                  extra_pct, o["korting"])
    items.append(dict(aantal=o["aantal"],type=o["type"],kleur=o["kleur"],
                      detail=d, prijs=p, sub=s))

# ---------- toeslagen ----------
special_toeslag = any(i["kleur"].lower()=="special" for i in items)*SPECIAL_COLOR_SURCHARGE
verzend_toeslag = SHIPPING_SURCHARGE if any(i["aantal"]>9999 for i in items) else 0
totaal_ex = sum(i["sub"] for i in items)+special_toeslag+verzend_toeslag
btw  = totaal_ex*BTW_PCT
totaal_in = totaal_ex+btw
today = date.today().strftime("%d-%m-%Y")
valid = (date.today()+timedelta(days=14)).strftime("%d-%m-%Y")

# ---------- tabel-rijen ----------
rows=""
for i in items:
    rows+=f"<tr><td>{i['aantal']}</td><td>{i['type']}</td><td>{i['kleur']}</td>"\
           f"<td>{i['detail']}</td><td style='text-align:right'>&euro; {i['prijs']:.2f}</td>"\
           f"<td style='text-align:right'>&euro; {i['sub']:.2f}</td></tr>"
if special_toeslag:
    rows+=f"<tr><td>1</td><td>Extra</td><td>Special</td><td>Afwijkende kleur bandje</td>"\
          f"<td style='text-align:right'>&euro; {SPECIAL_COLOR_SURCHARGE:.2f}</td>"\
          f"<td style='text-align:right'>&euro; {SPECIAL_COLOR_SURCHARGE:.2f}</td></tr>"
if verzend_toeslag:
    rows+=f"<tr><td>1</td><td>Verzendkosten</td><td>–</td><td>Extra kosten voor zending</td>"\
          f"<td style='text-align:right'>&euro; {SHIPPING_SURCHARGE:.2f}</td>"\
          f"<td style='text-align:right'>&euro; {SHIPPING_SURCHARGE:.2f}</td></tr>"

# ---------- complete HTML (CSS uit VBA) ----------
css_common = """
@page{size:A4;margin:0;}
@font-face{font-family:'Sansation';src:url('https://fonts.gstatic.com/s/sansation/v17/4UaHrEJDsxBrF37olUeD96rp8Rx7esR2.woff2') format('woff2');}
@font-face{font-family:'Clash Display';src:url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&display=swap');}
body{margin:0;padding:0;font-family:'Clash Display',sans-serif;font-size:12px;line-height:1.4;color:#333;}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;}
.section{padding:0 60px 8px 60px;}
.header{background:#E4B713;color:#fff;padding:10px 30px 80px 30px;
clip-path:polygon(0 0,100% 0,100% 70%,0 100%);position:relative;}
.header-top{display:flex;align-items:center;justify-content:space-between;}
.header-brand{font-size:18px;font-weight:700;letter-spacing:.5px;
text-transform:uppercase;font-family:'Sansation',sans-serif;}
.header-text{font-size:18px;font-weight:600;letter-spacing:.5px;
text-transform:uppercase;font-family:'Sansation',sans-serif;}
.header-divider{height:3px;background:#fff;width:100%;margin:0 0 30px 0;border-radius:2px;}
.header h1{font-size:26px;margin:0;font-weight:600;}
.footer-fixed{position:absolute;left:0;bottom:0;width:100%;
background:#E4B713;color:#fff;font-size:12px;padding:50px 0 30px;
clip-path:polygon(0 14%,100% 0%,100% 100%,0% 100%);}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:12px;}
table.prod tr:nth-child(even){background:#fafafa;}th,td{padding:6px;border-bottom:1px solid #FFFFFF;}
th{background:#f8f8f8;font-weight:600;text-align:left;}
.totals-separator{height:4px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px;}
.totalbar{height:4px;background:#E4B713;width:44%;margin:4px 0 8px auto;border-radius:2px;}
"""
html = f"""<!DOCTYPE html><html lang='nl'><head><meta charset='utf-8'>
<title>Offerte Calix</title><style>{css_common}</style></head><body>

<!-- ===== Page 1 ===== -->
<div class='page'>
 <div class='header'>
   <div class='header-top'><span class='header-brand'>CALIX</span>
        <span class='header-text'>HANDS FREE DANCING</span></div>
   <div class='header-divider'></div>
   <h1>Cupholder voor: {klantnaam}</h1>
   <p>Offertenummer: {off_nr}   |   Datum: {today}   |   Geldig tot: {valid}<br>Adres: {adres}</p>
 </div>

 <div class='section'><h2>Welkom!</h2>
   Dank voor je interesse in onze duurzame bekerhouders. Met deze oplossing verlaag je de afvalstroom én geef je bezoekers een handige gadget als blijvende herinnering.
 </div>

 <div class='section'><h2>Productoverzicht</h2>
   <table class='prod'>
     <tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
         <th style='text-align:right;'>Prijs/stuk</th>
         <th style='text-align:right;'>Totaal excl.</th></tr>
     {rows}
   </table>

   <div class='totals-separator'></div>
   <p style='text-align:right'>
     Totaal excl. btw: € {totaal_ex:.2f}<br>
     BTW (21 %): € {btw:.2f}<br>
     <span style='font-size:14px;font-weight:600'>Totaal incl. btw: € {totaal_in:.2f}</span>
   </p>
 </div>

 <div class='footer-fixed' style='text-align:center'>
   Calix Promotie Producten V.O.F. – Bieze 23, 5382 KZ Vinkel – info@handsfreedancing.nl
 </div>
</div>

<!-- ===== Page 2 ===== -->
<div class='page'>
 <div class='header'><div class='header-top'>
      <span class='header-brand'>CALIX</span><span class='header-text'>HANDS FREE DANCING</span></div>
      <div class='header-divider'></div>
      <h1>Visualisatie & Extra opties</h1>
      <p>Offertenummer {off_nr} – Datum {today}</p>
 </div>

 <div class='section' style='display:flex;justify-content:center;gap:20px;background:#f4f4f4;border-radius:6px;padding:14px;'>
     <img src='https://via.placeholder.com/240?text=Mock-up+1' width='240'>
     <img src='https://via.placeholder.com/240?text=Mock-up+2' width='240'>
 </div>

 <div class='footer-fixed' style='text-align:center'>
   BTW NL86614472B01 · IBAN NL04 RABO 0383 2726 88 · <a style='color:#fff' href='https://handsfreedancing.nl/voorwaarden'>Leveringsvoorwaarden</a>
 </div>
</div>

</body></html>"""
# calix_quote.py  –  DEEL 4
if st.button("🚀 Generate offerte"):
    tmp = tempfile.gettempdir()
    fname = f"offerte_{klantnaam.lower().replace(' ','_')}_{off_nr}.html"
    fpath = os.path.join(tmp, fname)
    save_html(html, fpath)
    st.success("Offerte gegenereerd ✔")
    st.markdown(download_link(fpath, fname), unsafe_allow_html=True)
    with st.expander("📄 Voorbeeld (scrollbaar)"):
        st.components.v1.html(html, height=720, scrolling=True)
