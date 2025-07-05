#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calix – offerte-generator (Streamlit)
HTML = 1-op-1 VBA-markup │ PDF = headless Chromium (pyppeteer)
"""

from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

import streamlit as st
from pyppeteer import launch

SELF = Path(__file__).resolve()

# ── Helpers ────────────────────────────────────────────────────────────────
def eur(val: float | Decimal) -> str:
    q = Decimal(val).quantize(Decimal("0.01"), ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"

def tampon(k: int) -> str:
    return ("1-kleur" if k == 1 else f"{k}-kleuren") + \
           " tampondruk, Inclusief Ontwerpcontrole"

async def _html2pdf(html: str) -> bytes:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setContent(html, waitUntil="networkidle0")
    pdf = await page.pdf(format="A4", printBackground=True,
                         margin={"top":"0","bottom":"0","left":"0","right":"0"})
    await browser.close()
    return pdf
def html_to_pdf_bytes(html: str) -> bytes:
    return asyncio.get_event_loop().run_until_complete(_html2pdf(html))

# ── Kostprijs-tabellen (exact Excel) ───────────────────────────────────────
STAFFEL = [1000, 2000, 5000, 7500, 10000, 50000]
def brk(a:int)->int:
    return next(s for s in STAFFEL if a<=s) if a<50000 else 50000

TAB = {
    "3D":      {1000:2.79,2000:1.63,5000:1.09,7500:0.97,10000:0.91,50000:0.75},
    "B1":      {1000:2.07,2000:1.94,5000:1.38,7500:1.36,10000:1.27,50000:1.20},
    "B2":      {1000:2.37,2000:2.15,5000:1.51,7500:1.48,10000:1.35,50000:1.24},
    "B3":      {1000:2.57,2000:2.31,5000:1.61,7500:1.57,10000:1.43,50000:1.28},
}
def kostprijs(t:str,a:int,k:int)->float:
    key = "3D" if t=="3D-logo" else f"B{k}"
    return TAB[key][brk(a)]
def verkoop(kost:float, verh:float, kort:float)->float:
    return kost*(1+verh/100)*(1-kort/100)

# ── Streamlit ui ───────────────────────────────────────────────────────────
st.set_page_config("Calix Offerte",layout="centered")
st.title("Calix – Offertegenerator")

# hoofdoptie
st.header("Hoofdoptie")
c1,c2 = st.columns(2)
with c1:
    klant   = st.text_input("Naam klant")
    adres   = st.text_input("Adres")
    offnr   = st.text_input("Offertenummer")
    aantal  = st.number_input("Aantal",1,value=1000,step=100)
with c2:
    typ     = st.selectbox("Type",["Bedrukt","3D-logo"])
    kln     = st.selectbox("Aantal kleuren",[1,2,3],disabled=typ!="Bedrukt")
    band    = st.selectbox("Kleur bandje",
              ["Standaard","Special","Zwart","Off White","Blauw","Rood"],index=2)
    korting = st.number_input("Korting (%)",0.0,100.0,0.0,0.5)
    verh    = st.number_input("Verhoging extra (%)",0.0,100.0,10.0,0.5)

opties = st.number_input("Aantal opties (1-4)",1,4,1)

extras=[]
if opties>1:
    st.header("Extra opties")
    for i in range(2,opties+1):
        st.subheader(f"Optie {i}")
        d1,d2,d3,d4 = st.columns(4)
        with d1: a = st.number_input("Aantal",1,value=500,key=f"a{i}")
        with d2: t = st.selectbox("Type",["Bedrukt","3D-logo"],key=f"t{i}")
        with d3:
            kc = st.selectbox("Kleuren",[1,2,3],key=f"kc{i}",disabled=t!="Bedrukt")
        with d4:
            b = st.selectbox("Bandje",
                ["Standaard","Special","Zwart","Off White","Blauw","Rood"],
                key=f"b{i}")
        krt = st.number_input("Korting (%)",0.0,100.0,0.0,0.5,key=f"kr{i}")
        extras.append(dict(aantal=a,type=t,kc=kc,band=b,krt=krt))

# ── Berekenen ──────────────────────────────────────────────────────────────
rows=[]; total=Decimal(0)
def add(a,t,b,oms,p):
    global total
    rows.append(
        f"<tr><td>{a}</td><td>{t}</td><td>{b}</td><td>{oms}</td>"
        f"<td style='text-align:right;'>{eur(p)}</td>"
        f"<td style='text-align:right;'>{eur(p*a)}</td></tr>")
    total+=Decimal(p*a)

kp=kostprijs(typ,aantal,kln); vp=verkoop(kp,verh,korting)
add(aantal,typ,band,tampon(kln) if typ=="Bedrukt"
    else "3D-logo inbegrepen, Inclusief Ontwerpcontrole",vp)

for ex in extras:
    kp=kostprijs(ex["type"],ex["aantal"],ex["kc"])
    vp=verkoop(kp,verh,ex["krt"])
    oms=tampon(ex["kc"]) if ex["type"]=="Bedrukt" else "3D-logo inbegrepen, Inclusief Ontwerpcontrole"
    add(ex["aantal"],ex["type"],ex["band"],oms,vp)

if band.lower()=="special" or any(e["band"].lower()=="special" for e in extras):
    add(1,"Extra","Special","Voor afwijkende kleurkeuze (‘Special’ bandje)",480)
if aantal>10000:
    add(1,"Verzendkosten","–","Extra kosten voor zending",150)

btw       = total*Decimal("0.21")
t_inc     = total+btw

# ── HTML template laden / aanmaken ─────────────────────────────────────────
TPL = SELF.parent/"template_calix.html"
if not TPL.exists():
    TPL.write_text("<!-- plak hier je volledige VBA-HTML in -->",encoding="utf-8")
    st.stop()
html = (TPL.read_text(encoding="utf-8")
        .replace("${KLANT}",klant or "–")
        .replace("${ADRES}",adres or "–")
        .replace("${OFFNR}",offnr or "–")
        .replace("${DATUM}",datetime.now().strftime("%d-%m-%Y"))
        .replace("${GELDIG}",(datetime.now()+timedelta(days=14)).strftime("%d-%m-%Y"))
        .replace("${PRODUCTROWS}","".join(rows))
        .replace("${TOTALEXCL}",eur(total))
        .replace("${BTW}",eur(btw))
        .replace("${TOTAALINC}",eur(t_inc)))

# ── UI output ──────────────────────────────────────────────────────────────
st.download_button("Download HTML",html,"offerte_calix.html","text/html")
st.components.v1.html(html,height=900,scrolling=True)
try:
    pdf = html_to_pdf_bytes(html)
    st.download_button("Download PDF",pdf,"offerte_calix.pdf","application/pdf")
except Exception as e:
    st.error(f"PDF genereren faalde: {e}. Download HTML en print als PDF.")
