#!/usr/bin/env python3
import csv
import io
import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import uvicorn

from core.database import PriceDB
from core.scraper import scrape
from core.notifier import send_telegram

app = FastAPI(title="Competitor Price Tracker")


def _get_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("session")
    if not token:
        return None
    db = PriceDB()
    user = db.get_user_by_token(token)
    if user:
        return {"id": user["id"], "email": user["email"], "name": user["name"]}
    return None


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Price Tracker — Login</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f7fa;color:#1a1a2e;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.1);padding:40px;width:100%;max-width:400px;margin:20px}
.card h1{font-size:1.5rem;margin-bottom:4px}
.card .sub{color:#718096;font-size:.9rem;margin-bottom:24px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:.85rem;color:#4a5568;margin-bottom:4px;font-weight:500}
.form-group input{width:100%;padding:10px 14px;border:2px solid #e2e8f0;border-radius:6px;font-size:.95rem;outline:none;transition:border-color .2s}
.form-group input:focus{border-color:#4299e1}
.btn{width:100%;background:#4299e1;color:#fff;border:none;padding:12px;border-radius:6px;font-size:1rem;cursor:pointer;font-weight:500;transition:background .2s}
.btn:hover{background:#3182ce}
.error{background:#fed7d7;color:#742a2a;padding:10px;border-radius:6px;font-size:.85rem;margin-bottom:16px;display:none}
.switch{text-align:center;margin-top:16px;font-size:.9rem;color:#718096}
.switch a{color:#4299e1;text-decoration:none}
</style>
</head>
<body>
<div class="card">
  <h1>[PRICE] Price Tracker</h1>
  <p class="sub" id="formTitle">Sign in to your account</p>
  <div class="error" id="errorMsg"></div>
  <form id="authForm">
    <input type="hidden" name="mode" id="mode" value="login">
    <div class="form-group">
      <label>Email</label>
      <input type="email" name="email" required>
    </div>
    <div class="form-group">
      <label>Password</label>
      <input type="password" name="password" required>
    </div>
    <button type="submit" class="btn" id="submitBtn">Sign In</button>
  </form>
  <div class="switch">
    <span id="switchText">Don't have an account?</span>
    <a href="#" id="switchLink" onclick="toggleMode();return false">Register</a>
  </div>
</div>
<script>
let isLogin = true;
function toggleMode() {
  isLogin = !isLogin;
  document.getElementById('mode').value = isLogin ? 'login' : 'register';
  document.getElementById('formTitle').textContent = isLogin ? 'Sign in to your account' : 'Create a new account';
  document.getElementById('submitBtn').textContent = isLogin ? 'Sign In' : 'Register';
  document.getElementById('switchText').textContent = isLogin ? "Don't have an account?" : 'Already have an account?';
  document.getElementById('switchLink').textContent = isLogin ? 'Register' : 'Sign In';
}
document.getElementById('authForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const fd = new FormData(this);
  const r = await fetch('/auth', {method:'POST', body: new URLSearchParams(fd), redirect:'follow'});
  if (r.redirected) {
    window.location.href = '/';
  } else {
    const data = await r.json();
    const err = document.getElementById('errorMsg');
    err.textContent = data.error || 'Failed';
    err.style.display = 'block';
  }
});
</script>
</body>
</html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Price Tracker</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f7fa;color:#1a1a2e;min-height:100vh}
  .header{background:#1a1a2e;color:#fff;padding:20px 0}
  .header .container{max-width:1100px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;align-items:center}
  .header h1{font-size:1.6rem}
  .header p{font-size:.9rem;color:#a0aec0}
  .user-info{font-size:.85rem;color:#a0aec0}
  .user-info a{color:#4299e1;text-decoration:none;margin-left:12px}
  .container{max-width:1100px;margin:0 auto;padding:0 20px}
  .nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:12px 0}
  .nav .container{display:flex;gap:20px;align-items:center}
  .nav a{color:#4a5568;text-decoration:none;font-size:.9rem;font-weight:500}
  .nav a:hover,.nav a.active{color:#2b6cb0;border-bottom:2px solid #2b6cb0}
  .nav .right{margin-left:auto;font-size:.8rem}
  .section{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:24px;margin:24px 0}
  .section h2{font-size:1.2rem;margin-bottom:16px;color:#2d3748}
  .form-row{display:flex;gap:12px;flex-wrap:wrap}
  .form-row input[type=url]{flex:1;min-width:200px;padding:10px 14px;border:2px solid #e2e8f0;border-radius:6px;font-size:.95rem;outline:none;transition:border-color .2s}
  .form-row input[type=url]:focus{border-color:#4299e1}
  .btn{background:#4299e1;color:#fff;border:none;padding:10px 24px;border-radius:6px;font-size:.95rem;cursor:pointer;font-weight:500;transition:background .2s}
  .btn:hover{background:#3182ce}
  .btn-sm{font-size:.8rem;padding:6px 12px}
  .btn-danger{background:#e53e3e}
  .btn-danger:hover{background:#c53030}
  table{width:100%;border-collapse:collapse;font-size:.9rem}
  th{text-align:left;padding:10px 8px;border-bottom:2px solid #e2e8f0;color:#718096;font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}
  td{padding:10px 8px;border-bottom:1px solid #e2e8f0}
  tr:hover td{background:#f7fafc}
  .price{font-weight:600;font-size:1.05rem}
  .up{color:#38a169}
  .down{color:#e53e3e}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600}
  .badge-up{background:#c6f6d5;color:#22543d}
  .badge-down{background:#fed7d7;color:#742a2a}
  .empty{text-align:center;padding:40px 20px;color:#a0aec0}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-top:16px}
  .card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;transition:box-shadow .2s}
  .card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
  .card h3{font-size:.95rem;margin-bottom:8px;line-height:1.4}
  .card .price-row{display:flex;justify-content:space-between;align-items:center}
  .card .price{font-size:1.3rem}
  .card .meta{font-size:.75rem;color:#a0aec0;margin-top:8px}
  .flash{background:#c6f6d5;color:#22543d;padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:.9rem;display:none}
  .flash.error{background:#fed7d7;color:#742a2a}
  .inline-flex{display:inline-flex;gap:6px;align-items:center}
  .chart-box{background:#fff;border-radius:8px;padding:16px;margin-top:12px;border:1px solid #e2e8f0}
  .toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
  @media(max-width:600px){.form-row input[type=url]{min-width:100%}.btn{width:100%}}
</style>
</head>
<body>

<div class="header">
  <div class="container">
    <div>
      <h1>[PRICE] Price Tracker</h1>
      <p>Monitor competitor prices and get alerted on changes</p>
    </div>
    <div class="user-info">
      {{USER_EMAIL}}
      <a href="/logout">Logout</a>
    </div>
  </div>
</div>

<div class="nav">
  <div class="container">
    <a href="/" class="active">Dashboard</a>
    <a href="/alerts">Alerts</a>
    <span class="right"><a href="/export/csv" style="color:#718096;text-decoration:none">Export CSV</a></span>
  </div>
</div>

<div class="container">
  <div id="flash" class="flash"></div>

  <div class="section">
    <h2>Add Product</h2>
    <form id="addForm" class="form-row">
      <input type="url" name="url" placeholder="https://example.com/product" required>
      <button type="submit" class="btn">Track Price</button>
    </form>
  </div>

  <div class="section">
    <div class="toolbar">
      <button class="btn btn-sm" onclick="checkAll()">[CHECK ALL]</button>
    </div>
    <h2>Tracked Products</h2>
    <div id="productGrid" class="grid">
      {{PRODUCTS}}
    </div>
  </div>

  <div id="chartSection" class="section" style="display:none">
    <h2>Price History</h2>
    <div class="chart-box">
      <canvas id="priceChart"></canvas>
    </div>
  </div>
</div>

<script>
let priceChart = null;

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

async function checkAll() {
  const btns = document.querySelectorAll('.check-btn');
  btns.forEach(b => { b.disabled = true; b.textContent = '...'; });
  showFlash('Checking all prices...');
  try {
    const r = await fetch('/check-all');
    const data = await r.json();
    showFlash('Checked '+data.checked+' products');
    location.reload();
  } catch(e) {
    showFlash('Check all failed', true);
  } finally {
    btns.forEach(b => { b.disabled = false; b.textContent = '[SYNC]'; });
  }
}

async function showHistory(id) {
  const r = await fetch('/history/'+id);
  const data = await r.json();
  if(!data.length) { showFlash('No history for this product', true); return; }
  const section = document.getElementById('chartSection');
  section.style.display = 'block';
  const labels = data.map(d => d.checked_at.slice(5,16)).reverse();
  const prices = data.map(d => d.price).reverse();
  if(priceChart) priceChart.destroy();
  const ctx = document.getElementById('priceChart').getContext('2d');
  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Price ($)',
        data: prices,
        borderColor: '#4299e1',
        backgroundColor: 'rgba(66,153,225,0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: false, ticks: { callback: v => '$'+v.toFixed(2) } },
        x: { ticks: { maxTicksLimit: 10 } }
      }
    }
  });
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

ALERTS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Price Alerts</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f7fa;color:#1a1a2e}
  .header{background:#1a1a2e;color:#fff;padding:20px 0}
  .header .container{max-width:1000px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;align-items:center}
  .header h1{font-size:1.6rem}
  .container{max-width:1000px;margin:0 auto;padding:0 20px}
  .nav{background:#fff;border-bottom:1px solid #e2e8f0;padding:12px 0}
  .nav .container{display:flex;gap:20px}
  .nav a{color:#4a5568;text-decoration:none;font-size:.9rem;font-weight:500}
  .nav a:hover,.nav a.active{color:#2b6cb0;border-bottom:2px solid #2b6cb0}
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
  .user-info{font-size:.85rem;color:#a0aec0}
  .user-info a{color:#4299e1;text-decoration:none;margin-left:12px}
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>[ALERT] Price Alerts</h1>
    <div class="user-info">{{USER_EMAIL}} <a href="/logout">Logout</a></div>
  </div>
</div>
<div class="nav"><div class="container"><a href="/">Dashboard</a><a href="/alerts" class="active">Alerts</a></div></div>
<div class="container">
  <div class="section">
    <h2>Recent Alerts</h2>
    {{ALERTS}}
  </div>
</div>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_HTML


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login")
    resp.delete_cookie("session")
    return resp


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = PriceDB()
    products = db.get_products(user["id"])
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
                <span class="{change_class}">{change_str}</span>
              </div>
              <div class="meta">
                <span class="inline-flex">
                  <button class="btn btn-sm check-btn" data-id="{p['id']}" onclick="checkPrice({p['id']})">[SYNC]</button>
                  <button class="btn btn-sm" onclick="showHistory({p['id']})">[CHART]</button>
                  <button class="btn btn-sm btn-danger" onclick="deleteProduct({p['id']})">[X]</button>
                </span>
                <span style="float:right">ID #{p['id']}</span>
              </div>
            </div>"""
    return HTMLResponse(
        DASHBOARD_HTML.replace("{{PRODUCTS}}", cards).replace("{{USER_EMAIL}}", user["email"])
    )


@app.get("/alerts", response_class=HTMLResponse)
def alerts_page(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = PriceDB()
    alerts = db.get_alerts(user["id"])
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
    return HTMLResponse(
        ALERTS_HTML.replace("{{ALERTS}}", rows).replace("{{USER_EMAIL}}", user["email"])
    )


@app.post("/auth")
def auth(email: str = Form(...), password: str = Form(...), mode: str = Form("login")):
    db = PriceDB()
    if mode == "register":
        uid = db.register_user(email, password)
        if uid == -1:
            return {"ok": False, "error": "Email already registered"}
        token = db.login_user(email, password)
    else:
        token = db.login_user(email, password)
        if not token:
            return {"ok": False, "error": "Invalid email or password"}
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie(key="session", value=token, max_age=86400 * 30, httponly=True)
    return resp


@app.post("/add")
def add_product(request: Request, url: str = Form(...)):
    user = _get_user(request)
    if not user:
        return {"ok": False, "error": "Not logged in"}
    db = PriceDB()
    result = scrape(url)
    if result:
        pid = db.add_product(url, result["title"], user["id"])
        db.save_price(pid, result["price"])
        return {"ok": True, "id": pid, "name": result["title"][:80], "price": result["price"]}
    pid = db.add_product(url, url, user["id"])
    return {"ok": False, "error": "Could not scrape price, added URL only", "id": pid}


@app.get("/check/{pid}")
def check_price(request: Request, pid: int):
    user = _get_user(request)
    if not user:
        return {"ok": False, "error": "Not logged in"}
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
        send_telegram(f"[PRICE] {p['name'][:60]}\n{msg}")
    return {"ok": True, "price": result["price"], "title": result["title"][:80]}


@app.get("/check-all")
def check_all(request: Request):
    user = _get_user(request)
    if not user:
        return {"ok": False, "error": "Not logged in"}
    db = PriceDB()
    products = db.get_products(user["id"])
    count = 0
    for p in products:
        result = scrape(p["url"])
        if not result:
            continue
        old_price = db.get_latest_price(p["id"])
        db.save_price(p["id"], result["price"])
        if old_price and old_price != result["price"]:
            change = ((result["price"] - old_price) / old_price) * 100
            msg = f"Price changed: ${old_price:.2f} -> ${result['price']:.2f} ({change:+.1f}%)"
            db.record_alert(p["id"], old_price, result["price"], change, msg)
            send_telegram(f"[PRICE] {p['name'][:60]}\n{msg}")
        count += 1
    return {"ok": True, "checked": count}


@app.get("/history/{pid}")
def price_history(request: Request, pid: int):
    user = _get_user(request)
    if not user:
        return []
    db = PriceDB()
    history = db.get_price_history(pid)
    return [{"checked_at": h["checked_at"], "price": h["price"]} for h in history]


@app.get("/export/csv")
def export_csv(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/login")
    db = PriceDB()
    products = db.get_products(user["id"])
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Product", "URL", "Latest Price", "Previous Price", "Change %", "Last Checked"])
    for p in products:
        latest = db.get_latest_price(p["id"])
        prev = db.get_previous_price(p["id"])
        change = ""
        if latest and prev and prev != 0:
            change = f"{((latest - prev) / prev) * 100:+.1f}%"
        history = db.get_price_history(p["id"], limit=1)
        last_checked = history[0]["checked_at"] if history else ""
        w.writerow([p["id"], p["name"], p["url"],
                     f"${latest:.2f}" if latest else "",
                     f"${prev:.2f}" if prev else "",
                     change, last_checked])
    return Response(
        content="\ufeff" + out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=price_tracker_export.csv"},
    )


@app.post("/delete/{pid}")
def delete_product(request: Request, pid: int):
    user = _get_user(request)
    if not user:
        return {"ok": False}
    db = PriceDB()
    db.delete_product(pid)
    return {"ok": True}


def _auto_check_loop():
    while True:
        try:
            db = PriceDB()
            products = db.conn.execute(
                "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC"
            ).fetchall()
            for p in products:
                result = scrape(p["url"])
                if not result:
                    continue
                old_price = db.get_latest_price(p["id"])
                db.save_price(p["id"], result["price"])
                if old_price and old_price != result["price"]:
                    change = ((result["price"] - old_price) / old_price) * 100
                    msg = f"Price changed: ${old_price:.2f} -> ${result['price']:.2f} ({change:+.1f}%)"
                    db.record_alert(p["id"], old_price, result["price"], change, msg)
                    send_telegram(f"[PRICE] {p['name'][:60]}\n{msg}")
        except Exception:
            pass
        time.sleep(3600)


@app.on_event("startup")
def start_scheduler():
    t = threading.Thread(target=_auto_check_loop, daemon=True)
    t.start()


def main():
    port = int(os.getenv("PORT", "8040"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
