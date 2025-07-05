# calix_quote.py  –  DEEL 1
import streamlit as st, base64, tempfile, os, re
from datetime import date, timedelta

# ========== helpers ==========
BTW_PCT                 = 0.21
SPECIAL_COLOR_SURCHARGE = 480.0
SHIPPING_SURCHARGE      = 150.0

def save_html(text: str, path: str):
    with open(path, "w", encoding="utf-8") as f: f.write(text)

def dl_link(path: str, fname: str):
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    return f'<a download="{fname}" href="data:text/html;base64,{b64}">📥 Download offerte (HTML)</a>'

# ========== UI ==========
st.set_page_config(page_title="Calix Offerte Tool", layout="wide")
st.title("🧾 Calix Offerte-generator")

c1, c2 = st.columns(2)
with c1:
    klantnaam   = st.text_input("Naam klant")
    adres       = st.text_input("Adres")
    offnr       = st.text_input("Offertenummer")
    extra_pct   = st.number_input("Verhoging (Extra %)", 0.0, 1.0, 0.10, 0.01)
    korting_pct = st.number_input("Korting (%)",          0.0, 1.0, 0.00, 0.01)
with c2:
    aantal_1  = st.number_input("Aantal (optie 1)", 1, step=1, value=1000)
    type_1    = st.selectbox("Type (optie 1)", ["Bedrukt", "3D-logo"])
    kleuren_1 = st.selectbox("Aantal kleuren (bij bedrukt)", [1,2,3],
                              disabled=(type_1!="Bedrukt"))
    kleur_1   = st.text_input("Kleur bandje (optie 1)", "Zwart")
optie_cnt   = st.selectbox("Aantal opties (1-4)", [1,2,3,4], 0)
# calix_quote.py  –  DEEL 2
st.header("🔄 Extra opties")
extra = []
for i in range(2, optie_cnt+1):
    st.subheader(f"Optie {i}")
    cA,cB,cC,cD,cE = st.columns(5)
    with cA: a = st.number_input("Aantal", 1, step=1, value=500, key=f"a{i}")
    with cB: t = st.selectbox ("Type", ["Bedrukt","3D-logo"], key=f"t{i}")
    with cC: k = st.text_input("Kleur", "Standaard", key=f"k{i}")
    with cD: c = st.selectbox ("Kleuren", [1,2,3], key=f"c{i}", disabled=(t!="Bedrukt"))
    with cE: d = st.number_input("Korting %", 0.0, 1.0, 0.0, 0.01, key=f"d{i}")
    extra.append(dict(aantal=a, type=t, kleur=k, kleuren=c, korting=d))
# calix_quote.py  –  DEEL 3
# ---------- prijsregel ----------
def regel(aantal, type_, kleuren, opslag, korting):
    grond = 2.00 if type_.lower()=="3d-logo" else 2.20+0.20*(kleuren-1)
    stuks = grond*(1+opslag)*(1-korting)
    detail = (f"{kleuren}-kleur tampondruk, Inclusief Ontwerpcontrole"
              if type_.lower()=="bedrukt"
              else "3D-logo inbegrepen, Inclusief Ontwerpcontrole")
    return stuks, detail, stuks*aantal

items=[]
p,d,s = regel(aantal_1, type_1, int(kleuren_1 or 0), extra_pct, korting_pct)
items.append(dict(aantal=aantal_1, type=type_1, kleur=kleur_1,
                  detail=d, prijs=p, sub=s))

for o in extra:
    p,d,s = regel(o["aantal"], o["type"], o["kleuren"],
                  extra_pct, o["korting"])
    items.append(dict(aantal=o["aantal"], type=o["type"], kleur=o["kleur"],
                      detail=d, prijs=p, sub=s))

spec_toeslag = SPECIAL_COLOR_SURCHARGE if any(i["kleur"].lower()=="special" for i in items) else 0
ship_toeslag = SHIPPING_SURCHARGE  if any(i["aantal"]>9999 for i in items)  else 0
totaal_ex = sum(i["sub"] for i in items)+spec_toeslag+ship_toeslag
btw       = totaal_ex*BTW_PCT
totaal_in = totaal_ex+btw

# ---------- HTML-rijen ----------
rows=""
for i in items:
    rows+=f"<tr><td>{i['aantal']}</td><td>{i['type']}</td><td>{i['kleur']}</td>"\
          f"<td>{i['detail']}</td><td style='text-align:right'>&euro; {i['prijs']:.2f}</td>"\
          f"<td style='text-align:right'>&euro; {i['sub']:.2f}</td></tr>"
if spec_toeslag:
    rows+=f"<tr><td>1</td><td>Extra</td><td>Special</td>"\
          f"<td>Voor afwijkende kleurkeuze (‘Special’ bandje)</td>"\
          f"<td style='text-align:right'>&euro; {spec_toeslag:.2f}</td>"\
          f"<td style='text-align:right'>&euro; {spec_toeslag:.2f}</td></tr>"
if ship_toeslag:
    rows+=f"<tr><td>1</td><td>Verzendkosten</td><td>–</td><td>Extra kosten voor zending</td>"\
          f"<td style='text-align:right'>&euro; {ship_toeslag:.2f}</td>"\
          f"<td style='text-align:right'>&euro; {ship_toeslag:.2f}</td></tr>"

# ---------- CSS (identiek aan VBA) ----------
css = r"""
@page{size:A4;margin:0;}
@font-face{font-family:'Sansation';src:url('https://fonts.gstatic.com/s/sansation/v17/4UaHrEJDsxBrF37olUeD96rp8Rx7esR2.woff2') format('woff2');}
@font-face{font-family:'Clash Display';src:url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&display=swap');}
body{margin:0;padding:0;font-family:'Clash Display',sans-serif;font-size:12px;line-height:1.4;color:#333;}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;}
.section{padding:0 60px 8px 60px;}
.header{background:#E4B713;color:#fff;padding:10px 30px 80px 30px;
clip-path:polygon(0 0,100% 0,100% 70%,0 100%);position:relative;}
.header-top{display:flex;align-items:center;justify-content:space-between;}
.header-brand,.header-text{font-family:'Sansation',sans-serif;font-weight:700;font-size:18px;letter-spacing:.5px;text-transform:uppercase;}
.header-text{font-weight:600;}
.header-divider{height:3px;background:#fff;width:100%;margin:0 0 30px;border-radius:2px;}
.header h1{font-size:26px;margin:0;font-weight:600;}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px;}
table.prod tr:nth-child(even){background:#fafafa;}th,td{padding:6px;border-bottom:1px solid #FFFFFF;}th{background:#f8f8f8;text-align:left;font-weight:600;}
.totals-separator{height:4px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px;}
.totalbar{height:4px;background:#E4B713;width:44%;margin:4px 0 8px auto;border-radius:2px;}
.footer-fixed{position:absolute;left:0;bottom:0;width:100%;background:#E4B713;color:#fff;font-size:12px;
padding:50px 0 30px;clip-path:polygon(0 14%,100% 0%,100% 100%,0% 100%);}
.footer-cols{display:flex;justify-content:space-between;max-width:960px;margin:0 auto;padding:0 40px;gap:40px;}
.footer-col{flex:1;}
.footer-col td{padding:2px 0;color:#fff;font-size:12px;border:none;vertical-align:top;}
.footer-col td:first-child{font-weight:600;padding-right:6px;white-space:nowrap;}
.footer-note{text-align:center;font-size:11px;color:#fff;line-height:1.4;margin-top:10px;}
.footer-note a{color:#fff!important;text-decoration:none;border-bottom:1px solid #fff;}
"""
today = date.today().strftime("%d-%m-%Y")
valid = (date.today()+timedelta(days=14)).strftime("%d-%m-%Y")

html = f"""<!DOCTYPE html><html lang='nl'><head><meta charset='utf-8'>
<title>Offerte Calix</title><style>{css}</style></head><body>

<!-- ======= PAGINA 1 ======= -->
<div class='page'>
 <div class='header'>
   <div class='header-top'><span class='header-brand'>CALIX</span><span class='header-text'>HANDS FREE DANCING</span></div>
   <div class='header-divider'></div>
   <h1>Cupholder voor: {klantnaam}</h1>
   <p>Offertenummer: {offnr} <br>Datum: {today} | Geldig tot: {valid}<br>Adres: {adres}</p>
 </div>

 <div class='section'><h2>Welkom!</h2>
   <p>Dank voor je interesse in onze duurzame bekerhouders. Met deze oplossing verlaag je de afvalstroom én geef je bezoekers een handige gadget als blijvende herinnering.</p>
 </div>

 <div class='section'><h2>Productoverzicht</h2>
   <table class='prod'>
     <tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
         <th style='text-align:right;'>Prijs/stuk</th><th style='text-align:right;'>Totaal excl. btw</th></tr>
     {rows}
   </table>
   <div class='totals-separator'></div>
   <table class='totals' style='width:100%;'><tr>
       <td class='label' style='text-align:right;width:70%;'>Totaal excl. btw:</td>
       <td class='value' style='text-align:right'>&euro; {totaal_ex:.2f}</td></tr>
       <tr><td class='label' style='text-align:right;'>BTW (21&nbsp;%):</td>
       <td class='value' style='text-align:right'>&euro; {btw:.2f}</td></tr></table>
   <div class='totalbar'></div>
   <table style='width:100%;'><tr><td style='text-align:right;font-weight:bold'>
       Totaal incl. btw:&nbsp;&euro;&nbsp;{totaal_in:.2f}</td></tr></table>
 </div>

 <div class='footer-fixed'>
   <div class='footer-cols'>
     <div class='footer-col'><table>
         <tr><td>Adres</td><td>Bieze&nbsp;23</td></tr>
         <tr><td></td><td>5382&nbsp;KZ&nbsp;Vinkel</td></tr>
         <tr><td>Telefoon</td><td>+31&nbsp;(0)6&nbsp;29&nbsp;83&nbsp;0517</td></tr>
     </table></div>
     <div class='footer-col'><table>
         <tr><td>E-mail</td><td><a href='mailto:info@handsfreedancing.nl'>info@handsfreedancing.nl</a></td></tr>
         <tr><td>Website</td><td><a href='https://handsfreedancing.nl'>handsfreedancing.nl</a></td></tr>
     </table></div>
     <div class='footer-col'><table>
         <tr><td>BTW</td><td>NL86614472B01</td></tr>
         <tr><td>IBAN</td><td>NL04&nbsp;RABO&nbsp;0383&nbsp;2726&nbsp;88</td></tr>
     </table></div>
   </div>
   <div class='footer-note'>
     Calix is een handelsnaam van Calix Promotie Producten V.O.F.&nbsp;
     Op deze aanbieding zijn onze leveringsvoorwaarden van toepassing.&nbsp;
     <a href='https://handsfreedancing.nl/voorwaarden'>Bekijk voorwaarden</a>
   </div>
 </div>
</div>

<!-- ======= PAGINA 2 ======= -->
<div class='page'>
 <div class='header'>
   <div class='header-top'><span class='header-brand'>CALIX</span><span class='header-text'>HANDS FREE DANCING</span></div>
   <div class='header-divider'></div>
   <h1>Visualisatie &amp; Extra opties</h1>
   <p>Offertenummer: {offnr} &nbsp;|&nbsp; Datum: {today}</p>
 </div>

 <div class='section'>
   <h2>Visualisatie</h2>
   <div style='display:flex;justify-content:center;gap:20px;background:#f4f4f4;border-radius:6px;padding:14px;'>
     <img src='https://via.placeholder.com/240?text=Mock-up+1' alt='Mock-up 1' width='240'>
     <img src='https://via.placeholder.com/240?text=Mock-up+2' alt='Mock-up 2' width='240'>
   </div>
 </div>

 <div class='section'><div class='flex-row-3'>
   <div class='flex-yellow'><h3 style='margin-top:0;'>Extra opties</h3><ul>
       <li>Leensysteem</li><li>Co-Branding</li></ul></div>
   <div class='flex-gray'><h3 style='margin-top:0;'>Levertijd &amp; verzending</h3><ul>
       <li>Productietijd circa 6 weken na akkoord.</li>
       <li>Afleveradres dient goed te bereiken zijn.</li></ul></div>
   <div class='flex-yellow'><h3 style='margin-top:0;'>Voorwaarden</h3><ul>
       <li>100 % aanbetaling</li><li>Annuleren tot 72 u na akkoord</li>
       <li><a href='https://calix.nl/voorwaarden'>Algemene voorwaarden</a></li></ul></div>
 </div></div>

 <div class='section'><h2>Meer info</h2><div style='text-align:center;'>
   <img src='https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=https://handsfreedancing.nl' style='border-radius:8px;'>
 </div></div>

 <div class='footer-fixed'>
   <div class='footer-cols'>
     <div class='footer-col'><table>
         <tr><td>Adres</td><td>Bieze&nbsp;23</td></tr>
         <tr><td></td><td>5382&nbsp;KZ&nbsp;Vinkel</td></tr>
         <tr><td>Telefoon</td><td>+31&nbsp;(0)6&nbsp;29&nbsp;83&nbsp;0517</td></tr>
     </table></div>
     <div class='footer-col'><table>
         <tr><td>E-mail</td><td><a href='mailto:info@handsfreedancing.nl'>info@handsfreedancing.nl</a></td></tr>
         <tr><td>Website</td><td><a href='https://handsfreedancing.nl'>handsfreedancing.nl</a></td></tr>
     </table></div>
     <div class='footer-col'><table>
         <tr><td>BTW</td><td>NL86614472B01</td></tr>
         <tr><td>IBAN</td><td>NL04&nbsp;RABO&nbsp;0383&nbsp;2726&nbsp;88</td></tr>
     </table></div>
   </div>
   <div class='footer-note'>
     Calix is een handelsnaam van Calix Promotie Producten V.O.F.&nbsp;
     Op deze aanbieding zijn onze leveringsvoorwaarden van toepassing.&nbsp;
     <a href='https://handsfreedancing.nl/voorwaarden'>Bekijk voorwaarden</a>
   </div>
 </div>
</div>

</body></html>"""
# calix_quote.py  –  DEEL 4
if st.button("🚀 Generate offerte"):
    tmp  = tempfile.gettempdir()
    safe = re.sub(r'[^a-z0-9_]+','_', klantnaam.lower().strip()) or "klant"
    fname= f"offerte_{safe}_{offnr}.html"
    fpath= os.path.join(tmp, fname)
    save_html(html, fpath)
    st.success("Offerte gegenereerd ✅")
    st.markdown(dl_link(fpath, fname), unsafe_allow_html=True)
    with st.expander("📄 Voorbeeld"):
        st.components.v1.html(html, height=760, scrolling=True)
