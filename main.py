#!/usr/bin/env python3
"""
pivot_analysis.py
Napi pivot-szintek statisztikai elemzése 1-perces OHLC adatokból.

Főbb funkciók
1. Napi pivot- (S3…R3) és mid-szintek (M1…M6) számítása a tegnapi H-L-C alapján
2. Minden kereskedési napon megkeresi:
   • melyik szintet érintette először az árfolyam,
   • elérte-e még ugyanazon a napon a közvetlen felső / alsó szomszédszintet
3. Összesített százalékos eredményeket ír ki.

Használat:
    python pivot_analysis.py --csv AUDCAD_1m.tsv --sep "\t" --tz Europe/Budapest
"""

import argparse
from collections import defaultdict
import pandas as pd
import pytz
import sys
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────────
#  Pivot- és mid-szintek képletei
# ────────────────────────────────────────────────────────────────────────────────
def daily_pivots(row):
    """Floor-formula napi pivotok + mid-szintek egy sor (H, L, C) alapján."""
    H, L, C = row["High"], row["Low"], row["Close"]
    pp = (H + L + C) / 3
    piv = {
        "S3": L - 2 * (H - pp),
        "S2": pp - (H - L),
        "S1": 2 * pp - H,
        "PP": pp,
        "R1": 2 * pp - L,
        "R2": pp + (H - L),
        "R3": H + 2 * (pp - L),
    }
    # mid-szintek új elnevezéssel
    piv["mid_S2-S3"] = (piv["S3"] + piv["S2"]) / 2
    piv["mid_S1-S2"] = (piv["S2"] + piv["S1"]) / 2
    piv["mid_PP-S1"] = (piv["S1"] + piv["PP"]) / 2
    piv["mid_R1-PP"] = (piv["PP"] + piv["R1"]) / 2
    piv["mid_R2-R1"] = (piv["R1"] + piv["R2"]) / 2
    piv["mid_R3-R2"] = (piv["R2"] + piv["R3"]) / 2
    return piv


# ────────────────────────────────────────────────────────────────────────────────
#  Adatbeolvasás – rugalmas szeparátor + fejléc felismerés
# ────────────────────────────────────────────────────────────────────────────────
def read_ohlc(path, sep, colmap):
    """
    Betölti a CSV/TSV-t:
    • automatikusan eldönti, van-e fejléc,
    • ha nincs fejléc, generál egyet (Time Open High Low Close Volume Extra…),
    majd átnevezi a felhasználó által megadott oszlopnevekre.
    """
    # 1) Első sor elemzése – hány oszlop?
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline().rstrip("\n")
        second_line = f.readline().rstrip("\n")
    
    first_fields = first_line.split(sep)
    second_fields = second_line.split(sep)
    n_cols = len(first_fields)

    # alapfejléc (MetaTrader formátum)
    base_cols = ["Time", "Open", "High", "Low", "Close", "Volume"]

    # Ellenőrizzük, hogy az első sor fejléc-e (nem numerikus értékeket tartalmaz)
    try:
        # Ha az első sor második eleme (Open) számmá konvertálható, akkor nincs fejléc
        float(first_fields[1])
        has_header = False
    except (ValueError, IndexError):
        # Ha nem konvertálható, akkor van fejléc
        has_header = True

    if has_header:
        # Van fejléc; pandas automatikusan felismeri
        header_opt, names_opt = "infer", None
    else:
        # Nincs fejléc – kreálunk egyet
        extra = n_cols - len(base_cols)
        names_opt = base_cols + [f"Extra{i+1}" for i in range(extra)]
        header_opt = None

    try:
        df = pd.read_csv(
            path,
            sep=sep,
            names=names_opt,
            header=header_opt,
            engine="python",
            index_col=False,  # Ne használj semmilyen oszlopot indexként
        )
        
        # Ha van extra oszlop amit nem használunk, hagyjuk figyelmen kívül
        if len(df.columns) > 6:
            df = df.iloc[:, :6]  # Csak az első 6 oszlopot tartsuk meg
            
        # Ha van header, de az oszlopok neve üres, akkor adjunk nekik nevet
        if header_opt == "infer" and len(df.columns) > 0:
            expected_cols = ["Time", "Open", "High", "Low", "Close", "Volume"]
            if len(df.columns) == len(expected_cols):
                df.columns = expected_cols
    except Exception as e:
        sys.exit(f"HIBA a fájl olvasásakor: {e}")

    # Kolumnák átnevezése a felhasználó által megadott mapping szerint
    df.rename(columns=colmap, inplace=True)

    # Kötelező oszlopok ellenőrzése
    required = {"Datetime", "Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"Hiányzó kötelező oszlop(ok): {', '.join(missing)}")

    # Időbélyeg átalakítása
    try:
        df["Datetime"] = pd.to_datetime(df["Datetime"], format="%Y-%m-%d %H:%M:%S")
    except Exception as e:
        try:
            # Ha a format nem működik, próbáljuk meg automatikus felismeréssel
            df["Datetime"] = pd.to_datetime(df["Datetime"])
        except Exception as e2:
            sys.exit(f"Datetime konverziós hiba: {e2}")

    return df


# ────────────────────────────────────────────────────────────────────────────────
#  Egy napi időszelet elemzése
# ────────────────────────────────────────────────────────────────────────────────
def analyse_day(df_day, pivots):
    """Visszatér: lista a mai napon először érintett szintekről és irányaikról."""
    levels = sorted(pivots.items(), key=lambda x: x[1])  # ár szerint
    names = [n for n, _ in levels]
    prices = [p for _, p in levels]
    
    touched_today = set()  # Ma már érintett szintek
    results = []  # Eredmények listája

    for ts, bar in df_day.iterrows():
        lo, hi = bar["Low"], bar["High"]
        
        # Nézzük meg, mely szinteket érinti ez a bar
        for i, price in enumerate(prices):
            if lo <= price <= hi and names[i] not in touched_today:
                # Ez a szint ma először érintődik
                touched_today.add(names[i])
                
                # Határozzuk meg a szomszédszinteket
                lower_idx = i - 1 if i > 0 else None
                upper_idx = i + 1 if i < len(names) - 1 else None
                
                # Keressük meg, hogy a mai nap folyamán eléri-e a szomszédszinteket
                reached_lower = reached_upper = False
                first_direction = None
                
                # Végignézzük a mai nap hátralévő részét
                for future_ts, future_bar in df_day.loc[ts:].iterrows():
                    future_lo, future_hi = future_bar["Low"], future_bar["High"]
                    
                    if lower_idx is not None and not reached_lower:
                        if future_lo <= prices[lower_idx] <= future_hi:
                            reached_lower = True
                            if first_direction is None:
                                first_direction = 'lower'
                    
                    if upper_idx is not None and not reached_upper:
                        if future_lo <= prices[upper_idx] <= future_hi:
                            reached_upper = True
                            if first_direction is None:
                                first_direction = 'upper'
                    
                    if ((lower_idx is None or reached_lower) and 
                        (upper_idx is None or reached_upper)):
                        break
                
                results.append({
                    "first": names[i],
                    "first_direction": first_direction,
                })
    
    return results


# ────────────────────────────────────────────────────────────────────────────────
#  Főprogram
# ────────────────────────────────────────────────────────────────────────────────
def main(args):
    # --------------- fájl & oszlopnevek ellenőrzése ---------------------------
    infile = Path(args.csv)
    if not infile.is_file():
        sys.exit(f"Nem létezik a megadott állomány: {infile}")

    colmap = {
        args.datetime: "Datetime",
        args.open: "Open",
        args.high: "High",
        args.low: "Low",
        args.close: "Close",
    }

    # ------------------- adat betöltése --------------------------------------
    # Separator feldolgozása - ha \t stringet kaptunk, cseréljük le tab karakterre
    if args.sep == "\\t":
        sep = "\t"
    else:
        sep = args.sep
    
    df = read_ohlc(infile, sep, colmap)

    # ------------------- időzóna kezelése ------------------------------------
    tz = pytz.timezone(args.tz)
    
    # Ha az időbélyegek nem tartalmaznak timezone infót, először UTC-ként kezeljük őket
    if df["Datetime"].dt.tz is None:
        df["Datetime"] = df["Datetime"].dt.tz_localize('UTC')
    
    df["Datetime"] = df["Datetime"].dt.tz_convert(tz)
    df.set_index("Datetime", inplace=True)
    df.sort_index(inplace=True)

    # ------------------- napi OHLC resample ----------------------------------
    daily = df.resample("1D")

    stats = defaultdict(lambda: {"count": 0, "first_lower": 0, "first_upper": 0})
    processed_days = 0
    valid_days = 0

    for day, group in daily:
        processed_days += 1
        if group.empty:
            continue
        
        # Tegnapi utolsó gyertya (előző nap OHLC) → pivotok
        prev_day = group.iloc[0].name.normalize() - pd.Timedelta(days=1)
        try:
            # Előző nap összes adata
            prev_day_data = df[df.index.date == prev_day.date()]
            if len(prev_day_data) == 0:
                continue
                
            prev_high = prev_day_data["High"].max()
            prev_low = prev_day_data["Low"].min()
            prev_close = prev_day_data["Close"].iloc[-1]
            piv = daily_pivots(
                pd.Series({"High": prev_high, "Low": prev_low, "Close": prev_close})
            )
        except Exception as e:
            continue

        res = analyse_day(group, piv)
        if not res:  # Ha üres lista
            continue
            
        # Most res egy lista, minden elemét feldolgozzuk
        for result in res:
            valid_days += 1  # Minden érintett szint egy "esemény"
            f = result["first"]
            stats[f]["count"] += 1
            
            # Első irány statisztika
            if result["first_direction"] == 'lower':
                stats[f]["first_lower"] += 1
            elif result["first_direction"] == 'upper':
                stats[f]["first_upper"] += 1

    # -------------------- eredmények kiírása + vizualizációk ---------------------------------
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import MaxNLocator
    from matplotlib.table import Table

    print("\nELSŐ IRÁNY (melyik szomszédot érte el először):")
    header = f"{'Pivot':<5} {'Mintaszám':>10} {'Le első%':>12} {'Fel első%':>12} {'Össz%':>8}"
    print(header)
    print("-" * len(header))
    ordered_lvls = [
        "S3", "mid_S2-S3", "S2", "mid_S1-S2", "S1", "mid_PP-S1",
        "PP", "mid_R1-PP", "R1", "mid_R2-R1", "R2", "mid_R3-R2", "R3"
    ]
    table_data = []
    for lvl in ordered_lvls:
        c = stats[lvl]["count"]
        if c == 0:
            continue
        first_lower_pct = stats[lvl]["first_lower"] / c * 100 if stats[lvl]["first_lower"] else 0
        first_upper_pct = stats[lvl]["first_upper"] / c * 100 if stats[lvl]["first_upper"] else 0
        total_pct = first_lower_pct + first_upper_pct
        print(f"{lvl:<5} {c:>10} {first_lower_pct:>11.1f}% {first_upper_pct:>11.1f}% {total_pct:>7.1f}%")
        table_data.append({
            "Pivot": lvl,
            "Mintaszám": c,
            "Le első%": first_lower_pct,
            "Fel első%": first_upper_pct,
            "Össz%": total_pct
        })

    # --- DataFrame a táblázathoz ---
    df_table = pd.DataFrame(table_data)

    # --- Táblázat mentése PNG-be ---
    fig, ax = plt.subplots(figsize=(10, 0.5 + 0.4 * len(df_table)))
    ax.axis('off')
    tbl = ax.table(
        cellText=df_table.values,
        colLabels=df_table.columns,
        cellLoc='center',
        loc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1.2, 1.2)
    # Oszlopszélességek állítása: az utolsó 3 oszlop legyen szélesebb
    col_widths = [0.12, 0.16, 0.24, 0.24, 0.24]  # arányok: Pivot, Mintaszám, Le első%, Fel első%, Össz%
    for i, width in enumerate(col_widths):
        for j in range(len(df_table) + 1):  # +1 a fejléc miatt
            tbl[(j, i)].set_width(width)
    plt.tight_layout()
    plt.savefig("elso_irany_table.png", bbox_inches='tight', dpi=200)
    plt.close(fig)

    # --- Bar chart: Le első% és Fel első% ---
    x = np.arange(len(df_table))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    rects1 = ax.bar(x - width/2, df_table["Le első%"], width, label='Le első%')
    rects2 = ax.bar(x + width/2, df_table["Fel első%"], width, label='Fel első%')
    ax.set_ylabel('Százalék (%)')
    ax.set_title('Első irány szomszéd elérésének aránya pivot szinteken')
    ax.set_xticks(x)
    ax.set_xticklabels(df_table["Pivot"])
    ax.legend()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig("elso_irany_barchart.png", bbox_inches='tight', dpi=200)
    plt.close(fig)

    # Pie chart generálás törölve a felhasználó kérésére


# ────────────────────────────────────────────────────────────────────────────────
#  CLI argumentumok
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pivot-szintek statisztikai elemzése 1M OHLC adatokból"
    )
    parser.add_argument("--csv", required=True, help="Bemeneti TSV/CSV fájl")
    parser.add_argument("--sep", default="\t",
                        help="Mezőelválasztó (pl. '\\t', ',', ';'). Alap: tab")
    parser.add_argument("--datetime", default="Time",
                        help="Időbélyeg oszlop neve (alap: Time)")
    parser.add_argument("--open", default="Open", help="Open oszlop neve")
    parser.add_argument("--high", default="High", help="High oszlop neve")
    parser.add_argument("--low", default="Low", help="Low oszlop neve")
    parser.add_argument("--close", default="Close", help="Close oszlop neve")
    parser.add_argument("--tz", default="UTC",
                        help="Cél időzóna a napi határokhoz (pl. Europe/Budapest)")
    args = parser.parse_args()
    main(args)
