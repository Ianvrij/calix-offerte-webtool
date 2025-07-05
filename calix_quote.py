#!/usr/bin/env python3
"""
calix_quote.py – Calix-offertegenerator (HTML + PDF)
===================================================

* Excel-logica herschreven in Python
* Output als HTML & PDF (Jinja2 + WeasyPrint)
* Werkt als CLI én Streamlit-webapp – één bestand
"""
from __future__ import annotations
import json, re, unicodedata, datetime as _dt, pathlib, sys, argparse
from dataclasses import dataclass
from typing import List, Dict

# ────────────── DATA-KLASSEN ──────────────
@dataclass
class OfferInput:
    quantity: int
    product_type: str          # "Bedrukt" | "3D-logo"
    colours: int               # 1..3 (alleen bij Bedrukt)
    band_color: str            # "Standaard" | "Special"
    extra_increase_pct: float = 0.10
    discount_pct: float = 0.0
    def special_band(self) -> bool: return self.band_color.lower() == "special"

@dataclass
class ClientInfo:
    name: str
    address: str
    offer_number: str

@dataclass
class OfferRow:
    inp:   OfferInput
    cost:  float
    price: float
    @property
    def total(self) -> float: return self.price * self.inp.quantity
    def html(self) -> Dict[str,str]:
        detail = (f"{self.inp.colours}-kleur tampondruk – ontwerpcontrole"
                  if self.inp.product_type.lower() == "bedrukt"
                  else "3D-logo inbegrepen – ontwerpcontrole")
        return {
            "qty":    self.inp.quantity,
            "type":   self.inp.product_type,
            "colour": self.inp.band_color,
            "detail": detail,
            "price":  f"€ {self.price:.2f}",
            "total":  f"€ {self.total:.2f}",
        }

# ────────────── TEMPLATE ──────────────
_slug = lambda s: re.sub(r"[^a-z0-9_-]+","_", unicodedata.normalize("NFKD",s)
                         .encode("ascii","ignore").decode()).strip("_") or "offerte"

from jinja2 import Environment, BaseLoader, select_autoescape
env = Environment(loader=BaseLoader(), autoescape=select_autoescape())

TEMPLATE = """<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"><title>Offerte</title>
{% raw %}
<style>
 @page{size:A4;margin:0}
 body{font-family:Arial,Helvetica,sans-serif;font-size:12px;margin:0;color:#333}
 .page{width:210mm;height:297mm;position:relative}
 .header{background:#E4B713;color:#fff;padding:25px;clip-path:polygon(0 0,100% 0,100% 70%,0 100%)}
 .header h1{margin:0;font-size:26px}
 .section{padding:0 25px}
 .prod{width:100%;border-collapse:collapse;margin-top:15px}
 .prod tr:nth-child(even){background:#fafafa}
 th,td{padding:6px;border-bottom:1px solid #fff}th{text-align:left}
 .totals-sep{height:3px;background:#E4B713;width:100%;margin:4px 0;border-radius:2px}
</style>
{% endraw %}
</head><body>
<div class="page">
 <div class="header">
  <h1>Cupholder voor {{ client.name }}</h1>
  <p>Offertenr {{ client.offer_number }}<br>
     Datum {{ today }} – geldig tot {{ valid }}<br>
     {{ client.address }}</p>
 </div>

 <div class="section">
  <h2>Productoverzicht</h2>
  <table class="prod">
   <tr><th>Aantal</th><th>Type</th><th>Kleur</th><th>Details</th>
       <th style="text-align:right">Prijs/stuk</th><th style="text-align:right">Totaal excl.</th></tr>
   {% for r in rows %}
   <tr><td>{{ r.qty }}</td><td>{{ r.type }}</td><td>{{ r.colour }}</td><td>{{ r.detail }}</td>
       <td style="text-align:right">{{ r.price }}</td><td style="text-align:right">{{ r.total }}</td></tr>
   {% endfor %}
   {% if special %}
   <tr><td>1</td><td>Extra</td><td>Special</td><td>Afwijkende kleur</td>
       <td style="text-align:right">€ 480,00</td><td style="text-align:right">€ 480,00</td></tr>
   {% endif %}
   {% if ship %}
   <tr><td>1</td><td>Verzendkosten</td><td>-</td><td>Extra zending</td>
       <td style="text-align:right">€ 150,00</td><td style="text-align:right">€ 150,00</td></tr>
   {% endif %}
  </table>
 </div>

 <div class="section"><div class="totals-sep"></div>
  <p style="text-align:right">
    Totaal excl.: € {{ '%.2f' % excl }}<br>
    BTW 21%: € {{ '%.2f' % tax }}<br>
    <strong>Totaal incl.: € {{ '%.2f' % incl }}</strong>
  </p>
 </div>
</div></body></html>"""
TEMPLATE_OBJ = env.from_string(TEMPLATE)

# ────────────── PRIJS-TABELLEN (voorbeeld-getallen) ──────────────
OFF_GEBREMA  = {"<3000":0.30,"<10000":0.28,"<100000":0.26,"otherwise":0.24}
EXTRA_KOSTEN = {"transport":150,"special":480}
ARTISAN      = [
    (200,(0.65,0.72,0.79)),(500,(0.55,0.62,0.69)),(1000,(0.50,0.57,0.64)),
    (5000,(0.45,0.52,0.59)),(10000,(0.40,0.47,0.54)),(20000,(0.35,0.42,0.49)),
    (999999,(0.30,0.37,0.44))
]
# ────────────── KOSTEN- & PRIJSLOGICA ──────────────
def _spuitgiet(q: int, t: str, special: bool) -> float:
    key   = "<3000" if q < 3000 else "<10000" if q < 10000 else "<100000" if q < 100000 else "otherwise"
    base  = OFF_GEBREMA[key] if t.lower() == "3d-logo" else (1.10 if q < 3000 else OFF_GEBREMA[key])
    extra = EXTRA_KOSTEN["special"] / q if special else 0
    return base + extra

def _artisan(q: int, colours: int) -> float:
    for upper, prices in ARTISAN:
        if q <= upper:
            return prices[colours-1]
    raise ValueError("Aantal valt buiten Artisan-staffel")

def unit_cost(inp: OfferInput) -> float:
    cost = _spuitgiet(inp.quantity, inp.product_type, inp.special_band())
    if inp.product_type.lower() == "bedrukt":
        cost += _artisan(inp.quantity, inp.colours)
    if inp.quantity < 10000:
        cost += EXTRA_KOSTEN["transport"] / inp.quantity
    return round(cost, 4)

def unit_price(cost: float, inp: OfferInput) -> float:
    return round(cost * (1 + inp.extra_increase_pct) * (1 - inp.discount_pct), 4)
# ────────────── HTML & PDF BUILDERS ──────────────
def build_html(client: ClientInfo, rows: List[OfferRow]) -> str:
    excl = sum(r.total for r in rows)
    tax  = round(excl * 0.21, 2)
    incl = round(excl + tax, 2)
    return TEMPLATE_OBJ.render(
        client   = client,
        rows     = [r.html() for r in rows],
        today    = _dt.date.today().strftime("%d-%m-%Y"),
        valid    = (_dt.date.today() + _dt.timedelta(days=14)).strftime("%d-%m-%Y"),
        special  = any(r.inp.special_band() for r in rows),
        ship     = any(r.inp.quantity > 10000 for r in rows),
        excl     = excl, tax = tax, incl = incl
    )

def html2pdf(html: str, target: pathlib.Path):
    from weasyprint import HTML
    HTML(string=html).write_pdf(target)

# ────────────── CLI-ENTRY ──────────────
def cli(argv=None):
    ap = argparse.ArgumentParser(description="Genereer Calix-offerte (HTML + PDF)")
    ap.add_argument("config", type=pathlib.Path)
    ap.add_argument("-o", "--output-dir", type=pathlib.Path, default=pathlib.Path.cwd())
    args = ap.parse_args(argv)

    data   = json.loads(args.config.read_text("utf-8"))
    client = ClientInfo(**data["client"])

    rows: List[OfferRow] = []
    for od in data["offers"]:
        inp   = OfferInput(**od)
        cost  = unit_cost(inp)
        price = unit_price(cost, inp)
        rows.append(OfferRow(inp, cost, price))

    html = build_html(client, rows)
    base = f"offerte_{_slug(client.name)}_{client.offer_number}"
    out  = args.output_dir ; out.mkdir(parents=True, exist_ok=True)

    (out / f"{base}.html").write_text(html, "utf-8")
    try:
        html2pdf(html, out / f"{base}.pdf")
    except Exception as e:
        print("[WAARSCHUWING] PDF-export mislukt:", e)

    print("✔ Offerte opgeslagen in", out.resolve())
# ────────────── STREAMLIT-GUI ──────────────
def gui():
    import streamlit as st, streamlit.components.v1 as components
    st.set_page_config(page_title="Calix offerte", page_icon="📄", layout="wide")
    st.title("Calix offerte generator")

    with st.sidebar:
        name    = st.text_input("Naam klant")
        address = st.text_input("Adres")
        nr      = st.text_input("Offertenummer")
        var_cnt = st.number_input("Aantal varianten", 1, 5, 1)

    offers = []
    for i in range(int(var_cnt)):
        with st.expander(f"Variant {i+1}", expanded=True):
            q     = st.number_input("Aantal", 1, 100_000, 1000, key=f"q{i}")
            t     = st.selectbox("Type", ["Bedrukt", "3D-logo"], key=f"t{i}")
            cols  = 1 if t == "3D-logo" else st.selectbox("Kleuren", [1,2,3], key=f"c{i}")
            band  = st.selectbox("Band-kleur", ["Standaard", "Special"], key=f"b{i}")
            up    = st.slider("Extra verhoging %", 0.0, 1.0, 0.10, 0.01, key=f"u{i}")
            disc  = st.slider("Korting %", 0.0, 1.0, 0.0, 0.01, key=f"d{i}")
            offers.append(dict(
                quantity=int(q), product_type=t, colours=int(cols), band_color=band,
                extra_increase_pct=up, discount_pct=disc
            ))

    if st.button("Genereer offerte"):
        if not (name and address and nr):
            st.error("Vul eerst alle klantgegevens in."); st.stop()

        client = ClientInfo(name, address, nr)
        rows   = [OfferRow(inp:=OfferInput(**d), unit_cost(inp), unit_price(unit_cost(inp), inp))
                  for d in offers]
        html   = build_html(client, rows)

        # preview
        components.html(html, height=1050, scrolling=True)

        st.download_button("Download HTML", html, "offerte.html", "text/html")
        try:
            from weasyprint import HTML as WPHTML
            pdf = WPHTML(string=html).write_pdf()
            st.download_button("Download PDF", pdf, "offerte.pdf", "application/pdf")
        except Exception as e:
            st.warning(f"PDF-export mislukt: {e}")

# ────────────── ENTRYPOINT ──────────────
if __name__ == "__main__":
    if "streamlit" in pathlib.Path(sys.argv[0]).name.lower():
        gui()
    elif len(sys.argv) == 1:
        print("CLI : python calix_quote.py offer_input.json --output-dir ./out\n"
              "GUI : streamlit run calix_quote.py")
    else:
        cli()
