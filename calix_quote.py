#!/usr/bin/env python3
"""
calix_quote.py  –  Generate a Calix quotation (HTML + PDF) in pure Python

• Volledige prijs-logica vanuit je Excel-sheet.
• HTML-rendering met Jinja2 (template zit in het script).
• PDF-export via WeasyPrint.
• Command-line én Streamlit-GUI samen in één bestand.

Installeren:
    pip install jinja2 weasyprint streamlit pandas python-dateutil
"""
from __future__ import annotations
import json, re, unicodedata, datetime as _dt, pathlib, subprocess, argparse, sys
from dataclasses import dataclass
from typing import List, Dict, Any

# ───────────────────── 1 · DATA CLASSES ─────────────────────
@dataclass
class OfferInput:
    quantity: int
    product_type: str          # "Bedrukt" or "3D-logo"
    colours: int               # 1,2,3 … (genegeerd bij 3D-logo)
    band_color: str            # "Standaard" / "Special"
    extra_increase_pct: float = 0.10
    discount_pct: float = 0.0
    def special_band(self) -> bool:
        return self.band_color.lower() == "special"

@dataclass
class ClientInfo:
    name: str
    address: str
    offer_number: str

@dataclass
class OfferRow:
    input: OfferInput
    unit_cost: float
    unit_price: float
    @property
    def total_price(self) -> float:
        return self.unit_price * self.input.quantity
    def as_html_dict(self) -> Dict[str, Any]:
        inp = self.input
        detail = (f"{inp.colours}-kleur{'en' if inp.colours>1 else ''} tampondruk – ontwerpcontrole"
                  if inp.product_type.lower() == "bedrukt"
                  else "3D-logo inbegrepen – ontwerpcontrole")
        return dict(
            qty=inp.quantity, type=inp.product_type, colour=inp.band_color,
            detail=detail, price=f"€ {self.unit_price:,.2f}",
            total=f"€ {self.total_price:,.2f}"
        )

# ───────────────────── 2 · HELPERS ──────────────────────────
_slug = lambda t: re.sub(r"[^a-z0-9_-]+","_", unicodedata.normalize('NFKD',t)
                         .encode('ascii','ignore').decode()).strip('_').lower() or "offerte"

from jinja2 import Environment, BaseLoader, select_autoescape
TEMPLATE = r"""<!DOCTYPE html><html lang=nl><head><meta charset=utf-8>
<title>Offerte</title>
<style>@page{size:A4;margin:0}
body{font-family:Arial,Helvetica,sans-serif;font-size:12px;margin:0;color:#333}
.page{width:210mm;height:297mm;position:relative}
.header{background:#E4B713;color:#fff;padding:25px;clip-path:polygon(0 0,100% 0,100% 70%,0 100%)}
.header h1{margin:0;font-size:26px}
.section{padding:0 25px}
.prod{width:100%;border-collapse:collapse;margin-top:15px}
.prod tr:nth-child(even){background:#fafafa}
th,td{padding:6px;border-bottom:1px solid #fff}th{text-align:left}
.totals-sep{height:3px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px}
</style></head><body>
<div class=page><div class=header><h1>Cupholder voor {{client.name}}</h1>
<p>Offertenummer {{client.offer_number}}<br>Datum {{today}} – geldig tot {{valid}}</p></div>
<div class=section><h2>Productoverzicht</h2><table class=prod>
<tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
    <th style="text-align:right">Prijs/stuk</th><th style="text-align:right">Totaal excl.</th></tr>
{% for r in rows %}<tr><td>{{r.qty}}</td><td>{{r.type}}</td><td>{{r.colour}}</td>
<td>{{r.detail}}</td><td style="text-align:right">{{r.price}}</td>
<td style="text-align:right">{{r.total}}</td></tr>{% endfor %}
{% if special %}<tr><td>1</td><td>Extra</td><td>Special</td><td>Afwijkende kleur</td>
<td style="text-align:right">€ 480,00</td><td style="text-align:right">€ 480,00</td></tr>{% endif %}
{% if ship %}<tr><td>1</td><td>Verzendkosten</td><td>-</td><td>Extra zending</td>
<td style="text-align:right">€ 150,00</td><td style="text-align:right">€ 150,00</td></tr>{% endif %}
</table></div>
<div class=section><div class=totals-sep></div>
<p style="text-align:right">Totaal excl.: € {{excl:.2f}}<br>BTW 21 %: € {{tax:.2f}}
<br><strong>Totaal incl.: € {{incl:.2f}}</strong></p></div>
</div></body></html>"""
env = Environment(loader=BaseLoader(), autoescape=select_autoescape())
tmpl = env.from_string(TEMPLATE)

# ───────────────────── 3 · BASIS-TABELWAARDEN ─────────────────
OFF_GEBREMA = {"<3000":0.30, "<10000":0.28, "<100000":0.26, "otherwise":0.24}   # TODO cijfers invullen
EXTRA_KOSTEN = {"transport":150, "special_band":480}
ARTISAN_BASE = [
    (200,(0.65,0.72,0.79)), (500,(0.55,0.62,0.69)), (1000,(0.50,0.57,0.64)),
    (5000,(0.45,0.52,0.59)), (10000,(0.40,0.47,0.54)), (20000,(0.35,0.42,0.49)),
    (999999,(0.30,0.37,0.44))
]

# ───────────────────── 4 · PRICING LOGIC ─────────────────────
def spuitgiet_price(q:int, t:str, special:bool) -> float:
    if t.lower()=="3d-logo":
        key = "<3000" if q<3000 else "<10000" if q<10000 else "<100000" if q<100000 else "otherwise"
        base = OFF_GEBREMA[key]
    else:
        base = 1.10 if q<3000 else OFF_GEBREMA["<10000" if q<10000 else "<100000" if q<100000 else "otherwise"]
    if special:
        base += EXTRA_KOSTEN["special_band"]/q
    return base

def artisan_price(q:int, colours:int) -> float:
    for upper, tup in ARTISAN_BASE:
        if q <= upper:
            return tup[colours-1]
    raise ValueError("No artisan price bracket")

def unit_cost(inp: OfferInput) -> float:
    cost = spuitgiet_price(inp.quantity, inp.product_type, inp.special_band())
    if inp.product_type.lower() == "bedrukt":
        cost += artisan_price(inp.quantity, inp.colours)
    cost += EXTRA_KOSTEN["transport"]/inp.quantity if inp.quantity < 10000 else 0
    return round(cost,4)

def unit_price(cost:float, inp:OfferInput) -> float:
    return round(cost*(1+inp.extra_increase_pct)*(1-inp.discount_pct),4)

# ───────────────────── 5 · HTML/PDF BUILDERS ─────────────────
def build_html(client:ClientInfo, rows:List[OfferRow]) -> str:
    excl = sum(r.total_price for r in rows)
    tax  = round(excl*0.21,2)
    incl = round(excl+tax,2)
    return tmpl.render(
        client=client, rows=[r.as_html_dict() for r in rows],
        today=_dt.date.today().strftime("%d-%m-%Y"),
        valid=(_dt.date.today()+_dt.timedelta(days=14)).strftime("%d-%m-%Y"),
        special=any(r.input.special_band() for r in rows),
        ship=any(r.input.quantity>10000 for r in rows),
        excl=excl, tax=tax, incl=incl
    )

def html_to_pdf(html:str, target:pathlib.Path):
    from weasyprint import HTML
    HTML(string=html).write_pdf(target)

# ───────────────────── 6 · CLI ENTRY ─────────────────────────
def cli(argv:List[str]|None=None):
    ap = argparse.ArgumentParser(description="Generate Calix offer (HTML+PDF)")
    ap.add_argument("config", type=pathlib.Path)
    ap.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path.cwd())
    args = ap.parse_args(argv)

    data = json.loads(args.config.read_text(encoding="utf-8"))
    client = ClientInfo(**data["client"])
    rows: List[OfferRow] = []
    for od in data["offers"]:
        inp = OfferInput(**od)
        c   = unit_cost(inp)
        p   = unit_price(c, inp)
        rows.append(OfferRow(inp, c, p))

    html = build_html(client, rows)
    base = f"offerte_{_slug(client.name)}_{client.offer_number}"
    out_dir = args.output_dir; out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir/f"{base}.html"
    pdf_path  = out_dir/f"{base}.pdf"
    html_path.write_text(html, encoding="utf-8")
    try:
        html_to_pdf(html, pdf_path)
        print(f"Saved PDF  → {pdf_path}")
    except Exception as e:
        print(f"[warn] PDF failed: {e}")
    print(f"Saved HTML → {html_path}")

# ───────────────────── 7 · STREAMLIT UI ─────────────────────
def run_gui():
    import streamlit as st
    st.set_page_config(page_title="Calix Offerte", layout="centered")
    st.title("Calix Offerte Generator")

    with st.sidebar:
        st.header("Klant­gegevens")
        name      = st.text_input("Naam klant", "TEST BV")
        address   = st.text_input("Adres", "Oude Kijk in 't Jatstraat 5, 9712 EA Groningen")
        offer_nr  = st.text_input("Offertenummer", "3241234")
        variants  = st.number_input("Aantal varianten", 1, 5, 2, 1, key="varcount")

    offers: List[Dict[str,Any]] = []
    for i in range(variants):
        with st.expander(f"Variant {i+1}", expanded=True):
            qty      = st.number_input("Aantal stuks", 1, 100000, 1000, key=f"q{i}")
            ptype    = st.selectbox("Type", ("Bedrukt", "3D-logo"), key=f"t{i}")
            cols     = 1 if ptype=="3D-logo" else st.selectbox("Aantal kleuren", (1,2,3), key=f"c{i}")
            band     = st.selectbox("Kleur bandje", ("Standaard", "Special"), key=f"b{i}")
            up_pct   = st.slider("Extra verhoging %", 0.0, 1.0, 0.10, 0.01, key=f"u{i}")
            disc_pct = st.slider("Korting %", 0.0, 1.0, 0.00, 0.01, key=f"d{i}")
            offers.append(dict(
                quantity=int(qty), product_type=ptype, colours=int(cols),
                band_color=band, extra_increase_pct=up_pct, discount_pct=disc_pct))

    if st.button("Genereer offerte"):
        client = ClientInfo(name, address, offer_nr)
        rows: List[OfferRow] = []
        for od in offers:
            inp = OfferInput(**od)
            c   = unit_cost(inp)
            p   = unit_price(c, inp)
            rows.append(OfferRow(inp, c, p))

        html = build_html(client, rows)
        st.success("Offerte gegenereerd!")
        st.markdown(html, unsafe_allow_html=True)

        st.download_button("Download HTML", html, file_name="offerte.html", mime="text/html")
        try:
            from weasyprint import HTML as WPHTML
            pdf_bytes = WPHTML(string=html).write_pdf()
            st.download_button("Download PDF", pdf_bytes, file_name="offerte.pdf",
                               mime="application/pdf")
        except Exception as e:
            st.warning(f"PDF genereren mislukt: {e}")

# ───────────────────── 8 · ENTRYPOINT ───────────────────────
if __name__ == "__main__":
    # Streamlit roept het script aan met zijn eigen executable pad
    if "streamlit" in pathlib.Path(sys.argv[0]).name.lower():
        run_gui()
    elif len(sys.argv) == 1:
        print("Gebruik:\n  • CLI :  python calix_quote.py offer_input.json"
              "\n  • GUI :  streamlit run calix_quote.py")
    else:
        cli()
