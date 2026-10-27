"""Builds the 12 synthetic test receipts: HTML -> PNG (headless Edge) -> Pillow degrade -> JPEG, plus ground-truth JSON.
All businesses are fictional. GSTINs/ABNs/VAT numbers are obviously fake.
Run:  python test/make_receipts.py        (from the receipts-demo folder)
"""
import json, math, random, subprocess, sys
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC, OUT, TRUTH = ROOT / "receipts-src", ROOT / "receipts", ROOT / "truth"
for p in (SRC, OUT, TRUTH): p.mkdir(exist_ok=True)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
random.seed(7); np.random.seed(7)
q2 = lambda x: D(x).quantize(D("0.01"), ROUND_HALF_UP)
f = lambda x: float(q2(x))
m = lambda x: f"{q2(x):,.2f}"

# ---------------------------------------------------------------- data
R = {}
def add(id, **kw): R[id] = dict(id=id, **kw)

# 1 AU cafe: GST 10% included in prices
items = [("Flat white", 2, "4.80"), ("Smashed avocado on sourdough", 1, "18.50"), ("Banana bread, toasted", 1, "7.00")]
tot = sum(q2(D(a) * q) for _, q, a in items)  # 35.10 incl GST
add("au-cafe", kind="thermal", vendor="Tin Roof Coffee Co", addr="41 Rokeby Rd, Subiaco WA 6008", tax_id="ABN 12 345 678 901",
    title="TAX INVOICE", inv="TR-20871", date_txt="Fri 18 Sep 2026  08:12", date="2026-09-18", cur="AUD", sym="$",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=True,
    lines=[("Subtotal (ex GST)", m(tot - q2(tot / 11))), ("GST 10%", m(tot / 11))], tax=f(tot / 11), tax_lbl="GST", subtotal=f(tot - q2(tot / 11)),
    total=f(tot), pay="Visa contactless", cat="Meals", footer="Prices include GST. Thanks for stopping by!", expect={})

# 2 India GST tax invoice, CGST + SGST
items = [("A4 copier paper 75 GSM (ream)", "4802", 10, "285.00"), ("Gel pens, box of 10", "9608", 4, "120.00"), ("Box file, foolscap", "4820", 6, "95.00"), ("Stapler, heavy duty", "8472", 1, "245.00")]
taxable = sum(q2(D(r) * q) for _, _, q, r in items)
cg = q2(taxable * D("0.09")); tot_raw = taxable + cg * 2; total = tot_raw.quantize(D("1"), ROUND_HALF_UP); ro = total - tot_raw
add("in-gst", kind="invoice_in", vendor="Shree Mahalakshmi Stationers", addr="14, Ellisbridge Market, Ahmedabad, Gujarat 380006", tax_id="GSTIN 24AAAAA0000A1Z5",
    title="TAX INVOICE", inv="SMS/26-27/0412", date_txt="14/08/2026", date="2026-08-14", cur="INR", sym="Rs ",
    items=[(d, q, f(D(r) * q), h, r) for d, h, q, r in items], taxable=f(taxable), cgst=f(cg), sgst=f(cg), ro=f(ro),
    tax=f(cg * 2), tax_lbl="GST", subtotal=f(taxable), total=f(total), pay="UPI", cat="Office supplies",
    buyer="Lumen Learning Pvt Ltd, Ahmedabad", expect={})

# 3 India petrol pump (no GST on fuel)
amt = q2(D("28.43") * D("102.76"))
add("in-petrol", kind="thermal", vendor="Jai Ambe Fuel Station", addr="NH-48, Near Toll Plaza, Vapi, Gujarat", tax_id="GSTIN 24AAAAA0000B1Z6",
    title="FUEL RECEIPT", inv="4410237", date_txt="03/09/2026  15:42:08", date="2026-09-03", cur="INR", sym="Rs ",
    items=[("Petrol (MS)  28.43 L @ 102.76", D("28.43"), f(amt))], show_unit=False, raw_items=True,
    lines=[("Nozzle 3   Veh GJ15XX0000", ""), ("Density 0.7392", "")], tax=None, tax_lbl="", subtotal=None,
    total=f(amt), pay="Card", cat="Fuel", footer="Thank you. Drive safe.", expect={})

# 4 UK receipt with VAT 20% included
items = [("Soup of the day", 1, "6.50"), ("Fish and chips", 1, "14.95"), ("Sparkling water", 2, "3.20"), ("Sticky toffee pudding", 1, "7.25")]
tot = sum(q2(D(a) * q) for _, q, a in items)
vat = q2(tot * 20 / 120)
add("uk-vat", kind="thermal", vendor="Hollybush Bistro", addr="22 Kirkgate, Leeds LS2 7DJ", tax_id="VAT No. GB 000 0000 00",
    title="RECEIPT", inv="Table 7 / Chk 30418", date_txt="17/09/2026  19:34", date="2026-09-17", cur="GBP", sym="£",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=True,
    lines=[("Net", m(tot - vat)), ("VAT 20%", m(vat))], tax=f(vat), tax_lbl="VAT", subtotal=f(tot - vat),
    total=f(tot), pay="Visa contactless", cat="Meals", footer="VAT included in prices. Service not included.", expect={})

# 5 US store, sales tax 8.25%
items = [("Copy paper 500ct", 2, "8.99"), ("Sticky notes 3-pack", 1, "5.49"), ("Dry erase markers 6pk", 1, "6.29"), ("USB-C cable 6ft", 1, "12.99")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.0825"))
add("us-store", kind="thermal", vendor="Lakeview Office and Supply", addr="1180 Congress Ave, Austin TX 78701", tax_id="",
    title="STORE #0417", inv="Trans 0417-88213", date_txt="10/04/2026  12:51 PM", date="2026-10-04", cur="USD", sym="$",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=True,
    lines=[("SUBTOTAL", m(sub)), ("SALES TAX 8.25%", m(tx))], tax=f(tx), tax_lbl="Sales tax", subtotal=f(sub),
    total=f(sub + tx), pay="Mastercard ending 4821", cat="Office supplies", footer="Returns within 30 days with receipt.", expect={})

# 6 Taxi, UAE VAT 5%
items = [("Trip fare, Dubai Marina to DIFC", 1, "38.50"), ("Salik toll", 1, "4.00"), ("Booking fee", 1, "4.00")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.05"))
add("taxi", kind="thermal", vendor="Gulf Cab Co", addr="Dubai, United Arab Emirates", tax_id="TRN 100000000000003",
    title="TAXI RECEIPT", inv="TRIP 5589-2204", date_txt="27 Sep 2026  21:14", date="2026-09-27", cur="AED", sym="AED ",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=False,
    lines=[("Distance 31.4 km", ""), ("Subtotal", m(sub)), ("VAT 5%", m(tx))], tax=f(tx), tax_lbl="VAT", subtotal=f(sub),
    total=f(sub + tx), pay="Cash", cat="Travel", footer="Thank you for riding with us.", expect={})

# 7 SaaS invoice (EUR, VAT 23%)
items = [("Pro plan, 5 seats, Oct 2026", 5, "12.00"), ("Extra storage, 100 GB", 2, "4.00")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.23"))
add("saas", kind="saas", vendor="Quillbase Software Ltd", addr="Grand Canal Quay, Dublin 2, Ireland", tax_id="VAT IE0000000A",
    title="Invoice", inv="INV-2026-004471", date_txt="1 October 2026", date="2026-10-01", cur="EUR", sym="€",
    items=[(d, q, f(D(a) * q), a) for d, q, a in items], tax=f(tx), tax_lbl="VAT", subtotal=f(sub), total=f(sub + tx),
    pay="Visa ending 4242", cat="Software", expect={})

# 8 Hardware / materials docket (AUD, GST added)
items = [("Treated pine 90x45 3.0m", 24, "8.45"), ("Plasterboard 10mm 2400x1200", 8, "16.90"), ("Plasterboard screws 1000pk", 2, "14.50"), ("General purpose cement 20kg", 5, "9.80")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.10"))
add("hardware", kind="docket", vendor="Westgate Building Supplies", addr="Lot 9 Bennett Rd, Kwinana WA 6167", tax_id="ABN 98 765 432 109",
    title="TAX INVOICE / DELIVERY DOCKET", inv="D-558201", date_txt="22/09/2026", date="2026-09-22", cur="AUD", sym="$",
    items=[(d, q, f(D(a) * q), a) for d, q, a in items], tax=f(tx), tax_lbl="GST", subtotal=f(sub), total=f(sub + tx),
    pay="On account", cat="Materials", expect={})

# 9 Totals do not add up (printed total is wrong on purpose)
items = [("Classic burger", 1, "11.50"), ("Fries", 1, "4.25"), ("Chocolate shake", 1, "6.00")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.08"))
add("mismatch", kind="thermal", vendor="Corner Booth Diner", addr="305 Main St, Tulsa OK 74103", tax_id="",
    title="GUEST CHECK", inv="Check 11902", date_txt="09/12/2026  13:07", date="2026-09-12", cur="USD", sym="$",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=False,
    lines=[("SUBTOTAL", m(sub)), ("TAX 8%", m(tx))], tax=f(tx), tax_lbl="Sales tax", subtotal=f(sub),
    total=26.49, pay="Cash", cat="Meals", footer="Thanks, come again.", expect={"totals_mismatch": True})

# 10 Very blurry pharmacy receipt
items = [("Paracetamol 500mg x20", 1, "4.95"), ("Vitamin C 1000mg x60", 1, "16.99"), ("Hand sanitiser 250ml", 2, "5.50")]
tot = sum(q2(D(a) * q) for _, q, a in items); gst = q2(D("4.95") * 0 + D("16.99") / 11 + D("11.00") / 11)  # only some lines taxable
add("blurry", kind="thermal", vendor="Lotus Pharmacy", addr="Shop 3, 88 Hay St, Perth WA 6000", tax_id="ABN 55 555 555 555",
    title="TAX INVOICE", inv="LP-30551", date_txt="05/10/2026  16:20", date="2026-10-05", cur="AUD", sym="$",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=True,
    lines=[("GST included", m(gst))], tax=f(gst), tax_lbl="GST", subtotal=None,
    total=f(tot), pay="EFTPOS", cat="Other", footer="Items marked * are GST free.", expect={"unreadable": True})

# 11 India IGST (interstate), crumpled photo
items = [("Wireless mouse", "8471", 3, "450.00"), ("Keyboard, wired USB", "8471", 2, "1250.00"), ("USB 3.0 hub, 4 port", "8471", 1, "899.00")]
taxable = sum(q2(D(r) * q) for _, _, q, r in items); ig = q2(taxable * D("0.18")); tot_raw = taxable + ig
total = tot_raw.quantize(D("1"), ROUND_HALF_UP); ro = total - tot_raw
add("in-igst", kind="invoice_in", vendor="Kaveri Digital Solutions", addr="27, Brigade Road Annex, Bengaluru, Karnataka 560001", tax_id="GSTIN 29AAAAA0000C1Z2",
    title="TAX INVOICE", inv="KDS/0098", date_txt="29/09/2026", date="2026-09-29", cur="INR", sym="Rs ",
    items=[(d, q, f(D(r) * q), h, r) for d, h, q, r in items], taxable=f(taxable), igst=f(ig), ro=f(ro),
    tax=f(ig), tax_lbl="GST", subtotal=f(taxable), total=f(total), pay="Bank transfer", cat="Office supplies",
    buyer="Lumen Learning Pvt Ltd, Ahmedabad (interstate supply)", expect={})

# 12 Faded thermal deli receipt (Seattle, 10.25%)
items = [("Turkey sandwich", 1, "11.95"), ("Tomato soup", 1, "5.50"), ("Iced tea", 1, "3.25")]
sub = sum(q2(D(a) * q) for _, q, a in items); tx = q2(sub * D("0.1025"))
add("faded", kind="thermal", vendor="Cedar Grove Deli", addr="702 Pike St, Seattle WA 98101", tax_id="",
    title="CUSTOMER COPY", inv="Ord 2291", date_txt="10/21/2026  12:38", date="2026-10-21", cur="USD", sym="$",
    items=[(d, q, f(D(a) * q)) for d, q, a in items], show_unit=False,
    lines=[("SUBTOTAL", m(sub)), ("TAX 10.25%", m(tx))], tax=f(tx), tax_lbl="Sales tax", subtotal=f(sub),
    total=f(sub + tx), pay="Cash", cat="Meals", footer="Have a great day!", expect={})

# ---------------------------------------------------------------- html builders
BASE = "body{margin:0;background:#d8d3ca}.p{box-sizing:border-box;margin:24px auto;background:#fff;color:#111}"
def thermal(r):
    rows = ""
    for it in r["items"]:
        d, q, a = it[0], it[1], it[2]
        if r.get("raw_items"): rows += f"<tr><td colspan=2>{d}</td></tr><tr><td></td><td class=r>{m(a)}</td></tr>"
        elif r.get("show_unit") and q != 1: rows += f"<tr><td colspan=2>{d}</td></tr><tr><td>&nbsp;&nbsp;{q} x {m(D(str(a))/D(str(q)))}</td><td class=r>{m(a)}</td></tr>"
        else: rows += f"<tr><td>{d}{'' if q == 1 else ' x' + str(q)}</td><td class=r>{m(a)}</td></tr>"
    ex = "".join(f"<tr><td>{k}</td><td class=r>{v}</td></tr>" for k, v in r.get("lines", []))
    return f"""<style>{BASE}.p{{width:360px;padding:22px 20px 26px;font:15px/1.38 'Courier New',monospace}}h1{{font-size:20px;text-align:center;margin:0 0 4px}}.c{{text-align:center}}table{{width:100%;border-collapse:collapse}}.r{{text-align:right;white-space:nowrap;vertical-align:bottom}}hr{{border:0;border-top:1px dashed #111;margin:9px 0}}.t td{{font-weight:bold;font-size:18px;padding-top:2px}}</style>
<div class=p><h1>{r['vendor']}</h1><div class=c>{r['addr']}<br>{r['tax_id']}</div><hr><div class=c><b>{r['title']}</b></div>
<div>No: {r['inv']}<br>Date: {r['date_txt']}</div><hr><table>{rows}</table><hr><table>{ex}<tr class=t><td>TOTAL {r['cur']}</td><td class=r>{r['sym']}{m(r['total'])}</td></tr></table><hr>
<div>Paid by: {r['pay']}</div><div class=c style="margin-top:10px">{r.get('footer','')}</div><div class=c style="margin-top:8px;letter-spacing:2px">||| |||| || ||||| ||| ||</div></div>"""

def invoice_in(r):
    rows = ""
    for i, (d, q, a, h, rate) in enumerate(r["items"], 1):
        rows += f"<tr><td>{i}</td><td>{d}</td><td>{h}</td><td class=r>{q}</td><td class=r>{rate}</td><td class=r>{m(a)}</td></tr>"
    if "cgst" in r: taxrows = f"<tr><td>CGST @ 9%</td><td class=r>{m(r['cgst'])}</td></tr><tr><td>SGST @ 9%</td><td class=r>{m(r['sgst'])}</td></tr>"
    else: taxrows = f"<tr><td>IGST @ 18%</td><td class=r>{m(r['igst'])}</td></tr>"
    ro = f"<tr><td>Round off</td><td class=r>{'-' if r['ro'] < 0 else ''}{abs(r['ro']):.2f}</td></tr>"
    return f"""<style>{BASE}.p{{width:760px;padding:26px 30px;font:14px/1.4 Arial,sans-serif;border:2px solid #223}}h1{{margin:0;font-size:24px}}.h{{display:flex;justify-content:space-between;border-bottom:2px solid #223;padding-bottom:10px}}table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{border:1px solid #556;padding:6px 8px;text-align:left}}th{{background:#e8ebf2}}.r{{text-align:right}}.s{{width:300px;margin-left:auto}}.s td{{border:0;border-bottom:1px solid #ccd}}.g td{{font-weight:bold;font-size:17px}}</style>
<div class=p><div class=h><div><h1>{r['vendor']}</h1>{r['addr']}<br><b>{r['tax_id']}</b></div><div style="text-align:right"><b style="font-size:20px">{r['title']}</b><br>Invoice No: <b>{r['inv']}</b><br>Date: {r['date_txt']}</div></div>
<p><b>Bill to:</b> {r['buyer']}</p>
<table><tr><th>#</th><th>Description</th><th>HSN</th><th class=r>Qty</th><th class=r>Rate</th><th class=r>Amount</th></tr>{rows}</table>
<table class=s><tr><td>Taxable value</td><td class=r>{m(r['taxable'])}</td></tr>{taxrows}{ro}<tr class=g><td>Grand Total (INR)</td><td class=r>Rs {m(r['total'])}</td></tr></table>
<p>Payment mode: {r['pay']}<br>Amount in words: (as per total) only.</p><p style="text-align:right;margin-top:28px">For {r['vendor']}<br><br>Authorised Signatory</p></div>"""

def saas(r):
    rows = "".join(f"<tr><td>{d}</td><td class=r>{q}</td><td class=r>{sym}{a}</td><td class=r>{sym}{m(am)}</td></tr>" for (d, q, am, a), sym in [(i, '€') for i in r['items']])
    return f"""<style>{BASE}body{{background:#eef0f4}}.p{{width:760px;padding:50px 56px;font:15px/1.5 Georgia,serif;box-shadow:0 1px 6px #0003}}h1{{font:300 42px Georgia,serif;margin:0 0 4px;letter-spacing:1px}}.h{{display:flex;justify-content:space-between}}.pill{{display:inline-block;background:#e3f3e8;color:#1c6b3a;padding:2px 12px;border-radius:12px;font:bold 12px Arial}}table{{width:100%;border-collapse:collapse;margin-top:28px}}th{{text-align:left;font:bold 12px Arial;color:#667;border-bottom:2px solid #223;padding:8px 0}}td{{padding:10px 0;border-bottom:1px solid #dde}}.r{{text-align:right}}.s{{width:300px;margin-left:auto;margin-top:12px}}.s td{{border:0;padding:4px 0}}.g td{{font-weight:bold;font-size:18px;border-top:2px solid #223;padding-top:9px}}</style>
<div class=p><div class=h><div><h1>{r['title']}</h1><span class=pill>PAID</span></div><div style="text-align:right"><b>{r['vendor']}</b><br>{r['addr']}<br>{r['tax_id']}</div></div>
<p style="margin-top:26px">Invoice number: <b>{r['inv']}</b><br>Date of issue: {r['date_txt']}<br>Billed to: Eklavya Demo Studio</p>
<table><tr><th>DESCRIPTION</th><th class=r>QTY</th><th class=r>UNIT PRICE</th><th class=r>AMOUNT</th></tr>{rows}</table>
<table class=s><tr><td>Subtotal</td><td class=r>€{m(r['subtotal'])}</td></tr><tr><td>VAT (Ireland) 23%</td><td class=r>€{m(r['tax'])}</td></tr><tr class=g><td>Amount paid</td><td class=r>€{m(r['total'])}</td></tr></table>
<p style="margin-top:36px;color:#556;font-size:13px">Paid with {r['pay']} on {r['date_txt']}. Thank you for your business.</p></div>"""

def docket(r):
    rows = "".join(f"<tr><td>{d}</td><td class=r>{q}</td><td class=r>{a}</td><td class=r>{m(am)}</td></tr>" for d, q, am, a in r["items"])
    return f"""<style>{BASE}body{{background:#cfcab9}}.p{{width:640px;padding:24px 28px;font:15px/1.35 'Courier New',monospace;background:#f6f3e6;border-left:14px dotted #bdb7a0;border-right:14px dotted #bdb7a0}}h1{{margin:0;font-size:24px;text-transform:uppercase}}table{{width:100%;border-collapse:collapse;margin-top:12px}}th{{text-align:left;border-bottom:2px solid #111}}td{{padding:3px 0}}.r{{text-align:right}}.s{{width:260px;margin-left:auto}}hr{{border:0;border-top:2px solid #111}}</style>
<div class=p><h1>{r['vendor']}</h1>{r['addr']}<br>{r['tax_id']}<hr><b>{r['title']}</b><br>Docket: {r['inv']} &nbsp; Date: {r['date_txt']}<br>Terms: {r['pay']}
<table><tr><th>ITEM</th><th class=r>QTY</th><th class=r>PRICE EX GST</th><th class=r>AMOUNT</th></tr>{rows}</table><hr>
<table class=s><tr><td>Sub total (ex GST)</td><td class=r>{m(r['subtotal'])}</td></tr><tr><td>GST 10%</td><td class=r>{m(r['tax'])}</td></tr><tr><td><b>TOTAL AUD</b></td><td class=r><b>${m(r['total'])}</b></td></tr></table><p>Goods received in good order: ____________</p></div>"""

BUILD = dict(thermal=thermal, invoice_in=invoice_in, saas=saas, docket=docket)

# ---------------------------------------------------------------- render
def render(r):
    html = f"<!doctype html><meta charset=utf-8><body>{BUILD[r['kind']](r)}</body>"
    h = SRC / f"{r['id']}.html"; h.write_text(html, encoding="utf-8")
    png = SRC / f"{r['id']}.png"
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2", "--window-size=900,1500",
                    f"--screenshot={png}", h.as_uri()], check=True, capture_output=True, timeout=90)
    im = Image.open(png).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    box = ImageChops.difference(im, bg).getbbox()
    return im.crop((max(0, box[0] - 30), max(0, box[1] - 30), min(im.width, box[2] + 30), min(im.height, box[3] + 30)))

# ---------------------------------------------------------------- degrade
def desk(size, base=(150, 118, 86)):
    w, h = size; a = np.zeros((h, w, 3), np.float32); a[:] = base
    a += np.random.normal(0, 7, (h, w, 1)); a += np.linspace(-18, 18, w)[None, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def photo(im, angle, pad=140, base=(150, 118, 86), light=0.0):
    W, H = im.size
    canvas = desk((W + 2 * pad, H + 2 * pad), base).convert("RGBA")
    r = im.convert("RGBA").rotate(angle, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    pos = ((canvas.width - r.width) // 2, (canvas.height - r.height) // 2)
    sh = Image.new("RGBA", r.size, (0, 0, 0, 0)); sh.paste((0, 0, 0, 120), mask=r.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(14)); canvas.paste(sh, (pos[0] + 10, pos[1] + 14), sh)
    canvas.paste(r, pos, r)
    out = canvas.convert("RGB")
    if light:
        w, h = out.size; g = np.linspace(1 - light, 1 + light * .3, w)[None, :, None]
        out = Image.fromarray(np.clip(np.asarray(out, np.float32) * g, 0, 255).astype(np.uint8))
    return out

def crumple(im, amp=7, freq=4):
    a = np.asarray(im, np.float32); h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = amp * np.sin(yy / h * math.pi * freq + 1) * np.sin(xx / w * math.pi * 2.3)
    dy = amp * np.sin(xx / w * math.pi * freq * .8) * np.cos(yy / h * math.pi * 1.7)
    sy = np.clip(yy + dy, 0, h - 1).astype(int); sx = np.clip(xx + dx, 0, w - 1).astype(int)
    out = a[sy, sx]
    # fold shading
    shade = 1 + 0.10 * np.sin(yy / h * math.pi * freq * 1.4) + 0.07 * np.sin(xx / w * math.pi * 3.1 + 2)
    out = out * shade[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def noise(im, s=6):
    a = np.asarray(im, np.float32) + np.random.normal(0, s, (im.height, im.width, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def finalize(im, name, max_side=1600):
    s = max_side / max(im.size)
    if s < 1: im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im.save(OUT / f"{name}.jpg", quality=84, optimize=True)

def degrade(id, im):
    if id == "au-cafe": return im                                              # clean
    if id == "in-gst": return photo(im, 1.8, base=(168, 140, 104), light=.10)  # lying on a desk, slightly rotated
    if id == "in-petrol": return noise(photo(im, -2.5, base=(120, 120, 124), light=.12), 5).filter(ImageFilter.GaussianBlur(.8))
    if id == "uk-vat": return im                                               # clean
    if id == "us-store": return ImageEnhance.Contrast(im.filter(ImageFilter.GaussianBlur(1.1))).enhance(.72)
    if id == "taxi": return photo(im, 4.5, base=(60, 62, 70), light=.18)
    if id == "saas": return im                                                 # PDF-style
    if id == "hardware": return noise(photo(im, -3.2, base=(138, 128, 110), light=.15), 4).filter(ImageFilter.GaussianBlur(1.3))
    if id == "mismatch": return im
    if id == "blurry":
        sm = im.resize((im.width // 3, im.height // 3), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3.2))
        return sm.resize(im.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    if id == "in-igst": return photo(noise(crumple(im), 5), -4.5, base=(172, 150, 120), light=.28).filter(ImageFilter.GaussianBlur(.9))
    if id == "faded":
        f2 = ImageEnhance.Brightness(ImageEnhance.Contrast(im).enhance(.36)).enhance(1.32)
        return noise(photo(f2, 2.8, base=(200, 196, 188), light=.06), 7).filter(ImageFilter.GaussianBlur(.9))
    return im

def truth(r):
    t = dict(id=r["id"], vendor=r["vendor"], date=r["date"], invoice_number=r["inv"], currency=r["cur"], subtotal=r.get("subtotal"),
             tax=r["tax"], total=r["total"], payment_method=r["pay"], category=r["cat"], expect=r["expect"],
             items=[dict(description=i[0], qty=float(i[1]), amount=i[2]) for i in r["items"]])
    if "cgst" in r: t["tax_split"] = dict(cgst=r["cgst"], sgst=r["sgst"])
    if "igst" in r: t["tax_split"] = dict(igst=r["igst"])
    if "ro" in r: t["round_off"] = r["ro"]
    return t

if __name__ == "__main__":
    only = sys.argv[1:]
    for id, r in R.items():
        if only and id not in only: continue
        im = degrade(id, render(r)); finalize(im, id)
        (TRUTH / f"{id}.json").write_text(json.dumps(truth(r), indent=1), encoding="utf-8")
        print(id, im.size, (OUT / f"{id}.jpg").stat().st_size // 1024, "KB")
