#!/usr/bin/env python3
"""Daily Screener — Overextended | Short Interest | Squeeze Radar. Author: Hermes Agent"""
import os, warnings, json
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
warnings.filterwarnings("ignore")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
CACHED_UNIVERSE = os.path.join(os.path.dirname(__file__), "stock_universe.csv")
TMPL_PATH = os.path.join(os.path.dirname(__file__), "template.html")
INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

EXPANDED_UNIVERSE = [
    # S&P 500 / LARGE CAP
    "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","TSLA","AVGO","BRK-B","JPM","LLY","V","UNH","XOM","MA","HD","PG","COST","JNJ",
    "WMT","MRK","ABBV","NFLX","BAC","CRM","AMD","PEP","TMO","ADBE","LIN","TXN","ACN","CMCSA","DHR","QCOM","NKE","AMGN","CAT","SPGI",
    "HON","UNP","LOW","IBM","BA","RTX","GE","DE","CVX","SCHW","BMY","SBUX","MMM","F","GM","INTC","CSCO","VZ","T","DIS","PFE","ABT","WFC",
    "VRTX","REGN","ISRG","LRCX","KLAC","SNOW","PLTR","UBER","COIN","ROKU","SQ","SHOP","DDOG","ZM","MRNA","CRWD","PANW","ANET","MRVL","FTNT","ZS",
    "OKTA","SPLK","NOW","WDAY","TEAM","DOCU","TWLO","FSLY","NET","U","MDB","ESTC","S","CFLT","GTLB","RBLX","DUOL","BILL","HOOD","SOFI",
    "LCID","RIVN","RKLB","ASTS","VST","CELH","SMCI","SMH","ARKK","IWM","QQQ","SPY",
    # DOW 30
    "AXP","GS","KO","MCD","SHW","TRV","WBA",
    # POPULAR MID-CAP / EMERGING
    "APO","KKR","ONON","TTWO","TTD","PLD","EQIX","DLR","O","AMT","CCI","WELL","PGR","ALL","CB","MET","AFL","PRU","C","MS","USB","PNC","TFC","RF","KEY","ZION","CFG","FITB","HBAN","SIVB",
    # HEALTHCARE / BIOTECH
    "BJ","TDOC","VEEV","GILD","BIIB","ALNY","INCY","ALGN","DXCM","EW","SYK","BSX","ZBH","HOLX","HSKA","SRPT","ARWR","NTLA","EDIT","CRSP","BEAM","VCEL","FATE","BLUE",
    # ENERGY // OIL // GAS
    "OXY","DVN","FANG","MRO","COP","SLB","HAL","BKR","NOV","RIG","VAL","ENPH","SEDG","FSLR","NEE","DUK","SO","AEP","EXC","ED","ETR","PEG","CNP","AES","NRG",
    # RETAIL // CONSUMER // RESTAURANTS
    "AZO","ORLY","AAP","GPC","BBY","TGT","KR","ACI","WBD","PARA","FOX","NWSA","LYV","YUM","DPZ","CMG","DRI","TXRH","CAKE","DENN","PLAY","LOCO","HLT","MAR","H","RCL","CCL","NCLH","DASH","ABNB","BKNG","EXPE","MAR","CHH","WYNN","MGM","LVS","BYD","PENN","DKNG","CZR","MGM",
    # TECH // SEMICONDUCTORS // SOFTWARE
    "ASML","LNVGY","TSM","UMC","MXIM","ADI","MPWR","MCHP","ON","SWKS","QRVO","COHR","LITE","IIVI","RMBS","SNPS","CDNS","ANSS","PTC","POWI","SMTC","SLAB","DIOD","AMKR","TER","FORM","KLIC","ATOM","PI","VSH","NVMI",
    # INDUSTRIALS // MATERIALS // TRANSPORTATION
    "MMM","GE","HON","CAT","DE","ITW","PH","EMR","ETN","ROP","TDG","TRMB","AME","GNRC","FLS","XYL","PKG"
]
def fetch_tickers():
    if os.path.exists(CACHED_UNIVERSE):
        tickers = pd.read_csv(CACHED_UNIVERSE)["Ticker"].dropna().unique().tolist()
        if tickers: return tickers
    tickers=[]
    try:
        for tbl in pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"):
            for col in tbl.columns:
                if "symbol" in str(col).lower(): tickers += tbl[col].dropna().astype(str).tolist(); break
    except: pass
    try:
        for tbl in pd.read_html("https://en.wikipedia.org/wiki/NASDAQ-100"):
            for col in tbl.columns:
                if "ticker" in str(col).lower(): tickers += tbl[col].dropna().astype(str).tolist(); break
    except: pass
    try:
        for tbl in pd.read_html("https://en.wikipedia.org/wiki/Russell_2000_Index"):
            for col in tbl.columns:
                lc = str(col).lower()
                if "ticker" in lc or "symbol" in lc: tickers += tbl[col].dropna().astype(str).tolist(); break
    except: pass
    try:
        for tbl in pd.read_html("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"):
            for col in tbl.columns:
                lc = str(col).lower()
                if "symbol" in lc or "ticker" in lc: tickers += tbl[col].dropna().astype(str).tolist(); break
    except: pass
    tickers = sorted(set([t.strip().upper().replace(".","-") for t in tickers+EXPANDED_UNIVERSE if isinstance(t,str) and t.strip()]))
    if not tickers: tickers = EXPANDED_UNIVERSE
    pd.DataFrame({"Ticker":tickers}).to_csv(CACHED_UNIVERSE, index=False)
    return tickers

def compute_rsi(series, period=14):
    delta = series.diff().fillna(0)
    gain = delta.where(delta>=0,0).ewm(alpha=1/period,adjust=False).mean()
    loss = (-delta.where(delta<0,0)).ewm(alpha=1/period,adjust=False).mean()
    return 100-(100/(1+gain/loss))

def compute_wavetrend(df, n1=10, n2=21):
    hlc3 = (df["High"]+df["Low"]+df["Close"])/3
    esa = hlc3.ewm(span=n1,adjust=False).mean()
    ci = (hlc3-esa)/(0.015*(hlc3-esa).abs().ewm(span=n1,adjust=False).mean()+1e-12)
    return ci.ewm(span=n2,adjust=False).mean(), None

def compute_bollinger_pctb(df, period=20, std_mult=2):
    sma = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    return (df["Close"]-(sma-std*std_mult))/((sma+std*std_mult)-(sma-std*std_mult)+1e-12)

def compute_macd(df, fast=12, slow=26, signal=9):
    ef = df["Close"].ewm(span=fast,adjust=False).mean()
    es = df["Close"].ewm(span=slow,adjust=False).mean()
    macd = ef-es
    sig = macd.ewm(span=signal,adjust=False).mean()
    return macd, sig, macd-sig

def generate_market_summary():
    try:
        tickers = {
            "SPY":"S&P 500","QQQ":"Nasdaq 100","IWM":"Russell 2000",
            "VIX":"VIX","DIA":"Dow Jones",
            "XLF":"Financials","XLK":"Technology","XLE":"Energy","XLV":"Health Care"
        }
        end = datetime.now(); start = end - timedelta(days=60)
        data = yf.download(list(tickers.keys()), start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                           interval="1d", group_by="ticker", auto_adjust=True, progress=False)
        if data.empty:
            return "Market data unavailable."
        summary = {}
        for sym, label in tickers.items():
            try:
                if sym not in data.columns.get_level_values(0):
                    continue
                df = data[sym].dropna()
                if len(df) < 5:
                    continue
                close = df["Close"]
                chg_1d = (close.iloc[-1]/close.iloc[-2]-1)*100 if len(close)>=2 else 0
                chg_5d = (close.iloc[-1]/close.iloc[-6]-1)*100 if len(close)>=6 else 0
                summary[sym] = {
                    "label": label, "price": close.iloc[-1], "chg_1d": chg_1d, "chg_5d": chg_5d,
                    "sma20": close.rolling(20).mean().iloc[-1],
                    "sma50": close.rolling(50).mean().iloc[-1],
                    "rsi14": compute_rsi(close).iloc[-1]
                }
            except:
                continue
        if not summary:
            return "Market data unavailable."

        # Determine vibe / news
        spy = summary.get("SPY",{}); qqq = summary.get("QQQ",{}); vix = summary.get("VIX",{})
        spy_chg = spy.get("chg_1d", 0); qqq_chg = qqq.get("chg_1d", 0)
        vix_val = vix.get("price", 15)

        if spy_chg >= 1.0 and qqq_chg >= 1.5:
            vibe = "broad buying with tech leadership"
        elif spy_chg >= 0.5:
            vibe = "modest buying across the board"
        elif spy_chg <= -1.0 and qqq_chg <= -1.5:
            vibe = "broad selling, tech leading the decline"
        elif spy_chg <= -0.5:
            vibe = "modest selling pressure"
        elif abs(spy_chg) < 0.3 and abs(qqq_chg) < 0.5:
            vibe = "choppy / range-bound action"
        else:
            vibe = "mixed action with rotation"

        if vix_val > 25:
            news = "Elevated fear suggests geopolitical or macro catalysts may be in play."
        elif vix_val > 20:
            news = "Elevated volatility may reflect earnings or Fed-related uncertainty."
        elif spy_chg > 2.0 or qqq_chg > 3.0:
            news = "Strong rally could indicate positive macro headlines or AI/tech momentum."
        elif spy_chg < -2.0:
            news = "Sharp selloff may reflect tariff concerns, rate fears, or global risk-off."
        else:
            news = "No clear headline-driven extremes — price action is technically driven."

        overbought = sum(1 for s in summary.values() if s.get("rsi14", 0) > 70)
        oversold   = sum(1 for s in summary.values() if s.get("rsi14", 0) < 30)
        if overbought >= 2:
            breadth = "<span style='color:#ff6b6b;'>⚠ Overbought breadth — mean-reversion risk elevated</span>"
        elif oversold >= 2:
            breadth = "<span style='color:#68d670;'>Oversold breadth — bounce potential if support holds</span>"
        else:
            breadth = "Breadth: Neutral"

        # Build clean bullet-list HTML
        def _c(val):
            return "#68d670" if val >= 0 else "#ff6b6b"

        html = f"""
        <div style="font-family:system-ui,-apple-system,sans-serif;max-width:900px;margin-bottom:16px;">
            <div style="font-size:16px;font-weight:700;color:#e2e8f0;margin-bottom:10px;border-bottom:1px solid #334155;padding-bottom:6px;">
                Market Regime — {datetime.now().strftime('%A, %B %d %Y')}
            </div>
            <div style="font-size:13px;color:#94a3b8;margin-bottom:14px;line-height:1.5;">
                <i>S&P 500 <span style="color:{_c(spy_chg)};">{spy_chg:+.2f}%</span>,
                Nasdaq <span style="color:{_c(qqq_chg)};">{qqq_chg:+.2f}%</span> — {vibe}.<br>{news}</i>
            </div>

            <div style="margin-bottom:12px;">
                <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:6px;">Major Indices</div>
                <ul style="margin:0;padding-left:18px;font-size:13px;color:#cbd5e1;line-height:1.7;">
        """
        for sym in ["SPY","QQQ","IWM","DIA"]:
            if sym in summary:
                s = summary[sym]
                emoji = "↑" if s["chg_1d"] >= 0 else "↓"
                c = _c(s["chg_1d"])
                html += f'<li>{s["label"]}: <strong>${s["price"]:.2f}</strong> ({emoji} <span style="color:{c};">{s["chg_1d"]:+.2f}%</span>)</li>\n'
        if "VIX" in summary:
            v = summary["VIX"]
            html += f'<li>VIX: <strong>${v["price"]:.2f}</strong> (fear gauge)</li>\n'
        html += "</ul></div>\n"

        # Regime
        s = summary.get("SPY")
        if s:
            regime = []
            if s["price"] > s["sma20"] and s["price"] > s["sma50"]:
                regime.append("bullish trend")
            elif s["price"] < s["sma20"] and s["price"] < s["sma50"]:
                regime.append("bearish trend")
            else:
                regime.append("mixed / chop")
            if s["chg_1d"] < -1.5:
                regime.append("selling pressure")
            elif s["chg_1d"] > 1.5:
                regime.append("buying pressure")
            html += f"""
            <div style="margin-bottom:12px;">
                <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">S&P 500 Regime</div>
                <ul style="margin:0;padding-left:18px;font-size:13px;color:#cbd5e1;line-height:1.6;">
                    <li>{' | '.join(regime)}</li>
                </ul>
            </div>\n"""

        # Leadership
        if "QQQ" in summary and "SPY" in summary:
            q5 = summary["QQQ"]["chg_5d"]
            sp5 = summary["SPY"]["chg_5d"]
            iw = summary.get("IWM", {}).get("chg_5d", 0)
            if q5 > sp5 and q5 > iw:
                leader = "Tech-heavy (QQQ outperforming)"
            elif iw > sp5:
                leader = "Small-caps (IWM outperforming)"
            else:
                leader = "Broad market in sync"
            html += f"""
            <div style="margin-bottom:12px;">
                <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">Leadership (5D)</div>
                <ul style="margin:0;padding-left:18px;font-size:13px;color:#cbd5e1;line-height:1.6;">
                    <li>{leader}</li>
                </ul>
            </div>\n"""

        # Sectors
        sectors = []
        for sym in ["XLF","XLK","XLE","XLV"]:
            if sym in summary:
                s = summary[sym]
                color = "#68d670" if s["chg_5d"] >= 0 else "#ff6b6b"
                sectors.append(f'<span style="color:{color};">{s["label"]} {s["chg_5d"]:+.1f}%</span>')
        if sectors:
            html += f"""
            <div style="margin-bottom:12px;">
                <div style="font-size:12px;font-weight:600;color:#60a5fa;margin-bottom:4px;">Sectors (5D)</div>
                <ul style="margin:0;padding-left:18px;font-size:13px;color:#cbd5e1;line-height:1.6;">
                    <li>{' • '.join(sectors)}</li>
                </ul>
            </div>\n"""

        # Breadth
        html += f"""
            <div style="font-size:13px;color:#94a3b8;margin-top:8px;padding-top:6px;border-top:1px solid #334155;">
                {breadth}
            </div>
        </div>
        """
        return html.strip()
    except Exception as e:
        return f"Market summary error: {e}"


def download_batch(tickers, start, end):
    out = {}
    if not tickers: return out
    print(f"[DATA] Fetching {len(tickers)} tickers...")
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i+100]
        try:
            data = yf.download(chunk, start=start, end=end, interval="1d", group_by="ticker", auto_adjust=True, progress=False)
            if data.empty: continue
            if len(chunk) == 1: out[chunk[0]] = data.copy()
            else:
                for t in chunk:
                    if t in data.columns.get_level_values(0):
                        df = data[t].copy()
                        if not df.empty: out[t] = df
        except Exception as e: print(f"[WARN] Batch failed: {e}")
        for t in chunk:
            if t in out: continue
            try:
                s = yf.download(t, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
                if s is not None and not s.empty: out[t] = s
            except: pass
    print(f"[DATA] Fetched {len(out)} tickers.")
    return out

def screen_overextended(ticker_data, min_price=1.0, min_vol=100_000):
    rows = []
    for ticker, df in ticker_data.items():
        try:
            if len(df) < 40: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [" ".join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
            rename = {}
            for c in df.columns:
                lc = str(c).lower()
                if "close" in lc: rename[c] = "Close"
                elif "open" in lc: rename[c] = "Open"
                elif "high" in lc: rename[c] = "High"
                elif "low" in lc: rename[c] = "Low"
                elif "volume" in lc: rename[c] = "Volume"
            if rename: df = df.rename(columns=rename)
            df = df[["Open","High","Low","Close","Volume"]].dropna()
            if len(df) < 40: continue
            df["RSI14"] = compute_rsi(df["Close"])
            df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
            df["SMA50"] = df["Close"].rolling(50).mean()
            df["SMA200"] = df["Close"].rolling(200).mean()
            df["BB_PctB"] = compute_bollinger_pctb(df)
            df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = compute_macd(df)
            df["WT1"], _ = compute_wavetrend(df)
            df["AvgVol20"] = df["Volume"].rolling(20).mean()
            df["PriceChg1D"] = df["Close"].pct_change()
            df["PriceChg5D"] = df["Close"].pct_change(5)
            df["Dist_EMA20"] = (df["Close"]-df["EMA20"]) / df["EMA20"] * 100
            df["Dist_SMA50"] = (df["Close"]-df["SMA50"]) / df["SMA50"] * 100
            cur = df.iloc[-1]
            price = float(cur["Close"]); vol = float(cur["Volume"])
            if price < min_price or vol < min_vol: continue
            rsi = float(cur["RSI14"]); bb = float(cur["BB_PctB"])
            dist_ema20 = float(cur["Dist_EMA20"]); dist_sma50 = float(cur["Dist_SMA50"])
            chg_1d = float(cur["PriceChg1D"]) * 100; chg_5d = float(cur["PriceChg5D"]) * 100
            avg_vol = float(cur["AvgVol20"])
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0
            wt1 = float(cur["WT1"])
            hist = df["MACD_Hist"].dropna()
            macd_div = 0.0
            if len(hist) > 10:
                recent = hist.iloc[-10:]
                if cur["Close"] == df["Close"].iloc[-10:].max() and recent.iloc[-1] < recent.max():
                    macd_div = abs(recent.iloc[-1] - recent.max())
            score = 0.0
            score += max(0, (rsi - 60) * 2)
            score += max(0, (bb - 0.80) * 50)
            score += max(0, dist_ema20 * 3)
            score += max(0, dist_sma50 * 1.5)
            score += max(0, chg_1d * 5)
            score += max(0, (chg_5d - chg_1d) * 2)
            if wt1 > 50: score += (wt1 - 50) * 1.5
            if vol_ratio > 2: score += (vol_ratio - 2) * 10
            score += macd_div * 20
            rows.append({"Ticker": ticker, "Price": round(price,2), "RSI14": round(rsi,1), "BB_PctB": round(bb,3),
                "Dist_EMA20_%": round(dist_ema20,2), "Dist_SMA50_%": round(dist_sma50,2),
                "Chg_1D_%": round(chg_1d,2), "Chg_5D_%": round(chg_5d,2), "VolRatio": round(vol_ratio,2),
                "WT1": round(wt1,2), "ShortScore": round(score,2), "AvgVol": int(avg_vol)})
        except: pass
    df_out = pd.DataFrame(rows)
    if not df_out.empty: df_out = df_out.sort_values("ShortScore", ascending=False).reset_index(drop=True)
    return df_out

def fetch_short_interest(tickers):
    rows = []
    print("[SHORT] Fetching short interest...")
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            spf = info.get("shortPercentOfFloat")
            shares = info.get("sharesShort")
            ratio = info.get("shortRatio")
            if spf is None or spf == 0: continue
            price = info.get("currentPrice") or info.get("previousClose") or info.get("regularMarketPrice")
            avgvol = info.get("averageVolume")
            rows.append({"Ticker": t, "ShortPctFloat": round(spf*100,2), "SharesShort": int(shares) if shares else None,
                "DaysToCover": round(ratio,2) if ratio else None, "Price": price, "AvgVol": avgvol})
        except: pass
    df = pd.DataFrame(rows)
    if not df.empty:
        df["SqueezeRisk"] = df["ShortPctFloat"].fillna(0) * 2 + df["DaysToCover"].fillna(0) * 10
        df = df.sort_values("SqueezeRisk", ascending=False).reset_index(drop=True)
    return df


def detect_squeeze_signals(ticker_data, min_price=1.0, min_vol=100_000):
    """Detect pre-squeeze candidates: coiled springs, volume-driven breakouts, high short interest."""
    rows = []
    for ticker, df in ticker_data.items():
        try:
            if len(df) < 40: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [" ".join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
            rename = {}
            for c in df.columns:
                lc = str(c).lower()
                if "close" in lc: rename[c] = "Close"
                elif "high" in lc: rename[c] = "High"
                elif "low" in lc: rename[c] = "Low"
                elif "volume" in lc: rename[c] = "Volume"
            if rename: df = df.rename(columns=rename)
            close = df["Close"].dropna(); high = df["High"].dropna(); low = df["Low"].dropna(); vol = df["Volume"].dropna()
            if len(close) < 40: continue
            price = float(close.iloc[-1])
            if price < min_price: continue
            avg_vol_20 = vol.rolling(20).mean().iloc[-1]
            if avg_vol_20 < min_vol: continue
            rsi = compute_rsi(close)
            rsi_cur = float(rsi.iloc[-1]); rsi_min_20 = float(rsi.rolling(20).min().iloc[-1]); rsi_max_20 = float(rsi.rolling(20).max().iloc[-1])
            ema20 = close.ewm(span=20, adjust=False).mean(); sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
            dist_ema20 = (close.iloc[-1] - ema20.iloc[-1]) / ema20.iloc[-1] * 100
            dist_sma50 = (close.iloc[-1] - sma50.iloc[-1]) / sma50.iloc[-1] * 100
            dist_sma200 = (close.iloc[-1] - sma200.iloc[-1]) / sma200.iloc[-1] * 100
            sma20 = close.rolling(20).mean(); std20 = close.rolling(20).std(); upper = sma20 + std20 * 2; lower = sma20 - std20 * 2
            bb_width = ((upper - lower) / sma20 * 100).dropna(); bb_width_pct = bb_width.iloc[-1]; bb_width_min_20 = bb_width.rolling(20).min().iloc[-1]
            bb_pct_b = compute_bollinger_pctb(df).iloc[-1]
            vol_ratio = vol.iloc[-1] / avg_vol_20 if avg_vol_20 > 0 else 1
            vol_max_30 = (vol / vol.rolling(20).mean()).rolling(30).max().iloc[-1]
            vol_expanding = vol.iloc[-5:].mean() / vol.iloc[-20:-5].mean() if len(vol) >= 20 else 1
            daily_range = ((high - low) / close * 100).dropna(); avg_range_50 = daily_range.rolling(50).mean().iloc[-1]; recent_range_avg = daily_range.iloc[-10:].mean(); today_range = daily_range.iloc[-1]; range_expansion = today_range / recent_range_avg if recent_range_avg > 0 else 1
            low_20d = low.rolling(20).min().iloc[-1]; low_52w = low.rolling(252, min_periods=1).min().iloc[-1]; high_52w = high.rolling(252, min_periods=1).max().iloc[-1]
            dist_from_low52w = (price - low_52w) / low_52w * 100 if low_52w > 0 else 999
            dist_from_high52w = (high_52w - price) / high_52w * 100 if high_52w > 0 else 999
            dist_from_low20d = (price - low_20d) / low_20d * 100 if low_20d > 0 else 999
            chg_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else 0
            chg_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
            chg_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
            signals = []; score = 0
            if bb_width_pct < 5.0 and bb_width_pct > bb_width_min_20 * 1.5 and vol_ratio > 1.5:
                signals.append("Coiled Spring"); score += 30
            elif bb_width_min_20 < 4 and bb_width_pct > bb_width_min_20 * 1.3:
                signals.append("BB Squeeze"); score += 20
            if vol_ratio > 2.5 and range_expansion > 1.8 and chg_1d > 3:
                signals.append("Volume Breakout"); score += 35
            elif vol_ratio > 2.0 and range_expansion > 1.5 and chg_1d > 2:
                signals.append("Volume Spike"); score += 25
            elif vol_max_30 > 3.0 and vol_ratio < 1.2 and chg_1d < 1:
                signals.append("Post-Spike Coil"); score += 15
            if dist_from_low52w < 15 and chg_1d > 2 and vol_ratio > 1.5:
                signals.append("Short Covering Fuel"); score += 25
            elif dist_from_low52w < 25 and chg_5d > 5 and vol_ratio > 2:
                signals.append("Low Base Rally"); score += 20
            if price > ema20.iloc[-1] and price < sma50.iloc[-1] and vol_ratio > 1.5 and chg_1d > 0:
                signals.append("EMA20 Break w/ Resistance"); score += 20
            elif price > sma50.iloc[-1] and price < sma50.iloc[-1] * 1.05 and vol_ratio > 2:
                signals.append("SMA50 Pressure"); score += 18
            if price < 20 and vol_ratio > 3 and chg_1d > 5:
                signals.append("Meme Momentum"); score += 30
            elif price < 15 and vol_ratio > 2.5 and abs(chg_1d) > 3:
                signals.append("Retail Magnet"); score += 22
            if rsi_min_20 < 35 and 38 < rsi_cur < 65 and chg_5d > 3:
                signals.append("RSI Recovery"); score += 18
            elif rsi_cur < 35 and vol_ratio > 2:
                signals.append("Oversold + Volume"); score += 15
            if avg_range_50 > 0 and recent_range_avg < avg_range_50 * 0.6 and today_range > avg_range_50 * 1.3:
                signals.append("Consolidation Break"); score += 20
            if chg_5d > 8 and chg_20d < 15 and vol_expanding > 1.3 and price < sma50.iloc[-1] * 1.1:
                signals.append("Steady Ramp"); score += 17
            if not signals: continue
            if score < 25: continue
            score = min(100, score)
            adr_20 = daily_range.iloc[-20:].mean() if len(daily_range) >= 20 else 0
            vwap_20 = (close * vol).rolling(20).sum().iloc[-1] / vol.rolling(20).sum().iloc[-1] if vol.rolling(20).sum().iloc[-1] > 0 else price
            resistance = high.iloc[-20:].max() if len(high) >= 20 else price
            support = low_20d
            rows.append({"Ticker": ticker, "Price": round(price,2), "SqueezeScore": round(score,1), "Signals": ", ".join(signals), "SignalCount": len(signals),
                "DistFromLow52w": round(dist_from_low52w,1), "DistFromHigh52w": round(dist_from_high52w,1), "DistFromLow20d": round(dist_from_low20d,1),
                "VolRatio": round(vol_ratio,2), "VolMax30": round(vol_max_30,2), "BBWidth": round(bb_width_pct,2), "BBPctB": round(bb_pct_b,3),
                "RangeExpansion": round(range_expansion,2), "AvgRange50": round(avg_range_50,2), "RSI": round(rsi_cur,1), "RSIMin20": round(rsi_min_20,1),
                "RSIMax20": round(rsi_max_20,1), "DistEMA20": round(dist_ema20,2), "DistSMA50": round(dist_sma50,2), "Chg1D": round(chg_1d,2),
                "Chg5D": round(chg_5d,2), "Chg20D": round(chg_20d,2), "ADR20": round(adr_20,2), "VWAP20": round(vwap_20,2),
                "AvgVol": int(avg_vol_20), "Resistance": round(resistance,2), "Support": round(support,2)})
        except: pass
    df_out = pd.DataFrame(rows)
    if not df_out.empty: df_out = df_out.sort_values("SqueezeScore", ascending=False).reset_index(drop=True)
    return df_out
def _color(val): return "#68d670" if val >= 0 else "#ff6b6b"

def _make_overext_rows(df):
    html = []
    for _, r in df.head(20).iterrows():
        bar = min(100, max(0, r["ShortScore"])); bar_color = "rgba(220,50,50,.8)" if r["ShortScore"] > 80 else "rgba(200,140,50,.8)"
        c20 = _color(r["Dist_EMA20_%"]); c50 = _color(r["Dist_SMA50_%"]); c1 = _color(r["Chg_1D_%"]); c5 = _color(r["Chg_5D_%"])
        html.append(f'<tr data-price="{r["Price"]}" data-vol="{r.get("AvgVol", 100000)}">'
            f'<td><strong>{r["Ticker"]}</strong></td>'
            f'<td data-sort="{r["ShortScore"]}"><div style="background:#1a1a2e;border-radius:4px;height:18px;width:100%;position:relative;"><div style="width:{bar}%;background:{bar_color};height:100%;border-radius:4px;"></div><span style="position:absolute;right:6px;top:0;font-size:11px;line-height:18px;">{r["ShortScore"]}</span></div></td>'
            f'<td data-sort="{r["Price"]}">${r["Price"]}</td>'
            f'<td data-sort="{r["RSI14"] if r["RSI14"] is not None else -1}">{r["RSI14"]}</td>'
            f'<td data-sort="{r["BB_PctB"] if r["BB_PctB"] is not None else -1}">{r["BB_PctB"]}</td>'
            f'<td data-sort="{r["Dist_EMA20_%"]}"><span style="color:{c20};">{r["Dist_EMA20_%"]:.2f}%</span></td>'
            f'<td data-sort="{r["Dist_SMA50_%"]}"><span style="color:{c50};">{r["Dist_SMA50_%"]:.2f}%</span></td>'
            f'<td data-sort="{r["Chg_1D_%"]}"><span style="color:{c1};">{r["Chg_1D_%"]:+.2f}%</span></td>'
            f'<td data-sort="{r["Chg_5D_%"]}"><span style="color:{c5};">{r["Chg_5D_%"]:+.2f}%</span></td>'
            f'<td data-sort="{r["VolRatio"]}">{r["VolRatio"]}x</td>'
            f'<td data-sort="{r["WT1"] if r["WT1"] is not None else -999}">{r["WT1"]}</td>'
            f'</tr>')
    return "\n".join(html)

def _make_short_rows(df):
    html = []
    for _, r in df.head(30).iterrows():
        bar = min(100, max(0, r["SqueezeRisk"])); bar_color = "rgba(220,50,50,.8)"
        price = r.get("Price") or 0; vol = r.get("AvgVol") or 0
        html.append(f'<tr data-price="{price}" data-vol="{vol}">'
            f'<td><strong>{r["Ticker"]}</strong></td>'
            f'<td data-sort="{price}">${price if price else "N/A"}</td>'
            f'<td data-sort="{r["ShortPctFloat"] or 0}"><span style="color:#ff6b6b;">{r["ShortPctFloat"]}%</span></td>'
            f'<td data-sort="{r["DaysToCover"] or 0}">{r["DaysToCover"]}</td>'
            f'<td data-sort="{r["SharesShort"] or 0}">{r["SharesShort"]:,}</td>'
            f'<td data-sort="{r["SqueezeRisk"]}"><div style="background:#1a1a2e;border-radius:4px;height:18px;width:100%;position:relative;"><div style="width:{bar}%;background:{bar_color};height:100%;border-radius:4px;"></div><span style="position:absolute;right:6px;top:0;font-size:11px;line-height:18px;">{r["SqueezeRisk"]:.0f}</span></div></td>'
            f'</tr>')
    return "\n".join(html)

def _make_squeeze_rows(df):
    html = []
    for _, r in df.head(30).iterrows():
        bar = min(100, max(0, r["SqueezeScore"]))
        if r["SqueezeScore"] > 70: bar_color = "rgba(220,50,50,.9)"; sig_color = "#ff6b6b"
        elif r["SqueezeScore"] > 45: bar_color = "rgba(255,170,50,.9)"; sig_color = "#ffa233"
        else: bar_color = "rgba(255,200,50,.8)"; sig_color = "#ccc"
        c1 = "#68d670" if r["Chg1D"] >= 0 else "#ff6b6b"
        c5 = "#68d670" if r["Chg5D"] >= 0 else "#ff6b6b"
        html.append(f'<tr data-price="{r["Price"]}" data-vol="{r["AvgVol"]}">'
            f'<td><strong>{r["Ticker"]}</strong></td>'
            f'<td data-sort="{r["Price"]}">${r["Price"]}</td>'
            f'<td data-sort="{r["SqueezeScore"]}"><div style="background:#1a1a2e;border-radius:4px;height:18px;width:100%;position:relative;"><div style="width:{bar}%;background:{bar_color};height:100%;border-radius:4px;"></div><span style="position:absolute;right:6px;top:0;font-size:11px;line-height:18px;">{r["SqueezeScore"]}</span></div></td>'
            f'<td style="font-size:11px;max-width:200px;white-space:normal;"><span style="color:{sig_color};">{r["Signals"]}</span></td>'
            f'<td data-sort="{r["Chg1D"]}"><span style="color:{c1};">{r["Chg1D"]:+.1f}%</span></td>'
            f'<td data-sort="{r["Chg5D"]}"><span style="color:{c5};">{r["Chg5D"]:+.1f}%</span></td>'
            f'<td data-sort="{r["VolRatio"]}">{r["VolRatio"]}x</td>'
            f'<td data-sort="{r["BBWidth"]}">{r["BBWidth"]:.1f}%</td>'
            f'<td data-sort="{r["RSI"]}">{r["RSI"]}</td>'
            f'<td data-sort="{r["DistFromLow52w"]}">{r["DistFromLow52w"]:.0f}%</td>'
            f'<td data-sort="{r["DistFromHigh52w"]}">{r["DistFromHigh52w"]:.0f}%</td>'
            f'<td data-sort="{r["Support"]}">${r["Support"]:.2f}</td>'
            f'<td data-sort="{r["Resistance"]}">${r["Resistance"]:.2f}</td>'
            f'</tr>')
    return "\n".join(html)
def fetch_crypto_data():
    """Fetch top crypto tickers. Returns dict of ticker > dataframe."""
    crypto_tickers = [
        "BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD",
        "AVAX-USD","DOT-USD","LINK-USD","LTC-USD","UNI-USD","MATIC-USD",
        "ATOM-USD","BCH-USD","ETC-USD","ICP-USD","XLM-USD","NEAR-USD",
        "FIL-USD","ALGO-USD","VET-USD","AAVE-USD","SUSHI-USD","MKR-USD",
        "YFI-USD","COMP-USD","ZRX-USD","MANA-USD","SAND-USD","AXS-USD",
        "FTM-USD","THETA-USD","GRT-USD","CHZ-USD","ENJ-USD","BAT-USD",
        "REN-USD","BNT-USD","CRV-USD","LRC-USD","STORJ-USD","NMR-USD"
    ]
    out = {}
    end = datetime.now(); start_d = end - timedelta(days=8)
    try:
        data = yf.download(crypto_tickers, start=start_d.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"), interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False)
        for t in crypto_tickers:
            try:
                if len(crypto_tickers) == 1:
                    df = data.copy()
                else:
                    df = data[t].copy()
                if not df.empty: out[t] = df
            except: pass
    except Exception as e:
        print(f"[CRYPTO WARN] batch failed: {e}")
    for t in crypto_tickers:
        if t in out: continue
        try:
            s = yf.download(t, start=start_d.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"), interval="1d",
                           auto_adjust=True, progress=False)
            if s is not None and not s.empty: out[t] = s
        except: pass

    # Try 1h for recent price action
    start_h = end - timedelta(days=7)
    out_1h = {}
    for t in list(out.keys()):
        try:
            h = yf.download(t, start=start_h.strftime("%Y-%m-%d"),
                           end=end.strftime("%Y-%m-%d"), interval="1h",
                           auto_adjust=True, progress=False)
            if h is not None and len(h) > 2:
                out_1h[t] = h
        except: pass
    return out, out_1h

def screen_crypto(daily_data, hourly_data):
    """Screen top crypto by daily % gain (fallback to hourly if daily sparse)."""
    rows = []
    for ticker, df in daily_data.items():
        try:
            close = df["Close"].dropna()
            vol  = df["Volume"].dropna()
            if len(close) < 2: continue
            price = float(close.iloc[-1])
            chg_1d = (close.iloc[-1]/close.iloc[-2]-1)*100 if len(close)>=2 else 0
            chg_7d = (close.iloc[-1]/close.iloc[0]-1)*100 if len(close)>=7 else 0
            avg_vol = vol.rolling(20).mean().iloc[-1] if len(vol) > 0 else 0
            vol_ratio = (vol.iloc[-1] / avg_vol) if avg_vol > 0 else 1

            # 1h change
            chg_1h = 0.0
            if ticker in hourly_data:
                h_close = hourly_data[ticker]["Close"].dropna()
                if len(h_close) >= 2:
                    chg_1h = (h_close.iloc[-1]/h_close.iloc[-2]-1)*100

            symbol = ticker.replace("-USD","")
            rows.append({
                "Symbol": symbol, "Price": round(price,2),
                "Chg_1H": round(chg_1h,2), "Chg_1D": round(chg_1d,2),
                "Chg_7D": round(chg_7d,2), "VolRatio": round(vol_ratio,2),
                "Abs_1D": abs(chg_1d)  # for sorting
            })
        except: pass
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out = df_out.sort_values("Abs_1D", ascending=False).reset_index(drop=True)
    return df_out

def _make_crypto_rows(df):
    html = []
    for _, r in df.head(20).iterrows():
        c1h = "#68d670" if r["Chg_1H"] >= 0 else "#ff6b6b"
        c1d = "#68d670" if r["Chg_1D"] >= 0 else "#ff6b6b"
        c7d = "#68d670" if r["Chg_7D"] >= 0 else "#ff6b6b"
        html.append(
            f'<tr data-1h="{r["Chg_1H"]}" data-1d="{r["Chg_1D"]}">'
            f'<td><strong>{r["Symbol"]}</strong></td>'
            f'<td data-sort="{r["Price"]}">${r["Price"]}</td>'
            f'<td data-sort="{r["Chg_1H"]}"><span style="color:{c1h};">{r["Chg_1H"]:+.2f}%</span></td>'
            f'<td data-sort="{r["Chg_1D"]}"><span style="color:{c1d};">{r["Chg_1D"]:+.2f}%</span></td>'
            f'<td data-sort="{r["Chg_7D"]}"><span style="color:{c7d};">{r["Chg_7D"]:+.2f}%</span></td>'
            f'<td data-sort="{r["VolRatio"]}">{r["VolRatio"]}x</td>'
            f'</tr>'
        )
    return "\n".join(html)

def generate_report(df_overext, df_short, df_squeeze, df_crypto, summary_html):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_block = ""
    if summary_html:
        summary_block = f'<div class="summary-box">{summary_html}</div>'
    with open(TMPL_PATH, "r", encoding="utf-8") as f:
        tmpl = f.read()
    crypto_rows = _make_crypto_rows(df_crypto) if df_crypto is not None and not df_crypto.empty else "<tr><td colspan='6'>Crypto data unavailable</td></tr>"
    html = tmpl.replace("{{TS}}", ts).replace("{{SUMMARY_BLOCK}}", summary_block) \
        .replace("{{OVEREXT_ROWS}}", _make_overext_rows(df_overext)) \
        .replace("{{SHORT_ROWS}}", _make_short_rows(df_short)) \
        .replace("{{SQUEEZE_ROWS}}", _make_squeeze_rows(df_squeeze)) \
        .replace("{{CRYPTO_ROWS}}", crypto_rows)
    fname = f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    path = os.path.join(REPORTS_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    return path

if __name__ == "__main__":
    print("="*60)
    print("DAILY SHORT SCREENER")
    print("="*60)
    end = datetime.now()
    start = end - timedelta(days=365)
    tickers = fetch_tickers()
    data = download_batch(tickers, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    overext = screen_overextended(data, min_price=1.0, min_vol=100_000)
    if overext.empty: print("[OVEREXT] No candidates.")
    else: print(f"[OVEREXT] {len(overext)} candidates. Top 5: {', '.join(overext.head(5)['Ticker'])}")
    squeeze = detect_squeeze_signals(data, min_price=1.0, min_vol=100_000)
    if squeeze.empty: print("[SQUEEZE] No candidates.")
    else: print(f"[SQUEEZE] {len(squeeze)} candidates. Top 5: {', '.join(squeeze.head(5)['Ticker'])}")
    shorts = fetch_short_interest(tickers)
    if shorts.empty: print("[SHORTS] No data.")
    else: print(f"[SHORTS] {len(shorts)} tickers with short interest. Top 5: {', '.join(shorts.head(5)['Ticker'])}")
    print("[CRYPTO] Fetching crypto data...")
    crypto_d, crypto_h = fetch_crypto_data()
    df_crypto = screen_crypto(crypto_d, crypto_h)
    if df_crypto.empty: print("[CRYPTO] No data.")
    else: print(f"[CRYPTO] {len(df_crypto)} coins. Top 5: {', '.join(df_crypto.head(5)['Symbol'])}")
    summary_html = generate_market_summary()
    report_path = generate_report(overext, shorts, squeeze, df_crypto, summary_html)
    print(f"[REPORT] Saved: {report_path}")
