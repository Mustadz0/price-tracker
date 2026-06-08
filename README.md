<div align="center">

# Price Tracker

**Monitor competitor prices, get alerts on changes. Free & open-source.**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

[English](#english) • [العربية](#arabic) • [Français](#français) • [Español](#español) • [Deutsch](#deutsch) • [Türkçe](#türkçe)

---

<a name="english"></a>
## English

Price Tracker helps small business owners monitor competitor product prices. Add any product URL, and it will track prices over time and alert you when prices change.

### Features
- **Smart Scraping** — extracts prices from any product page using JSON-LD, meta tags, and regex fallbacks
- **Price History** — tracks every price change in SQLite
- **Alerts** — automatic notifications when prices go up or down
- **Web Dashboard** — clean, responsive UI at `http://localhost:8040`
- **CLI** — full command-line interface for automation
- **Free** — no paid APIs, no subscriptions, no tracking

### Quick Start

```bash
pip install -r requirements.txt

# CLI: add a product
python cli.py add "https://example.com/product"

# List all tracked products
python cli.py list

# Check latest prices
python cli.py check --all

# Show price history
python cli.py history 1

# Web dashboard
python webui.py
# Open http://localhost:8040
```

### How It Works

1. Add a product URL via CLI or web dashboard
2. The scraper fetches the page and extracts the price (JSON-LD -> meta tags -> regex)
3. Prices are stored in SQLite with timestamps
4. When you check again, if the price changed — an alert is created
5. View price history and alerts in the dashboard

### Project Structure

```
price-tracker/
├── core/
│   ├── __init__.py
│   ├── database.py      # SQLite models
│   └── scraper.py       # Price extraction engine
├── cli.py               # Command-line interface
├── webui.py             # FastAPI web dashboard
├── samples.txt          # Test URLs
├── requirements.txt
└── README.md
```

---

<a name="arabic"></a>
## العربية

Price Tracker — أداة مجانية لمراقبة أسعار المنافسين. أضف رابط أي منتج وتتبع تغيرات السعر مع تنبيهات فورية.

### المميزات
- استخراج ذكي للأسعار من أي صفحة منتج
- سجل كامل لتغيرات الأسعار
- تنبيهات عند الارتفاع أو الانخفاض
- واجهة ويب على `http://localhost:8040`
- واجهة أوامر كاملة

### البداية السريعة

```bash
pip install -r requirements.txt
python cli.py add "https://example.com/product"
python cli.py list
python cli.py check --all
python webui.py
```

### طريقة العمل
1. أضف رابط المنتج
2. الأداة تستخرج السعر تلقائياً
3. الأسعار تُحفظ مع الوقت
4. تنبيه عند أي تغير في السعر
5. عرض السجل والتنبيهات في لوحة التحكم

---

<a name="français"></a>
## Français

Price Tracker — outil gratuit pour surveiller les prix des concurrents. Ajoutez n'importe quelle URL de produit et suivez l'évolution des prix.

### Fonctionnalités
- Extraction intelligente des prix (JSON-LD, meta tags, regex)
- Historique complet des prix
- Alertes en cas de changement
- Interface web sur `http://localhost:8040`
- Interface en ligne de commande

### Démarrage rapide

```bash
pip install -r requirements.txt
python cli.py add "https://example.com/produit"
python cli.py list
python cli.py check --all
python webui.py
```

---

<a name="español"></a>
## Español

Price Tracker — herramienta gratuita para monitorear precios de la competencia. Añade cualquier URL de producto y rastrea cambios de precio.

### Características
- Extracción inteligente de precios
- Historial completo de precios
- Alertas de cambios
- Dashboard web en `http://localhost:8040`
- Interfaz de línea de comandos

### Inicio rápido

```bash
pip install -r requirements.txt
python cli.py add "https://ejemplo.com/producto"
python cli.py list
python cli.py check --all
python webui.py
```

---

<a name="deutsch"></a>
## Deutsch

Price Tracker — kostenloses Tool zur Überwachung von Konkurrenzpreisen. Fügen Sie jede Produkt-URL hinzu und verfolgen Sie Preisänderungen.

### Funktionen
- Intelligente Preisextraktion
- Vollständiger Preisverlauf
- Benachrichtigungen bei Änderungen
- Web-Dashboard unter `http://localhost:8040`
- Kommandozeilen-Schnittstelle

### Schnellstart

```bash
pip install -r requirements.txt
python cli.py add "https://beispiel.de/produkt"
python cli.py list
python cli.py check --all
python webui.py
```

---

<a name="türkçe"></a>
## Türkçe

Price Tracker — rakip fiyatlarını izlemek için ücretsiz araç. Herhangi bir ürün URL'si ekleyin ve fiyat değişikliklerini takip edin.

### Özellikler
- Akıllı fiyat çıkarma
- Tam fiyat geçmişi
- Değişiklik bildirimleri
- Web paneli `http://localhost:8040`
- Komut satırı arayüzü

### Hızlı Başlangıç

```bash
pip install -r requirements.txt
python cli.py add "https://ornek.com/urun"
python cli.py list
python cli.py check --all
python webui.py
```

---

## License

MIT — free to use, modify, and distribute.

Created by [Mustadz0](https://github.com/Mustadz0)
