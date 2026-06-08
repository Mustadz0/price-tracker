#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn

from core.database import PriceDB
from core.scraper import scrape

app = FastAPI(title="Competitor Price Tracker")

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Price Tracker</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f7fa;color:#1a1a2e;min-height:100vh}
  .header{background:#1a1a2e;color:#fff;padding:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.15)}
  .header h1{font-size:1.6rem;margin-bottom:4px}
  .header p{font-size:.9rem;color:#a0aec0}
  .container{max-width:1000px;margin:0 auto;padding:0 20px}
  .nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:12px 0}
  .nav a{color:#4a5568;text-decoration:none;margin-right:20px;font-size:.9rem;font-weight:500}
  .nav a:hover{color:#2b6cb0}
  .nav a.active{color:#2b6cb0;border-bottom:2px solid #2b6cb0}
  .section{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:24px;margin:24px 0}
  .section h2{font-size:1.2rem;margin-bottom:16px;color:#2d3748}
  .form-row{display:flex;gap:12px;flex-wrap:wrap}
  .form-row input[type=url]{flex:1;min-width:200px;padding:10px 14px;border:2px solid #e2e8f0;border-radius:6px;font-size:.95rem;outline:none;transition:border-color .2s}
  .form-row input[type=url]:focus{border-color:#4299e1}
  .btn{background:#4299e1;color:#fff;border:none;padding:10px 24px;border-radius:6px;font-size:.95rem;cursor:pointer;font-weight:500;transition:background .2s}
  .btn:hover{background:#3182ce}
  .btn-sm{font-size:.8rem;padding:4px 12px}
  .btn-danger{background:#e53e3e}
  .btn-danger:hover{background:#c53030}
  .btn-outline{background:transparent;color:#4299e1;border:2px solid #4299e1}
  .btn-outline:hover{background:#ebf8ff}
  table{width:100%;border-collapse:collapse;font-size:.9rem}
  th{text-align:left;padding:10px 8px;border-bottom:2px solid #e2e8f0;color:#718096;font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}
  td{padding:10px 8px;border-bottom:1px solid #e2e8f0}
  tr:hover td{background:#f7fafc}
  .price{font-weight:600;font-size:1.05rem}
  .up{color:#38a169}
  .down{color:#e53e3e}
  .change{font-size:.8rem}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600}
  .badge-up{background:#c6f6d5;color:#22543d}
  .badge-down{background:#fed7d7;color:#742a2a}
  .empty{text-align:center;padding:40px 20px;color:#a0aec0}
  .empty p{font-size:1.1rem;margin-bottom:8px}
  .empty .sub{font-size:.9rem}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-top:16px}
  .card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;transition:box-shadow .2s}
  .card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
  .card h3{font-size:.95rem;margin-bottom:8px;line-height:1.4}
  .card .price-row{display:flex;justify-content:space-between;align-items:center}
  .card .price{font-size:1.3rem}
  .card .meta{font-size:.75rem;color:#a0aec0;margin-top:8px}
  .flash{background:#c6f6d5;color:#22543d;padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:.9rem;display:none}
  .flash.error{background:#fed7d7;color:#742a2a}
  .loading{text-align:center;padding:12px;color:#718096}
  .inline-flex{display:inline-flex;gap:6px;align-items:center}
  @media(max-width:600px){.form-row input[type=url]{min-width:100%}.btn{width:100%}}
</style>
</head>
<body>

<div class="header">
  <div class="container">
    <h1>[PRICE] Competitor Price Tracker</h1>
    <p>Monitor competitor prices and get alerted on changes</p>
  </div>
</div>

<div class="nav">
  <div class="container">
    <a href="/" class="active">Dashboard</a>
    <a href="/alerts">Alerts</a>
  </div>
</div>

<div class="container">
  <div id="flash" class="flash"></div>

  <div class="section">
    <h2>Add Product</h2>
    <form id="addForm" class="form-row" action="/add" method="POST">
      <input type="url" name="url" placeholder="https://example.com/product" required>
      <button type="submit" class="btn">Track Price</button>
    </form>
  </div>

  <div class="section">
    <h2>Tracked Products</h2>
    <div id="productGrid" class="grid">
      {{PRODUCTS}}
    </div>
  </div>
</div>

<script>
document.getElementById('addForm')?.addEventListener('submit', async function(e){
  e.preventDefault();
  const url = this.querySelector('[name=url]').value;
  const btn = this.querySelector('button');
  btn.disabled = true; btn.textContent = 'Adding...';
  try {
    const r = await fetch('/add', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'url='+encodeURIComponent(url)});
    const data = await r.json();
    if(data.ok) {
      showFlash('Product added: '+data.name);
      this.querySelector('[name=url]').value = '';
      location.reload();
    } else {
      showFlash(data.error||'Failed', true);
    }
  } catch(e) {
    showFlash('Network error', true);
  } finally {
    btn.disabled = false; btn.textContent = 'Track Price';
  }
});

async function checkPrice(id) {
  const btn = document.querySelector(`.check-btn[data-id="${id}"]`);
  if(btn) { btn.disabled = true; btn.textContent = '...'; }
  try {
    const r = await fetch('/check/'+id);
    const data = await r.json();
    if(data.ok) {
      showFlash('Price: $'+data.price.toFixed(2));
      setTimeout(()=>location.reload(), 800);
    } else {
      showFlash(data.error||'Check failed', true);
    }
  } catch(e) {
    showFlash('Check failed', true);
  } finally {
    if(btn) { btn.disabled = false; btn.textContent = '[SYNC]'; }
  }
}

async function deleteProduct(id) {
  if(!confirm('Remove this product?')) return;
  await fetch('/delete/'+id, {method:'POST'});
  location.reload();
}

function showFlash(msg, error) {
  const f = document.getElementById('flash');
  f.textContent = msg;
  f.className = 'flash'+(error?' error':'');
  f.style.display = 'block';
  setTimeout(()=>{f.style.display='none'}, 4000);
}
</script>
</body>
</html>"""

ALERTS_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Price Alerts</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f7fa;color:#1a1a2e}
  .header{background:#1a1a2e;color:#fff;padding:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.15)}
  .header h1{font-size:1.6rem;margin-bottom:4px}
  .header p{font-size:.9rem;color:#a0aec0}
  .container{max-width:1000px;margin:0 auto;padding:0 20px}
  .nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:12px 0}
  .nav a{color:#4a5568;text-decoration:none;margin-right:20px;font-size:.9rem;font-weight:500}
  .nav a:hover{color:#2b6cb0}
  .nav a.active{color:#2b6cb0;border-bottom:2px solid #2b6cb0}
  .section{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:24px;margin:24px 0}
  .section h2{font-size:1.2rem;margin-bottom:16px;color:#2d3748}
  table{width:100%;border-collapse:collapse;font-size:.9rem}
  th{text-align:left;padding:10px 8px;border-bottom:2px solid #e2e8f0;color:#718096;font-weight:600;font-size:.8rem;text-transform:uppercase}
  td{padding:10px 8px;border-bottom:1px solid #e2e8f0}
  tr:hover td{background:#f7fafc}
  .up{color:#38a169}
  .down{color:#e53e3e}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600}
  .badge-up{background:#c6f6d5;color:#22543d}
  .badge-down{background:#fed7d7;color:#742a2a}
  .empty{text-align:center;padding:40px;color:#a0aec0}
  .back{display:inline-block;margin-bottom:16px;color:#4299e1;text-decoration:none;font-size:.9rem}
  .back:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="header"><div class="container"><h1>[ALERT] Price Alerts</h1></div></div>
<div class="nav"><div class="container"><a href="/">Dashboard</a><a href="/alerts" class="active">Alerts</a></div></div>
<div class="container">
  <div class="section">
    <h2>Recent Alerts</h2>
    {{ALERTS}}
  </div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    db = PriceDB()
    products = db.get_products()
    cards = ""
    if not products:
        cards = '<div class="empty"><p>No products tracked yet</p><p class="sub">Add a product URL above to start monitoring prices</p></div>'
    else:
        for p in products:
            latest = db.get_latest_price(p["id"])
            prev = db.get_previous_price(p["id"])
            change_str = ""
            change_class = ""
            if latest and prev and prev != 0:
                pct = ((latest - prev) / prev) * 100
                change_str = f"{pct:+.1f}%"
                change_class = "up" if pct > 0 else "down"
            price_str = f"${latest:.2f}" if latest else "?"
            cards += f"""<div class="card">
              <h3><a href="{p['url']}" target="_blank" style="color:#2d3748;text-decoration:none">{p['name'][:80]}</a></h3>
              <div class="price-row">
                <span class="price">{price_str}</span>
                <span class="change {change_class}">{change_str}</span>
              </div>
              <div class="meta">
                <span class="inline-flex">
                  <button class="btn btn-sm check-btn" data-id="{p['id']}" onclick="checkPrice({p['id']})">[SYNC]</button>
                  <button class="btn btn-sm btn-danger" onclick="deleteProduct({p['id']})">[X]</button>
                </span>
                <span style="float:right">ID #{p['id']}</span>
              </div>
            </div>"""
    html = HTML_TEMPLATE.replace("{{PRODUCTS}}", cards)
    return HTMLResponse(content=html)


@app.get("/alerts", response_class=HTMLResponse)
def alerts_page():
    db = PriceDB()
    alerts = db.get_alerts()
    rows = ""
    if not alerts:
        rows = '<div class="empty"><p>No price alerts yet</p></div>'
    else:
        rows = '<table><tr><th>Date</th><th>Product</th><th>Old</th><th>New</th><th>Change</th></tr>'
        for a in alerts:
            cls = "badge badge-up" if (a["change_pct"] or 0) > 0 else "badge badge-down"
            arrow = "[UP]" if (a["change_pct"] or 0) > 0 else "[DOWN]"
            rows += f"""<tr>
              <td>{a['created_at'][:19]}</td>
              <td><a href="{a['url']}" target="_blank">{a['product_name'][:50]}</a></td>
              <td>${a['old_price']:.2f}</td>
              <td>${a['new_price']:.2f}</td>
              <td><span class="{cls}">{arrow} {a['change_pct']:+.1f}%</span></td>
            </tr>"""
        rows += "</table>"
    html = ALERTS_TEMPLATE.replace("{{ALERTS}}", rows)
    return HTMLResponse(content=html)


@app.post("/add")
def add_product(url: str = Form(...)):
    db = PriceDB()
    result = scrape(url)
    if result:
        pid = db.add_product(url, result["title"])
        db.save_price(pid, result["price"])
        return {"ok": True, "id": pid, "name": result["title"][:80], "price": result["price"]}
    pid = db.add_product(url, url)
    return {"ok": False, "error": "Could not scrape price, added URL only", "id": pid}


@app.get("/check/{pid}")
def check_price(pid: int):
    db = PriceDB()
    p = db.get_product(pid)
    if not p:
        return {"ok": False, "error": "Product not found"}
    result = scrape(p["url"])
    if not result:
        return {"ok": False, "error": "Failed to fetch page"}
    old_price = db.get_latest_price(pid)
    db.save_price(pid, result["price"])
    if old_price and old_price != result["price"]:
        change = ((result["price"] - old_price) / old_price) * 100
        msg = f"Price changed: ${old_price:.2f} -> ${result['price']:.2f} ({change:+.1f}%)"
        db.record_alert(pid, old_price, result["price"], change, msg)
    return {"ok": True, "price": result["price"], "title": result["title"][:80]}


@app.post("/delete/{pid}")
def delete_product(pid: int):
    db = PriceDB()
    db.delete_product(pid)
    return {"ok": True}


def main():
    port = int(os.getenv("PORT", "8040"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
