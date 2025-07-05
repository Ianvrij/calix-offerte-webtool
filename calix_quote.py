#!/usr/bin/env python3
"""
calix_quote.py  –  Calix-­offertegenerator (HTML + PDF)

CLI-gebruik
-----------
    python calix_quote.py offer_input.json -o ./out

Streamlit-GUI
-------------
    streamlit run calix_quote.py
"""
from __future__ import annotations
import json, re, unicodedata, datetime as _dt, pathlib, argparse, sys
from dataclasses import dataclass
from typing import List, Dict, Any

# ───────────────────────── 1 · DATA KLASSEN ─────────────────────────
@dataclass
class OfferInput:
    quantity: int
    product_type: str          # "Bedrukt" / "3D-logo"
    colours: int               # 1–3 (irrelevant bij 3D-logo)
    band_color: str            # "Standaard" / "Special"
    extra_increase_pct: float  # b.v. 0.10
    discount_pct: float        # b.v. 0.05

    def special_band(self) -> bool: return self.band_color.lower() == "special"
    def is_print(self) -> bool:    return self.product_type.lower() == "bedrukt"

@dataclass
class ClientInfo:
    name: str; address: str; offer_number: str

@dataclass
class OfferRow:
    inp: OfferInput; unit_cost: float; unit_price: float
    @property
    def total(self) -> float: return self.unit_price * self.inp.quantity
    def to_html(self) -> Dict[str,str]:
        d = self.inp
        detail = (f"{d.colours}-kleur{'en' if d.colours>1 else ''} tampondruk – ontwerpcontrole"
                  if d.is_print() else "3D-logo inbegrepen – ontwerpcontrole")
        fmt = lambda x:f"€ {x:,.2f}"
        return dict(qty=d.quantity,type=d.product_type,colour=d.band_color,
                    detail=detail,price=fmt(self.unit_price),total=fmt(self.total))

# ─────────────────────── 2 · BASIS­TABEL­WAARDEN (TODO) ─────────────────────
OFF_GEBREMA = {     # spuitgiet €/st.
    "<3000":0.30, "<10000":0.28, "<100000":0.26, "otherwise":0.24
}
EXTRA_KOSTEN = {    # vaste kosten
    "special_band":480, "transport":150
}
ARTISAN_BASE = [    # kale bedrukprijs (per kleur‐kolom 1-2-3)
    (200,(0.65,0.72,0.79)), (500,(0.55,0.62,0.69)), (1000,(0.50,0.57,0.64)),
    (5000,(0.45,0.52,0.59)),(10000,(0.40,0.47,0.54)),(20000,(0.35,0.42,0.49)),
    (999999,(0.30,0.37,0.44)),
]

# ───────────────────────── 3 · PRICING LOGIC ─────────────────────────
def spuitgiet(q:int,t:str,special:bool)->float:
    if t.lower()=="3d-logo":
        key="<3000" if q<3000 else "<10000" if q<10000 else "<100000" if q<100000 else "otherwise"
        base=OFF_GEBREMA[key]
    else:
        base=1.10 if q<3000 else OFF_GEBREMA["<10000" if q<10000 else "<100000" if q<100000 else "otherwise"]
    if special: base+=EXTRA_KOSTEN["special_band"]/q
    return base

def artisan(q:int,col:int)->float:
    for up,vals in ARTISAN_BASE:
        if q<=up: return vals[col-1]
    raise ValueError("colours-range buiten tabel")

def unit_cost(inp:OfferInput)->float:
    cost=spuitgiet(inp.quantity,inp.product_type,inp.special_band())
    if inp.is_print(): cost+=artisan(inp.quantity,inp.colours)
    if inp.quantity<10000: cost+=EXTRA_KOSTEN["transport"]/inp.quantity
    return round(cost,4)

def unit_price(cost:float,inp:OfferInput)->float:
    return round(cost*(1+inp.extra_increase_pct)*(1-inp.discount_pct),4)

# ───────────────────────── 4 · HTML TEMPLATE ─────────────────────────
from jinja2 import Environment, BaseLoader, select_autoescape
TEMPLATE=r"""<!DOCTYPE html><html lang=nl><head><meta charset=utf-8>
<title>Offerte</title><style>
@page{size:A4;margin:0}body{font-family:Arial,Helvetica,sans-serif;font-size:12px;margin:0;color:#333}
.page{width:210mm;height:297mm;position:relative}.header{background:#E4B713;color:#fff;padding:25px;clip-path:polygon(0 0,100% 0,100% 70%,0 100%)}
.section{padding:0 25px}.prod{width:100%;border-collapse:collapse;margin-top:15px}
.prod tr:nth-child(even){background:#fafafa}th,td{padding:6px;border-bottom:1px solid #fff}th{text-align:left}
.sep{height:3px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px}
</style></head><body>
<div class=page>
  <div class=header><h1>Cupholder voor {{c.name}}</h1>
    <p>Offertenr {{c.offer_number}}<br>Datum {{today}} – geldig tot {{valid}}</p></div>
  <div class=section><h2>Productoverzicht</h2>
    <table class=prod><tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
      <th style="text-align:right">Prijs/stuk</th><th style="text-align:right">Totaal excl.</th></tr>
      {% for r in rows %}<tr>
        <td>{{r.qty}}</td><td>{{r.type}}</td><td>{{r.colour}}</td><td>{{r.detail}}</td>
        <td style="text-align:right">{{r.price}}</td><td style="text-align:right">{{r.total}}</td></tr>{% endfor %}
      {% if special %}<tr><td>1</td><td>Extra</td><td>Special</td><td>Afwijkende kleur</td>
        <td style="text-align:right">€ 480,00</td><td style="text-align:right">€ 480,00</td></tr>{% endif %}
      {% if ship %}<tr><td>1</td><td>Verzendkosten</td><td>-</td><td>Extra zending</td>
        <td style="text-align:right">€ 150,00</td><td style="text-align:right">€ 150,00</td></tr>{% endif %}
    </table>
  </div>
  <div class=section><div class=sep></div>
    <p style="text-align:right">Totaal excl.: € {{'%.2f'%excl}}<br>BTW 21 %: € {{'%.2f'%tax}}
    <br><strong>Totaal incl.: € {{'%.2f'%incl}}</strong></p>
  </div>
</div></body></html>"""
env=Environment(loader=BaseLoader(),autoescape=select_autoescape())
tmpl=env.from_string(TEMPLATE)

def build_html(client:ClientInfo,rows:List[OfferRow])->str:
    excl=sum(r.total for r in rows); tax=round(excl*0.21,2); incl=round(excl+tax,2)
    return tmpl.render(c=client,rows=[r.to_html() for r in rows],
                       today=_dt.date.today().strftime("%d-%m-%Y"),
                       valid=(_dt.date.today()+_dt.timedelta(days=14)).strftime("%d-%m-%Y"),
                       special=any(r.inp.special_band() for r in rows),
                       ship=any(r.inp.quantity>10000 for r in rows),
                       excl=excl,tax=tax,incl=incl)

# ─────────────────────── 5 · PDF (WeasyPrint) ───────────────────────
def html_to_pdf(html:str,target:pathlib.Path):
    from weasyprint import HTML
    HTML(string=html).write_pdf(target)

# ─────────────────────── 6 · COMMAND-LINE  ─────────────────────────
def cli(argv:List[str]|None=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("config",type=pathlib.Path)
    ap.add_argument("-o","--output-dir",type=pathlib.Path,default=pathlib.Path.cwd())
    args=ap.parse_args(argv)

    data=json.loads(args.config.read_text(encoding="utf-8"))
    client=ClientInfo(**data["client"])
    rows=[]
    for d in data["offers"]:
        inp=OfferInput(**d)
        c=unit_cost(inp); p=unit_price(c,inp)
        rows.append(OfferRow(inp,c,p))

    html=build_html(client,rows)
    base=f"offerte_{re.sub(r'[^a-z0-9]','_',client.name.lower())}_{client.offer_number}"
    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    html_path=out/f"{base}.html"; pdf_path=out/f"{base}.pdf"
    html_path.write_text(html,encoding="utf-8")
    try: html_to_pdf(html,pdf_path)
    except Exception as e: print(f"[PDF fout] {e}")
    print("HTML →",html_path); print("PDF  →",pdf_path)

# ─────────────────────── 7 · STREAMLIT-FORM ─────────────────────────
def gui():
    import streamlit as st
    st.set_page_config(page_title="Calix offerte",layout="centered")
    st.title("Calix offerte-generator")

    with st.sidebar:
        st.header("Klant")
        cname=st.text_input("Naam","TEST BV")
        caddr=st.text_input("Adres","Oude Kijk in 't Jatstraat 5, Groningen")
        cnr=st.text_input("Offertenummer","3241234")
        vcount=st.number_input("Aantal varianten",1,5,2,1)

    offers=[]
    for i in range(vcount):
        with st.expander(f"Variant {i+1}",True):
            q=st.number_input("Aantal",1,100000,1000,key=f"q{i}")
            ptype=st.selectbox("Type",("Bedrukt","3D-logo"),key=f"t{i}")
            cols=1 if ptype=="3D-logo" else st.selectbox("Kleuren",(1,2,3),key=f"c{i}")
            band=st.selectbox("Bandje",("Standaard","Special"),key=f"b{i}")
            up=st.slider("Extra %",0.0,1.0,0.10,0.01,key=f"u{i}")
            disc=st.slider("Korting %",0.0,1.0,0.0,0.01,key=f"d{i}")
            offers.append(dict(quantity=int(q),product_type=ptype,colours=int(cols),
                               band_color=band,extra_increase_pct=up,discount_pct=disc))
    if st.button("Genereer"):
        client=ClientInfo(cname,caddr,cnr); rows=[]
        for d in offers:
            inp=OfferInput(**d); c=unit_cost(inp); p=unit_price(c,inp); rows.append(OfferRow(inp,c,p))
        html=build_html(client,rows)
        st.markdown("### Preview"); st.components.v1.html(html,height=600,scrolling=True)
        st.download_button("Download HTML",html,"offerte.html","text/html")
        try:
            from weasyprint import HTML; pdf=HTML(string=html).write_pdf()
            st.download_button("Download PDF",pdf,"offerte.pdf","application/pdf")
        except Exception as e: st.warning(f"PDF mislukt: {e}")

# ─────────────────────── 8 · ENTRYPOINT ─────────────────────────────
if __name__=="__main__":
    if "streamlit" in pathlib.Path(sys.argv[0]).name.lower():
        gui()
    elif len(sys.argv)==1:
        print("Gebruik: python calix_quote.py offer_input.json  of  streamlit run calix_quote.py")
    else:
        cli()
