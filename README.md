# 📈 Pivot Szint Érintés Elemző – MetaTrader 5 alapú backteszt

Ez a Python-szkript **pivot szintek érintését és azok utáni árfolyammozgásokat** elemzi a MetaTrader 5 (MT5) platformról letöltött tick-adatok alapján. Az elemzés célja, hogy statisztikát nyújtson arról, melyik pivot szint érintése után milyen ármozgások történnek.

---

## 🧠 Működés

1. A szkript minden napra kiszámítja a klasszikus **pivot szinteket**:
   - R3, R2, R1, Pivot, S1, S2, S3
   - Valamint köztes szinteket is (pl. R1.5, S0.5 stb.)
2. Tick alapon elemzi, **melyik szintet érintette meg először az árfolyam** az adott napon.
3. Megvizsgálja, hogy az **első érintett szint után** felfelé vagy lefelé haladva melyik szomszédos szintet érte el előbb.
4. Az eredmények alapján megállapítja, hogy az ár az érintés után felfelé vagy lefelé mozgott-e hamarabb.
5. Az eredményeket a konzolra írja, és (opcionálisan) minden napról ment egy grafikont az adott instrumentum mappájába.

---

## ⚙️ Beállítások – config.json

A konfigurációs fájl így néz ki:

{
  "SYMBOLS": ["EURUSD", "GBPUSD"],
  "TIMEFRAME": "M1",
  "DATE_FROM": "2024-01-01",
  "DATE_TO": "2024-01-31",
  "TOLERANCE": {
    "EURUSD": 0.0002,
    "GBPUSD": 0.0003
  },
  "SAVE_DAILY_CHARTS": true
}

Paraméterek leírása:

- SYMBOLS: A vizsgálni kívánt instrumentum(ok) listája.
- TIMEFRAME: Az elemzéshez használt időkeret (pl. M1, M5, stb.)
- DATE_FROM, DATE_TO: Az elemzendő időszak kezdete és vége.
- TOLERANCE: Pontossági érték szintérintés meghatározásához (instrumentumonként).
- SAVE_DAILY_CHARTS: Ha true, akkor minden napról mentésre kerül egy grafikon (.png).

---

## 📦 Követelmények

- Python 3.7+
- Telepített MetaTrader 5 terminál
- Telepített következő Python csomagok:

pip install MetaTrader5 pandas matplotlib

---

## ▶️ Használat

1. Töltsd le vagy klónozd a projektet.
2. Módosítsd a config.json fájlt igény szerint.
3. Futtasd a pivot_analysis.py szkriptet:

python pivot_analysis.py

---

## 📊 Kimenet

Konzolra:

- Melyik szintet érintette meg először az ár az adott napon.
- Az ezt követő mozgás iránya és a következő szint.
- Siker vagy kudarc (vagy egyik szint sem lett elérve).
- Nap végi statisztika: sikerarány, semleges napok száma stb.

Fájlban:

- Opcionálisan mentésre kerülnek a napi grafikonok a ./{SYMBOL}/chart_{SYMBOL}_{YYYY-MM-DD}.png útvonalra.
- A fájlok külön mappában vannak instrumentumonként.

---

## 🧪 Kódfelépítés

pivot/
│
├── pivot_analysis.py      # A fő elemző szkript
├── config.json            # Konfigurációs fájl
├── EURUSD/                # Mentett napi grafikonok az EURUSD-re
│   └── chart_EURUSD_2024-01-02.png
├── GBPUSD/                # Mentett napi grafikonok a GBPUSD-re
│   └── chart_GBPUSD_2024-01-02.png
└── README.md              # Ez a dokumentáció

---

## 📌 Fontos tudnivalók

- A MetaTrader terminálnak futnia kell, és be kell jelentkezni, különben az adatok nem lesznek elérhetők.
- Tick adatok lekérdezése több instrumentumra és hosszabb időszakra időigényes lehet.
- A TOLERANCE érték kritikus fontosságú – ha túl alacsony, akkor lehet, hogy nem érzékeli az érintéseket.

---

## 🚀 Jövőbeli fejlesztések (ötletek)

- CSV export a naplózott eredményekből.
- GUI beépítése konfigurációhoz.
- Többféle pivot számítás (Fibonacci, Woodie stb.).
- Machine learning modellek tanítása az adatokból.

---

## 📮 Kapcsolat

Ha kérdésed van, hibát találtál vagy javaslatod van, nyiss egy issue-t vagy írj üzenetet.

---

Készült: Python + MetaTrader5 + Pivot elmélet alapján.  
📅 Készült: 2025  
👨‍💻 Fejlesztő: Króner

---

Ez a projekt oktatási célokra készült. Használata saját felelősségre történik.
