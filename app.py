import math
import io
import html as html_lib
import re
import time
import random
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="四时段强势回踩大师 V20.1", page_icon="🎲", layout="wide")

JST = timezone(timedelta(hours=9))

STOCKS = [
    ("627A", "ａｋｉｐｐａ", "akippa"),
    ("6203", "豊和工業", "丰和工业"),
    ("485A", "パワーエックス", "PowerX"),
    ("634A", "レイヤード", "Layered"),
    ("6904", "原田工業", "原田工业"),
    ("4073", "ジィ・シィ企画", "GC企划"),
    ("6533", "Orchestra Holdings", "Orchestra控股"),
    ("625A", "Skyfall", "Skyfall"),
    ("5706", "三井金属", "三井金属"),
    ("2980", "SREホールディングス", "SRE控股"),
    ("5802", "住友電気工業", "住友电工"),
    ("6920", "レーザーテック", "Lasertec"),
    ("7013", "IHI", "IHI"),
    ("7012", "川崎重工業", "川崎重工"),
    ("8593", "三菱HCキャピタル", "三菱HC资本"),
    ("5016", "JX金属", "JX金属"),
    ("6208", "石川製作所", "石川制作所"),
    ("4274", "細谷火工", "细谷火工"),
    ("4440", "ヴィッツ", "Vitz"),
    ("4052", "フィーチャ", "Ficha"),
    ("604A", "ビーエイブル", "B-able"),
    ("8848", "レオパレス21", "Leopalace21"),
    ("6330", "東洋エンジニアリング", "东洋工程"),
    ("5801", "古河電気工業", "古河电工"),
    ("8267", "イオン", "永旺"),
    ("3103", "ユニチカ", "尤尼吉可"),
    ("3110", "日東紡績", "日东纺织"),
    ("3003", "ヒューリック", "Hulic"),
    ("200A", "NEXT FUNDS 日経半導体株指数連動型上場投信", "NEXT FUNDS日经半导体ETF"),
    ("3350", "メタプラネット", "Metaplanet"),
    ("3231", "野村不動産ホールディングス", "野村不动产控股"),
    ("3101", "東洋紡", "东洋纺"),
    ("5713", "住友金属鉱山", "住友金属矿山"),
    ("6701", "NEC", "NEC"),
    ("4564", "オンコセラピー・サイエンス", "OncoTherapy Science"),
    ("1615", "NEXT FUNDS 東証銀行業株価指数連動型上場投信", "NEXT FUNDS东证银行业ETF"),
    ("4063", "信越化学工業", "信越化学"),
    ("2502", "アサヒグループホールディングス", "朝日集团控股"),
    ("7203", "トヨタ自動車", "丰田汽车"),
    ("7261", "マツダ", "马自达"),
    ("3905", "データセクション", "DataSection"),
    ("5074", "テスホールディングス", "TESS控股"),
    ("4901", "富士フイルムホールディングス", "富士胶片控股"),
    ("6526", "ソシオネクスト", "Socionext"),
    ("8001", "伊藤忠商事", "伊藤忠商事"),
    ("8306", "三菱UFJフィナンシャル・グループ", "三菱UFJ金融集团"),
    ("2768", "双日", "双日"),
    ("1570", "NEXT FUNDS 日経平均レバレッジ・インデックス連動型上場投信", "NEXT FUNDS日经平均杠杆ETF"),
    ("6305", "日立建機", "日立建机"),
    ("4062", "イビデン", "揖斐电"),
    ("285A", "キオクシアホールディングス", "铠侠控股"),
    ("5803", "フジクラ", "藤仓"),
    ("6758", "ソニーグループ", "索尼集团"),
    ("4755", "楽天グループ", "乐天集团"),
    ("9432", "NTT", "NTT"),
    ("8136", "サンリオ", "三丽鸥"),
    ("4661", "オリエンタルランド", "东方乐园"),
    ("3038", "神戸物産", "神户物产"),
    ("282A", "Global X 半導体・トップ10-日本株式", "Global X日本半导体Top10 ETF"),
    ("9984", "ソフトバンクグループ", "软银集团"),
    ("7974", "任天堂", "任天堂"),
    ("8035", "東京エレクトロン", "东京电子"),
    ("6146", "ディスコ", "DISCO"),
    ("6857", "アドバンテスト", "爱德万测试"),
    ("6981", "村田製作所", "村田制作所"),
    ("3778", "さくらインターネット", "樱花互联网"),
    ("3099", "三越伊勢丹ホールディングス", "三越伊势丹控股"),
    ("6976", "太陽誘電", "太阳诱电"),
    ("6367", "ダイキン工業", "大金工业"),
    ("6506", "安川電機", "安川电机"),
    ("7936", "アシックス", "亚瑟士"),
    ("8058", "三菱商事", "三菱商事"),
]
STOCK_CODES = [x[0] for x in STOCKS]
STOCK_META = {code: {"jp": jp, "zh": zh} for code, jp, zh in STOCKS}

def stock_label(code: str) -> str:
    m = STOCK_META.get(code, {})
    return f"{code}｜{m.get('jp','')}｜{m.get('zh','')}"


RULES = [
    "原本就强 + 健康回踩不破关键位 + 再次转强，才考虑买；同等质量优先上方空间更大、下方支撑更近的候选。",
    "连续创新低、收盘重心持续下移的弱票，直接重罚；不能因为“跌很多了”就自动抄底。",
    "有量不等于强：如果放量但价格不涨、冲高回落、收盘仍弱，视为派发/承接不足风险。",
    "弱势结构里的突然暴拉不追；但强趋势、接近/突破前高、涨幅留存好且风险门槛通过的真突破，允许追强。",
    "关注新闻催化、最近走势、当前所处价位；新闻只作催化佐证，不替代价格确认。",
    "突然单日暴涨、明显远离短期均线时，即使评分高也增加追高惩罚。",
    "优先考虑强势趋势中的小回调：跌一点不是买点本身，必须仍守住关键位，并保留重新转强的条件。",
    "随机只用于合格候选之间的点兵，不允许把连续创新低、破位弱票随机成买入候选。",
    "资金少也是现实约束：在质量相近的合格候选里，优先一手资金更低、资金利用率更高的股票。",
    "便宜只做同档候选的加分项，绝不能让低价弱票因为便宜就越过结构更好的强票。",
    "重视涨幅保留率：冲高后能把大部分涨幅留到收盘、连续几天收盘重心抬高，加分；反复冲高全吐、收盘越来越低，扣分。",
    "一旦给出可买/推荐，必须同时给动态止盈参考：结合买入价、ATR、近期前高/压力位和通常涨停价，而不是统一写死+5%。",
    "收盘前大引不成只挑隔夜质量：尾盘站得住、接近日高但不过热、最后30分钟不跳水、最好站在VWAP上方且有合理尾盘量能；尾盘拉一根骗炮或当天已经失控加速的不追。",
]

MODE_DESCRIPTIONS = {
    "开盘前": "用昨收/历史结构 + 隔夜新闻做盘前筛选。重点找今天值得盯的票，不把尚未发生的盘中转强当成既成事实。",
    "盘中": "重点判断现在是否真的转强：实时价格、当日高低位置、量价、冲高回落与追高风险权重最高。",
    "收盘后预测明天": "重点看收盘质量、全天涨幅保留、量能、关键位是否守住，以及新闻催化，用来挑明天优先观察/埋伏的票。",
    "收盘前大引不成": "专门筛选适合收盘集合竞价前考虑隔夜持有的候选：重尾盘承接、收盘位置、VWAP、最后30分钟动量与量能，同时严惩冲高回落、尾盘跳水、过度加速和弱趋势。",
}

POSITIVE_KW = [
    "上方修正","増益","増収","最高益","過去最高","上方修正","受注","大型受注","採用","提携","業務提携","資本提携",
    "自社株買い","増配","復配","承認","認可","特許","新製品","新サービス","黒字転換","TOB","MBO","買収","株主還元",
    "好調","急拡大","契約","共同開発","AI","半導体","防衛","データセンター","電線","電力","インフラ"
]
NEGATIVE_KW = [
    "下方修正","減益","減収","赤字","赤字転落","業績悪化","不正","調査","行政処分","訴訟","事故","リコール","減配",
    "希薄化","増資","MSワラント","新株予約権","公募増資","売出し","破産","民事再生","債務超過"
]



# JPX normal daily price-limit table. The base price is normally the previous close / final quote.
# Special widened limits can apply after certain consecutive limit sessions, so this is the normal-limit calculator only.
JPX_LIMIT_TABLE = [
    (100, 30), (200, 50), (500, 80), (700, 100), (1000, 150), (1500, 300),
    (2000, 400), (3000, 500), (5000, 700), (7000, 1000), (10000, 1500),
    (15000, 3000), (20000, 4000), (30000, 5000), (50000, 7000), (70000, 10000),
    (100000, 15000), (150000, 30000), (200000, 40000), (300000, 50000), (500000, 70000),
    (700000, 100000), (1000000, 150000), (1500000, 300000), (2000000, 400000),
    (3000000, 500000), (5000000, 700000), (7000000, 1000000), (10000000, 1500000),
    (15000000, 3000000), (20000000, 4000000), (30000000, 5000000), (50000000, 7000000),
    (float("inf"), 10000000),
]

def jpx_normal_limit(base_price):
    if base_price is None or not math.isfinite(base_price) or base_price <= 0:
        return np.nan, np.nan, np.nan
    width = next(w for upper, w in JPX_LIMIT_TABLE if base_price < upper)
    return max(1, base_price - width), base_price + width, width

def pullback_preference(day_pct, support_gap, from_h20, c, ma20):
    """Reward a modest pullback only when the trend/support structure remains intact."""
    s = 0.0
    if math.isfinite(day_pct):
        if -4.0 <= day_pct <= -0.5:
            s += 9
        elif -0.5 < day_pct <= 1.5:
            s += 5
        elif day_pct >= 6:
            s -= 10
        elif day_pct < -6:
            s -= 10
    if math.isfinite(support_gap):
        if 0 <= support_gap <= 4:
            s += 7
        elif support_gap < 0:
            s -= 14
    if math.isfinite(from_h20):
        draw = -from_h20
        if 3 <= draw <= 10:
            s += 6
        elif draw > 18:
            s -= 8
    if math.isfinite(ma20) and c >= ma20:
        s += 4
    return float(np.clip(s, -25, 25))


def pullback_quality_score(day_pct, r5, support_gap, from_h20, c, ma20, last_vol_ratio, structure_score):
    """Score a *healthy* pullback, not mere cheapness.

    Rewards: prior strength still intact, modest retreat, nearby support, contracting sell volume,
    and enough room back to a recent high. Penalizes deep/accelerating declines and support breaks.
    """
    s = 0.0
    # 1-day retreat: modest weakness is preferred; a plunge is not.
    if math.isfinite(day_pct):
        if -3.5 <= day_pct <= -0.8:
            s += 10
        elif -0.8 < day_pct <= 0.8:
            s += 5
        elif 0.8 < day_pct <= 3.0:
            s += 1
        elif day_pct > 5.0:
            s -= 7
        elif day_pct < -5.0:
            s -= 11

    # Multi-day trend must not be collapsing.
    if math.isfinite(r5):
        if 0 <= r5 <= 12:
            s += 5
        elif -3 <= r5 < 0:
            s += 2
        elif r5 < -7:
            s -= 10

    # Nearby support gives a defined downside reference.
    if math.isfinite(support_gap):
        if 0 <= support_gap <= 2.5:
            s += 9
        elif 2.5 < support_gap <= 5.5:
            s += 5
        elif support_gap < 0:
            s -= 16
        elif support_gap > 8:
            s -= 5

    # A useful pullback leaves room to the recent high, but very deep drawdowns are not 'healthy'.
    if math.isfinite(from_h20):
        draw = -from_h20
        if 3 <= draw <= 12:
            s += 9
        elif 12 < draw <= 18:
            s += 2
        elif draw > 18:
            s -= 10
        elif draw < 1:
            s -= 2

    # Price should still respect the medium-term structure.
    if math.isfinite(ma20):
        if c >= ma20:
            s += 6
        elif c < ma20 * 0.98:
            s -= 10

    # Pullbacks on lighter volume are healthier than heavy-volume selloffs.
    if math.isfinite(day_pct) and day_pct < 0 and math.isfinite(last_vol_ratio):
        if last_vol_ratio <= 0.85:
            s += 6
        elif last_vol_ratio >= 1.5:
            s -= 8

    # Structural consistency is a gate, not a free pass.
    if math.isfinite(structure_score):
        if structure_score >= 8:
            s += 5
        elif structure_score <= -6:
            s -= 7

    return float(np.clip(s, -35, 40))


def reward_risk_proxy(from_h20, support_gap, pullback_quality):
    """Simple observable proxy: room to recent high versus distance to nearby support.

    It is deliberately capped and only rewards already-healthy pullbacks.
    """
    if pullback_quality < 8 or not (math.isfinite(from_h20) and math.isfinite(support_gap)):
        return 0.0, np.nan
    upside = max(0.0, -from_h20)
    downside = max(0.6, support_gap)
    ratio = upside / downside if downside > 0 else np.nan
    score = 0.0
    if 3 <= upside <= 15:
        if ratio >= 3.0:
            score = 8.0
        elif ratio >= 2.0:
            score = 6.0
        elif ratio >= 1.3:
            score = 3.0
    return score, ratio


def affordability_score(price, budget=300000):
    """Capital friendliness for a standard 100-share cash lot.

    V20.1: moderately stronger than before and relative to the user's actual budget.
    Cheapness can separate otherwise comparable candidates, but never rescues a weak stock.
    Maximum bonus is 14 points.
    """
    if price is None or not math.isfinite(price) or price <= 0:
        return 0.0, np.nan, False
    lot_cash = float(price) * 100.0
    budget = float(budget) if budget and math.isfinite(float(budget)) and float(budget) > 0 else 300000.0
    fits = lot_cash <= budget
    ratio = lot_cash / budget

    # Moderate weighting: noticeably rewards usable 100-share lots without making price the main factor.
    if ratio <= 0.35:
        s = 14
    elif ratio <= 0.50:
        s = 13
    elif ratio <= 0.70:
        s = 11
    elif ratio <= 0.90:
        s = 9
    elif ratio <= 1.00:
        s = 8
    elif ratio <= 1.25:
        s = 5
    elif ratio <= 1.60:
        s = 2
    elif ratio <= 2.00:
        s = 1
    else:
        s = 0
    return float(s), float(lot_cash), bool(fits)


def structure_consistency(close: pd.Series, low: pd.Series, high: pd.Series):
    """Reward sustained structure instead of one-off spikes."""
    if len(close) < 25:
        return 0.0
    c20 = close.tail(20)
    ma20s = close.rolling(20).mean().tail(20)
    above = float((c20 > ma20s).mean()) if ma20s.notna().any() else 0.0
    # compare 5-day blocks: higher lows / higher highs
    lows = [safe_float(low.iloc[-20:-15].min()), safe_float(low.iloc[-15:-10].min()), safe_float(low.iloc[-10:-5].min()), safe_float(low.iloc[-5:].min())]
    highs = [safe_float(high.iloc[-20:-15].max()), safe_float(high.iloc[-15:-10].max()), safe_float(high.iloc[-10:-5].max()), safe_float(high.iloc[-5:].max())]
    hl = sum(lows[i] >= lows[i-1] for i in range(1,4))
    hh = sum(highs[i] >= highs[i-1] for i in range(1,4))
    s = above * 14 + hl * 2.5 + hh * 1.5
    return float(np.clip(s, 0, 28))


def volatility_risk(high: pd.Series, low: pd.Series, close: pd.Series):
    if len(close) < 15:
        return 0.0, np.nan
    prev = close.shift(1)
    tr = pd.concat([(high-low).abs(), (high-prev).abs(), (low-prev).abs()], axis=1).max(axis=1)
    atr14 = safe_float(tr.rolling(14).mean().iloc[-1])
    c = safe_float(close.iloc[-1])
    atr_pct = atr14 / c * 100 if math.isfinite(atr14) and c > 0 else np.nan
    penalty = 0.0
    if math.isfinite(atr_pct):
        if atr_pct >= 9: penalty = 15
        elif atr_pct >= 7: penalty = 10
        elif atr_pct >= 5: penalty = 5
    return penalty, atr_pct


@st.cache_data(ttl=60, show_spinner=False)
def download_intraday(codes_tuple):
    symbols = [ticker(c) for c in codes_tuple]
    try:
        return yf.download(
            tickers=symbols,
            period="1d",
            interval="5m",
            auto_adjust=False,
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception:
        return pd.DataFrame()


def extract_intraday(data, code):
    if data is None or getattr(data, "empty", True):
        return None
    sym = ticker(code)
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if sym in data.columns.get_level_values(0):
                d = data[sym].copy()
            elif sym in data.columns.get_level_values(-1):
                d = data.xs(sym, axis=1, level=-1).copy()
            else:
                return None
        else:
            d = data.copy()
        d = d.dropna(how="all")
        return d if not d.empty else None
    except Exception:
        return None


def apply_intraday_features(rank, intraday_batch):
    rank = rank.copy()
    for col, default in [("盘中现价", np.nan),("盘中涨跌%", np.nan),("当日位置%", np.nan),("距日高%", np.nan),("盘中量价分",0.0),
                         ("5分MA20", np.nan),("距5分MA20%", np.nan),("5分MA20斜率%", np.nan),("5分结构分",0.0),
                         ("尾盘30分钟%", np.nan),("尾盘量能倍率", np.nan),("VWAP偏离%", np.nan),("尾盘强度分",0.0),("日内涨幅保留率%", np.nan)]:
        rank[col] = default
    for idx, row in rank.iterrows():
        code = str(row["代码"])
        d = extract_intraday(intraday_batch, code)
        if d is None or len(d) < 2 or "Close" not in d.columns:
            continue
        c = safe_float(d["Close"].dropna().iloc[-1])
        hi = safe_float(d["High"].max()) if "High" in d.columns else c
        lo = safe_float(d["Low"].min()) if "Low" in d.columns else c
        prev = safe_float(row.get("现价", np.nan))
        # daily row may already include today's partial bar; prefer prior close reconstructed from 日涨跌 when possible
        daypct = safe_float(row.get("日涨跌%", np.nan))
        if math.isfinite(daypct) and math.isfinite(prev) and abs(daypct) < 50:
            base = prev / (1 + daypct/100.0) if (1 + daypct/100.0) != 0 else np.nan
        else:
            base = np.nan
        if not math.isfinite(base):
            base = safe_float(d["Open"].dropna().iloc[0])
        dp = pct(c, base)
        pos = (c-lo)/(hi-lo)*100 if math.isfinite(hi) and math.isfinite(lo) and hi>lo else np.nan
        from_hi = pct(c, hi)
        score = 0.0
        if math.isfinite(dp):
            if 0.5 <= dp <= 4: score += 8
            elif dp > 7: score -= 7
            elif dp < -4: score -= 9
        if math.isfinite(pos):
            if pos >= 75: score += 7
            elif pos <= 25: score -= 7
        if math.isfinite(from_hi) and from_hi < -3: score -= 4

        # Short-cycle structure from ACTUAL 5-minute OHLCV bars.
        # 5m MA20 = rolling mean of the last 20 five-minute closes (~100 trading minutes).
        ma20_5m = np.nan
        ma20_gap = np.nan
        ma20_slope = np.nan
        structure_score = 0.0
        closes_all = d["Close"].dropna()
        if len(closes_all) >= 20:
            ma20_series = closes_all.rolling(20).mean()
            ma20_5m = safe_float(ma20_series.iloc[-1])
            if math.isfinite(ma20_5m) and ma20_5m > 0:
                ma20_gap = pct(c, ma20_5m)
            # Compare current 5m MA20 with five bars earlier to measure short-cycle slope.
            if len(ma20_series.dropna()) >= 6:
                ma20_prev = safe_float(ma20_series.dropna().iloc[-6])
                if math.isfinite(ma20_prev) and ma20_prev > 0:
                    ma20_slope = pct(ma20_5m, ma20_prev)
            if math.isfinite(ma20_gap):
                if 0 <= ma20_gap <= 2.5: structure_score += 5
                elif ma20_gap < -1.0: structure_score -= 6
                elif ma20_gap > 4.0: structure_score -= 3
            if math.isfinite(ma20_slope):
                if ma20_slope > 0.15: structure_score += 4
                elif ma20_slope < -0.15: structure_score -= 4

        # Higher-high / higher-low check using two adjacent 3-bar windows near the latest price.
        # This is deliberately simple and transparent; it is not inferred from names or news.
        if len(d) >= 6 and "High" in d.columns and "Low" in d.columns:
            recent = d.dropna(subset=["High","Low"]).tail(6)
            if len(recent) == 6:
                h1 = safe_float(recent["High"].iloc[:3].max())
                h2 = safe_float(recent["High"].iloc[3:].max())
                l1 = safe_float(recent["Low"].iloc[:3].min())
                l2 = safe_float(recent["Low"].iloc[3:].min())
                if all(math.isfinite(x) for x in [h1,h2,l1,l2]):
                    if h2 > h1 and l2 > l1:
                        structure_score += 7
                    elif h2 < h1 and l2 < l1:
                        structure_score -= 7
                    elif l2 > l1:
                        structure_score += 2
                    elif l2 < l1:
                        structure_score -= 2

        score += structure_score

        # Close-auction / overnight features from 5-minute bars.
        closes = d["Close"].dropna()
        vols = d["Volume"].fillna(0) if "Volume" in d.columns else pd.Series(dtype=float)
        tail_ret = np.nan
        if len(closes) >= 7:
            tail_ret = pct(safe_float(closes.iloc[-1]), safe_float(closes.iloc[-7]))
        tail_vol_ratio = np.nan
        if len(vols) >= 12 and safe_float(vols.iloc[-6:].mean(), 0) >= 0:
            prior_mean = safe_float(vols.iloc[:-6].tail(18).mean(), np.nan)
            tail_mean = safe_float(vols.iloc[-6:].mean(), np.nan)
            if math.isfinite(prior_mean) and prior_mean > 0 and math.isfinite(tail_mean):
                tail_vol_ratio = tail_mean / prior_mean
        vwap = np.nan
        if "Volume" in d.columns and d["Volume"].fillna(0).sum() > 0:
            typical = (d["High"].fillna(d["Close"]) + d["Low"].fillna(d["Close"]) + d["Close"]) / 3.0
            vwap = safe_float((typical * d["Volume"].fillna(0)).sum() / d["Volume"].fillna(0).sum())
        vwap_gap = pct(c, vwap) if math.isfinite(vwap) else np.nan
        retention = np.nan
        if math.isfinite(base) and math.isfinite(hi) and hi > base:
            retention = (c - base) / (hi - base) * 100.0

        close_score = 0.0
        # Prefer a firm close, but avoid buying a stock that is already in uncontrolled acceleration.
        if math.isfinite(pos):
            if 72 <= pos <= 96: close_score += 10
            elif pos > 96: close_score += 5
            elif pos < 45: close_score -= 10
        if math.isfinite(tail_ret):
            if 0.15 <= tail_ret <= 1.8: close_score += 8
            elif -0.25 <= tail_ret < 0.15: close_score += 2
            elif tail_ret < -1.2: close_score -= 12
            elif tail_ret > 2.5: close_score -= 5
        if math.isfinite(vwap_gap):
            if 0 <= vwap_gap <= 3.0: close_score += 7
            elif vwap_gap < -1.0: close_score -= 8
            elif vwap_gap > 5.0: close_score -= 5
        if math.isfinite(tail_vol_ratio):
            if 1.05 <= tail_vol_ratio <= 2.8: close_score += 6
            elif tail_vol_ratio > 4.0: close_score -= 3
        if math.isfinite(retention):
            if 60 <= retention <= 105: close_score += 6
            elif retention < 30: close_score -= 8
        if math.isfinite(dp):
            if -1.0 <= dp <= 4.5: close_score += 5
            elif dp > 8.0: close_score -= 10
            elif dp < -3.5: close_score -= 9
        if math.isfinite(from_hi) and from_hi < -3.0:
            close_score -= 7

        rank.at[idx,"盘中现价"] = c
        rank.at[idx,"盘中涨跌%"] = dp
        rank.at[idx,"当日位置%"] = pos
        rank.at[idx,"距日高%"] = from_hi
        rank.at[idx,"盘中量价分"] = float(np.clip(score,-25,25))
        rank.at[idx,"5分MA20"] = ma20_5m
        rank.at[idx,"距5分MA20%"] = ma20_gap
        rank.at[idx,"5分MA20斜率%"] = ma20_slope
        rank.at[idx,"5分结构分"] = float(np.clip(structure_score,-15,15))
        rank.at[idx,"尾盘30分钟%"] = tail_ret
        rank.at[idx,"尾盘量能倍率"] = tail_vol_ratio
        rank.at[idx,"VWAP偏离%"] = vwap_gap
        rank.at[idx,"日内涨幅保留率%"] = retention
        rank.at[idx,"尾盘强度分"] = float(np.clip(close_score,-30,35))
    return rank


def mode_score(rank: pd.DataFrame, mode: str, budget: int):
    r = rank.copy()
    aff = r["现价"].apply(lambda x: affordability_score(x, budget))
    r["资金友好分"] = [x[0] for x in aff]
    r["一手资金"] = [x[1] for x in aff]
    r["预算可买一手"] = [x[2] for x in aff]
    news = r.get("新闻分", pd.Series(0.0, index=r.index)).astype(float)
    bg = r["背景分"].astype(float)
    trig = r["触发分"].astype(float)
    risk = r["风险总惩罚"].astype(float)
    pull = r["回调质量分"].astype(float)
    rr = r.get("空间盈亏比分", pd.Series(0.0, index=r.index)).astype(float)
    retain = r["涨幅保留分"].astype(float)
    cheap = r["资金友好分"].astype(float)

    if mode == "开盘前":
        # Yesterday's structure + news + affordable execution. Trigger is only a minor prior-session clue.
        score = 0.52*bg + 0.48*np.maximum(pull,0) + 0.16*trig + 0.55*rr + 0.75*news - 0.72*risk
        r["模式说明"] = "盘前：重背景/支撑/隔夜新闻，少依赖尚未发生的盘中触发"
    elif mode == "盘中":
        intra = r.get("盘中量价分", pd.Series(0.0,index=r.index)).astype(float)
        short_struct = r.get("5分结构分", pd.Series(0.0,index=r.index)).astype(float)
        score = 0.34*bg + 0.68*trig + 0.52*np.maximum(pull,0) + 0.42*rr + 0.82*intra + 0.55*short_struct + 0.45*news - 0.82*risk
        r["模式说明"] = "盘中：重实时转强/日内位置/量价，严惩追高和冲高回落"
    elif mode == "收盘前大引不成":
        close_strength = r.get("尾盘强度分", pd.Series(0.0,index=r.index)).astype(float)
        intra = r.get("盘中量价分", pd.Series(0.0,index=r.index)).astype(float)
        short_struct = r.get("5分结构分", pd.Series(0.0,index=r.index)).astype(float)
        # For overnight MOC, closing behavior dominates. Background must still be healthy; cheapness remains a tie-breaker.
        score = 0.36*bg + 0.28*trig + 0.36*np.maximum(pull,0) + 0.30*rr + 1.18*close_strength + 0.20*intra + 0.45*short_struct + 0.48*news - 0.90*risk
        # Extra hard penalties for weak close / late dump / excessive daily acceleration.
        dayp = r.get("盘中涨跌%", r.get("日涨跌%", pd.Series(np.nan,index=r.index))).astype(float)
        posi = r.get("当日位置%", pd.Series(np.nan,index=r.index)).astype(float)
        tail = r.get("尾盘30分钟%", pd.Series(np.nan,index=r.index)).astype(float)
        score = pd.Series(score, index=r.index)
        score.loc[(posi < 40) | (tail < -1.2)] -= 14
        score.loc[dayp > 9] -= 10
        score.loc[(r["结论"] == "回避")] -= 20
        r["大引不成资格"] = (
            r["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])
            & (r["背景分"] >= 20)
            & (r["风险总惩罚"] < 18)
            & (close_strength >= 12)
            & (posi >= 65)
            & (tail >= -0.30)
            & (dayp <= 8.0)
            & (dayp >= -2.5)
        )
        score.loc[~r["大引不成资格"]] -= 18
        r["模式说明"] = "收盘前大引不成：先低价限价埋伏，未成交则收盘集合竞价转市价；重尾盘承接/日内位置/VWAP/最后30分钟量价，只筛值得隔夜的票"
    else:
        # Closing quality / retention matters most for next-day watchlist.
        score = 0.43*bg + 0.38*trig + 0.55*np.maximum(pull,0) + 0.48*rr + 0.85*retain + 0.58*news - 0.76*risk
        r["模式说明"] = "收盘后：重收盘质量/涨幅留存/全天量价，筛明日候选"

    if "大引不成资格" not in r.columns:
        r["大引不成资格"] = False

    # Capital friendliness is a medium-strength tie-breaker for healthy candidates, never a rescue factor.
    healthy = r["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])
    score = pd.Series(score, index=r.index)
    score.loc[healthy] += cheap.loc[healthy]
    r["模式分"] = score.clip(-50,100)
    r = r.sort_values(["模式分","回调质量分","背景分","触发分","一手资金"], ascending=[False,False,False,False,True]).reset_index(drop=True)
    return r


def ticker(code: str) -> str:
    return f"{code}.T"


def safe_float(x, default=np.nan):
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def pct(a, b):
    if b is None or not math.isfinite(b) or b == 0 or a is None or not math.isfinite(a):
        return np.nan
    return (a / b - 1) * 100.0


@st.cache_data(ttl=120, show_spinner=False)
def download_daily(codes_tuple):
    symbols = [ticker(c) for c in codes_tuple]
    data = yf.download(
        tickers=symbols,
        period="4mo",
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        threads=True,
        progress=False,
        timeout=20,
    )
    return data


def extract_one_daily(batch: pd.DataFrame, code: str) -> pd.DataFrame:
    sym = ticker(code)
    try:
        if isinstance(batch.columns, pd.MultiIndex):
            if sym in batch.columns.get_level_values(0):
                df = batch[sym].copy()
            elif sym in batch.columns.get_level_values(1):
                df = batch.xs(sym, axis=1, level=1).copy()
            else:
                return pd.DataFrame()
        else:
            df = batch.copy()
        df = df.dropna(how="all")
        # Normalize possible lowercase/mixed labels.
        df.columns = [str(c).title() for c in df.columns]
        need = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
        return df[need].copy() if need else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def calc_rsi(close: pd.Series, n=14):
    d = close.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def analyze_daily(df: pd.DataFrame, code: str):
    # New IPOs may have fewer than 20 trading days. Do NOT silently drop them from the stock pool.
    # Five daily bars is the minimum for a basic short-term read; unavailable long-window metrics stay NaN
    # and are explicitly treated as "insufficient history" rather than invented.
    if df is None or df.empty or "Close" not in df.columns or len(df.dropna(subset=["Close"])) < 5:
        return None
    d = df.dropna(subset=["Close"]).copy()
    history_days = len(d)
    for col in ["Open","High","Low","Volume"]:
        if col not in d.columns:
            d[col] = np.nan
    close = d["Close"].astype(float)
    high = d["High"].astype(float)
    low = d["Low"].astype(float)
    vol = d["Volume"].astype(float)

    c = safe_float(close.iloc[-1])
    prev = safe_float(close.iloc[-2])
    ma5 = safe_float(close.rolling(5).mean().iloc[-1])
    ma20 = safe_float(close.rolling(20).mean().iloc[-1])
    ma60 = safe_float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else np.nan
    h20 = safe_float(high.tail(20).max())
    l20 = safe_float(low.tail(20).min())
    h60 = safe_float(high.tail(min(60, len(high))).max())
    l60 = safe_float(low.tail(min(60, len(low))).min())
    r1 = pct(c, prev)
    r5 = pct(c, safe_float(close.iloc[-6])) if len(close) >= 6 else np.nan
    r20 = pct(c, safe_float(close.iloc[-21])) if len(close) >= 21 else np.nan
    r60 = pct(c, safe_float(close.iloc[-61])) if len(close) >= 61 else np.nan
    vol5 = safe_float(vol.tail(5).mean())
    vol20 = safe_float(vol.tail(20).mean())
    volume_ratio = vol5 / vol20 if math.isfinite(vol5) and math.isfinite(vol20) and vol20 > 0 else np.nan
    last_vol_ratio = safe_float(vol.iloc[-1]) / vol20 if math.isfinite(vol20) and vol20 > 0 else np.nan
    rsi = safe_float(calc_rsi(close).iloc[-1])
    limit_down, limit_up, limit_width = jpx_normal_limit(prev)

    # Trend quality: rising moving averages and positive medium-term momentum.
    ma20_prev5 = safe_float(close.rolling(20).mean().iloc[-6]) if len(close) >= 26 else np.nan
    strong_score = 0
    if math.isfinite(r20): strong_score += np.clip(r20 / 12 * 18, -18, 18)
    if c > ma20: strong_score += 10
    if math.isfinite(ma5) and ma5 > ma20: strong_score += 8
    if math.isfinite(ma20_prev5) and ma20 > ma20_prev5: strong_score += 8
    if math.isfinite(r60): strong_score += np.clip(r60 / 25 * 8, -8, 8)

    # Key support is the highest of useful nearby supports, but not above price.
    supports = [x for x in [ma20, safe_float(low.tail(10).min()), safe_float(close.tail(10).min())] if math.isfinite(x) and x <= c]
    support = max(supports) if supports else l20
    support_gap = pct(c, support) if math.isfinite(support) else np.nan
    from_h20 = pct(c, h20)  # negative below high
    range_pos = (c - l20) / (h20 - l20) * 100 if math.isfinite(h20) and math.isfinite(l20) and h20 > l20 else np.nan

    # Pullback-hold: near MA/support, but not breaking it; reward healthy retreat from high.
    pullback_score = 0
    if math.isfinite(support_gap):
        if 0 <= support_gap <= 4: pullback_score += 16
        elif 4 < support_gap <= 8: pullback_score += 9
        elif support_gap < 0: pullback_score -= 18
    if math.isfinite(from_h20):
        draw = -from_h20
        if 2 <= draw <= 10: pullback_score += 12
        elif draw < 1: pullback_score += 2
        elif draw > 18: pullback_score -= 10

    # Re-strengthening confirmation.
    turn_score = 0
    prev_high = safe_float(high.iloc[-2])
    if c > prev_high: turn_score += 12
    if math.isfinite(r1) and r1 > 0: turn_score += min(r1 * 2.2, 9)
    if len(close) >= 3 and c > safe_float(close.iloc[-2]) > safe_float(close.iloc[-3]): turn_score += 7
    if math.isfinite(last_vol_ratio) and last_vol_ratio >= 1.15 and math.isfinite(r1) and r1 > 0: turn_score += min((last_vol_ratio - 1) * 8, 6)

    # Weakness / 'akippa-style' penalties.
    penalties = 0
    flags = []
    recent_lows = low.tail(8).dropna().values
    lower_low_count = int(sum(recent_lows[i] < recent_lows[i-1] for i in range(1, len(recent_lows))))
    is_new20_low = math.isfinite(l20) and safe_float(low.iloc[-1]) <= l20 * 1.002
    if is_new20_low:
        penalties += 25; flags.append("接近/刷新20日低点")
    if lower_low_count >= 5:
        penalties += 15; flags.append("近期低点持续下移")
    if math.isfinite(r5) and r5 < -5:
        penalties += min(abs(r5) * 1.3, 16); flags.append("5日趋势偏弱")
    if math.isfinite(r20) and r20 < -10:
        penalties += min(abs(r20) * 0.8, 16); flags.append("20日趋势偏弱")
    if math.isfinite(last_vol_ratio) and last_vol_ratio >= 1.5 and ((math.isfinite(r1) and r1 <= 0.5) or c < ma5):
        penalties += 12; flags.append("放量但价格没有同步走强")
    if math.isfinite(r1) and r1 >= 7:
        dist_ma5 = pct(c, ma5)
        if math.isfinite(dist_ma5) and dist_ma5 >= 5:
            penalties += 18; flags.append("突然暴拉且远离MA5，追高风险")

    safe_pullback_score = pullback_preference(r1, support_gap, from_h20, c, ma20)

    # Sustained structure: do not confuse a one-off vertical spike with a healthy trend.
    structure_score = structure_consistency(close, low, high)

    # Pullbacks are healthier when volume contracts; heavy-volume drops are riskier.
    pullback_volume_score = 0.0
    if math.isfinite(r1) and r1 < 0 and math.isfinite(last_vol_ratio):
        if last_vol_ratio <= 0.85:
            pullback_volume_score += 6
        elif last_vol_ratio >= 1.5:
            pullback_volume_score -= 7

    # Dedicated healthy-pullback score: this is intentionally more important than raw daily decline.
    pullback_quality = pullback_quality_score(
        r1, r5, support_gap, from_h20, c, ma20, last_vol_ratio, structure_score
    )
    rr_score, rr_ratio = reward_risk_proxy(from_h20, support_gap, pullback_quality)

    # Volatility / exhaustion risk.
    vol_penalty, atr_pct = volatility_risk(high, low, close)
    day_range = safe_float(high.iloc[-1] - low.iloc[-1])
    upper_wick_pct = ((safe_float(high.iloc[-1]) - c) / day_range * 100) if math.isfinite(day_range) and day_range > 0 else np.nan
    if math.isfinite(upper_wick_pct) and upper_wick_pct >= 55 and math.isfinite(r1) and r1 > 1:
        vol_penalty += 6
        flags.append("上影偏长，冲高承接一般")

    # Liquidity: avoid ranking very thin names too highly.
    avg_value20 = c * vol20 if math.isfinite(c) and math.isfinite(vol20) else np.nan
    liquidity_penalty = 0.0
    if math.isfinite(avg_value20):
        if avg_value20 < 100_000_000:
            liquidity_penalty = 10
            flags.append("日均成交额偏低")
        elif avg_value20 < 300_000_000:
            liquidity_penalty = 5

    # Rally-retention quality: strong names should keep at least part of their intraday gains instead of fully round-tripping every pop.
    retention_score, retention_pct, failed_pops = gain_retention_quality(high.tail(15), close.tail(15))
    if retention_score <= -8:
        flags.append("近期多次冲高回吐，涨幅留存差")

    # Background and trigger are intentionally separated.
    background_score = float(np.clip(
        strong_score * 0.52 + structure_score * 1.00 + pullback_score * 0.30
        + pullback_quality * 0.48 + rr_score * 0.55 + retention_score * 0.72,
        -30, 70
    ))
    trigger_score = float(np.clip(turn_score * 1.5 + max(0, pullback_quality) * 0.18, 0, 35))
    risk_penalty = float(penalties + vol_penalty + liquidity_penalty)
    technical = float(np.clip(background_score + trigger_score - risk_penalty, -50, 100))

    meta = STOCK_META.get(code, {})
    return {
        "代码": code,
        "历史交易日": history_days,
        "历史完整度": "完整" if history_days >= 22 else f"新股/短历史（{history_days}日）",
        "日文名": meta.get("jp", ""),
        "中文名": meta.get("zh", ""),
        "现价": c,
        "日涨跌%": r1,
        "5日%": r5,
        "20日%": r20,
        "60日%": r60,
        "MA5": ma5,
        "MA20": ma20,
        "20日高": h20,
        "20日低": l20,
        "60日高": h60,
        "60日低": l60,
        "距20日高%": from_h20,
        "区间位置%": range_pos,
        "量比20日": last_vol_ratio,
        "RSI14": rsi,
        "关键支撑": support,
        "距支撑%": support_gap,
        "强势分": float(strong_score),
        "回踩分": float(pullback_score),
        "转强分": float(turn_score),
        "安全回调分": float(safe_pullback_score),
        "回调质量分": float(pullback_quality),
        "空间盈亏比分": float(rr_score),
        "上方空间/支撑风险比": rr_ratio,
        "结构持续分": float(structure_score),
        "回调量价分": float(pullback_volume_score),
        "涨幅保留分": float(retention_score),
        "近10日冲高保留率%": retention_pct,
        "冲高失败次数": int(failed_pops),
        "背景分": float(background_score),
        "触发分": float(trigger_score),
        "ATR14%": atr_pct,
        "20日均成交额": avg_value20,
        "风险总惩罚": float(risk_penalty),
        "正常涨停价": limit_up,
        "正常跌停价": limit_down,
        "制限值幅": limit_width,
        "弱势惩罚": float(penalties),
        "技术总分": technical,
        "风险标签": "；".join(flags) if flags else "无明显弱势惩罚",
        "_df": d,
    }


def gain_retention_quality(high: pd.Series, close: pd.Series):
    """Measure whether intraday rallies are retained into the close over the last 10 sessions."""
    if len(close) < 12:
        return 0.0, np.nan, 0
    prev = close.shift(1)
    excursion = (high - prev) / prev
    close_gain = (close - prev) / prev
    mask = excursion >= 0.02  # only count sessions that actually rallied >=2% intraday
    fr = (close_gain[mask] / excursion[mask]).replace([np.inf, -np.inf], np.nan).dropna().tail(10)
    if fr.empty:
        return 0.0, np.nan, 0
    fr = fr.clip(-1.0, 1.2)
    avg = float(fr.mean())
    failed = int((fr <= 0.15).sum())
    if avg >= 0.65:
        score = 12.0
    elif avg >= 0.45:
        score = 7.0
    elif avg >= 0.25:
        score = 2.0
    elif avg < 0.05:
        score = -10.0
    else:
        score = -4.0
    if failed >= 3:
        score -= 5.0
    return float(np.clip(score, -15, 12)), avg * 100.0, failed




def render_take_profit_banner(tp, is_recommended=True, note=None):
    status = "推荐买点止盈计划" if is_recommended else "仅测算｜尚未触发A级买点"
    border = "#16a34a" if is_recommended else "#d97706"
    bg = "rgba(22,163,74,0.10)" if is_recommended else "rgba(217,119,6,0.10)"
    extra = f"<div style='margin-top:8px;font-size:0.92rem;opacity:.82'>{note}</div>" if note else ""
    st.markdown(f"""
    <div style="border:3px solid {border};background:{bg};border-radius:16px;padding:18px 20px;margin:14px 0 18px 0;">
      <div style="font-size:1.05rem;font-weight:800;margin-bottom:12px;">🎯 {status}</div>
      <div style="display:flex;gap:14px;flex-wrap:wrap;">
        <div style="flex:1;min-width:190px;background:rgba(255,255,255,.72);border-radius:12px;padding:14px;">
          <div style="font-size:.9rem;opacity:.75;">参考买入价</div>
          <div style="font-size:1.55rem;font-weight:800;">¥{tp['参考买入价']:.0f}</div>
        </div>
        <div style="flex:1;min-width:190px;background:rgba(255,255,255,.72);border-radius:12px;padding:14px;">
          <div style="font-size:.9rem;opacity:.75;">✅ 第一止盈</div>
          <div style="font-size:1.9rem;font-weight:900;">¥{tp['第一止盈']:.0f}</div>
          <div style="font-size:1rem;font-weight:700;">+{tp['第一止盈幅度%']:.1f}%</div>
        </div>
        <div style="flex:1;min-width:190px;background:rgba(255,255,255,.72);border-radius:12px;padding:14px;">
          <div style="font-size:.9rem;opacity:.75;">🚀 强势续抱目标</div>
          <div style="font-size:1.9rem;font-weight:900;">¥{tp['强势续抱目标']:.0f}</div>
          <div style="font-size:1rem;font-weight:700;">+{tp['第二目标幅度%']:.1f}%</div>
        </div>
      </div>
      {extra}
    </div>
    """, unsafe_allow_html=True)


def breakout_chase_score(row):
    """Strict breakout-chase gate using already-computed metrics.
    Allows true strong breakouts, rejects weak-stock fake pops.
    """
    score = 0.0
    reasons, risks = [], []

    r20 = safe_float(row.get("20日%", np.nan))
    r5 = safe_float(row.get("5日%", np.nan))
    from_h20 = safe_float(row.get("距20日高%", np.nan))
    retention = safe_float(row.get("近10日冲高保留率%", np.nan))
    failed = int(row.get("冲高失败次数", 0) or 0)
    weak_pen = safe_float(row.get("弱势惩罚", 0))
    risk_pen = safe_float(row.get("风险总惩罚", 0))
    close = safe_float(row.get("现价", np.nan))
    ma5 = safe_float(row.get("MA5", np.nan))
    ma20 = safe_float(row.get("MA20", np.nan))
    atr_pct = safe_float(row.get("ATR14%", np.nan))
    day_pct = safe_float(row.get("日涨跌%", np.nan))
    structure = safe_float(row.get("结构持续分", np.nan))
    trigger = safe_float(row.get("触发分", np.nan))

    flags = str(row.get("风险标签", ""))

    # Hard disqualifiers first.
    if "刷新20日低点" in flags or "近期低点持续下移" in flags:
        risks.append("近期低点结构弱")
    if "涨幅留存差" in flags:
        risks.append("冲高留存差")
    if weak_pen >= 12:
        risks.append("弱势惩罚过高")
    if math.isfinite(r20) and r20 < -5:
        risks.append("20日趋势偏弱")
    if math.isfinite(r5) and r5 < -4:
        risks.append("5日趋势偏弱")
    if math.isfinite(retention) and retention < 25:
        risks.append("冲高保留率过低")
    if failed >= 3:
        risks.append("近期冲高失败过多")

    # Trend / breakout quality.
    if math.isfinite(r20):
        if r20 >= 20:
            score += 18; reasons.append("20日趋势很强")
        elif r20 >= 8:
            score += 12; reasons.append("20日趋势偏强")
        elif r20 >= 0:
            score += 5

    if math.isfinite(close) and math.isfinite(ma5) and close >= ma5:
        score += 8; reasons.append("站上MA5")
    if math.isfinite(close) and math.isfinite(ma20) and close >= ma20:
        score += 8; reasons.append("站上MA20")

    if math.isfinite(from_h20):
        if -2 <= from_h20 <= 1.5:
            score += 15; reasons.append("接近/突破20日高点")
        elif -5 <= from_h20 < -2:
            score += 8

    if math.isfinite(structure):
        if structure >= 8:
            score += 10; reasons.append("结构持续性好")
        elif structure <= -5:
            score -= 8; risks.append("结构持续性差")

    if math.isfinite(trigger):
        if trigger >= 14:
            score += 10; reasons.append("已有转强触发")
        elif trigger < 5:
            score -= 4

    if math.isfinite(retention):
        if retention >= 70:
            score += 14; reasons.append("冲高后涨幅留存优秀")
        elif retention >= 50:
            score += 8
        elif retention < 30:
            score -= 14

    score -= min(12, failed * 4)

    # Risk controls: don't chase uncontrolled acceleration.
    if math.isfinite(day_pct):
        if day_pct > 12:
            score -= 14; risks.append("单日加速过猛")
        elif day_pct > 8:
            score -= 7
        elif day_pct < -3:
            score -= 6

    if math.isfinite(atr_pct):
        if atr_pct > 10:
            score -= 10; risks.append("ATR波动过高")
        elif atr_pct > 7:
            score -= 5

    hard_fail = (
        "近期低点结构弱" in risks
        or "冲高留存差" in risks
        or weak_pen >= 12
        or (math.isfinite(r20) and r20 < -5)
        or (math.isfinite(retention) and retention < 25)
        or failed >= 3
    )

    eligible = (score >= 45) and not hard_fail and risk_pen < 30
    return round(score, 1), bool(eligible), "；".join(reasons[:4]) if reasons else "—", "；".join(risks[:4]) if risks else "—"

def take_profit_targets(row, entry_price=None):
    """Dynamic informational profit-taking references, not a guarantee or order instruction."""
    current = safe_float(row.get("现价", np.nan))
    entry = safe_float(entry_price) if entry_price is not None else current
    if not math.isfinite(entry) or entry <= 0:
        entry = current
    atr_pct = safe_float(row.get("ATR14%", np.nan))
    atr_abs = entry * atr_pct / 100.0 if math.isfinite(atr_pct) else entry * 0.03
    atr_abs = max(atr_abs, entry * 0.015)
    h20 = safe_float(row.get("20日高", np.nan))
    h60 = safe_float(row.get("60日高", np.nan))
    limit_up = safe_float(row.get("正常涨停价", np.nan))

    # TP1: roughly 0.9 ATR / 2.5% above entry, but respect a nearby prior high as resistance.
    base1 = entry + max(0.9 * atr_abs, entry * 0.025)
    resist = sorted([x for x in [h20, h60] if math.isfinite(x) and x > entry * 1.01])
    tp1 = base1
    if resist and resist[0] < entry + 2.2 * atr_abs:
        tp1 = min(tp1, resist[0] * 0.995)
    tp1 = max(tp1, entry * 1.012)

    # TP2: let a strong trend run about 1.8 ATR / 6%, but never pretend it can exceed the normal daily limit from the current session.
    base2 = entry + max(1.8 * atr_abs, entry * 0.06)
    higher_resist = [x for x in resist if x > tp1 * 1.01]
    tp2 = base2
    if higher_resist and higher_resist[0] < entry + 3.2 * atr_abs:
        tp2 = min(tp2, higher_resist[0] * 0.995)
    if math.isfinite(limit_up):
        tp1 = min(tp1, limit_up * 0.995)
        tp2 = min(tp2, limit_up * 0.995)
    if tp2 <= tp1:
        tp2 = min(tp1 + max(0.8 * atr_abs, entry * 0.025), limit_up * 0.995 if math.isfinite(limit_up) else float("inf"))

    return {
        "参考买入价": entry,
        "第一止盈": float(tp1),
        "强势续抱目标": float(tp2),
        "第一止盈幅度%": pct(tp1, entry),
        "第二目标幅度%": pct(tp2, entry),
        "说明": "第一档优先考虑近期压力/约0.9ATR；若放量突破且不回落，再看第二档。遇到明显长上影、放量滞涨或跌回突破位，应重新评估，不机械死等目标价。",
    }


def fetch_news(code: str, max_items=6):
    # No API key. Public RSS; availability depends on network / Google response.
    meta = STOCK_META.get(code, {})
    jp = meta.get("jp", "")
    query = urllib.parse.quote(f"{code} {jp} 株 OR {code} {jp} 決算 OR {code} {jp} 提携 OR {code} {jp} 受注")
    url = f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall(".//item")[:max_items]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            out.append({"title": title, "link": link, "pubDate": pub})
        return out
    except Exception:
        return []


def score_news(items):
    if not items:
        return 0, "未抓到近期公开新闻"
    score = 0
    pos_hits, neg_hits = [], []
    for it in items:
        t = it["title"]
        for kw in POSITIVE_KW:
            if kw in t:
                score += 2.5
                pos_hits.append(kw)
        for kw in NEGATIVE_KW:
            if kw in t:
                score -= 4
                neg_hits.append(kw)
    score = float(np.clip(score, -15, 15))
    if pos_hits and not neg_hits:
        label = "有潜在正面催化词：" + "、".join(sorted(set(pos_hits))[:5])
    elif neg_hits:
        label = "存在风险新闻词：" + "、".join(sorted(set(neg_hits))[:5])
    else:
        label = "有新闻，但未识别到明确催化/风险关键词"
    return score, label


def force_news_check(code: str):
    """Always perform a news lookup for an explicitly inspected/recommended stock.
    Returns (score, display_label, items). Never returns an "unreviewed" placeholder.
    """
    items = fetch_news(code)
    if not items:
        return 0.0, "新闻获取失败或未找到近期匹配新闻", []
    ns, label = score_news(items)
    if label.startswith("有潜在正面催化词"):
        display = "已检索｜潜在正面催化｜" + label.split("：", 1)[-1]
    elif label.startswith("存在风险新闻词"):
        display = "已检索｜风险新闻｜" + label.split("：", 1)[-1]
    else:
        display = "已检索｜无明显催化/风险关键词"
    return float(ns), display, items


def classify(row):
    risk = row["风险标签"]
    if "刷新20日低点" in risk or (math.isfinite(row["20日%"] ) and row["20日%"] < -12):
        return "回避"
    if row["背景分"] >= 32 and row["触发分"] >= 14 and row["风险总惩罚"] < 18:
        return "A｜强背景+已触发"
    if row["背景分"] >= 30 and row["触发分"] < 14 and row["风险总惩罚"] < 18:
        return "B+｜好候选，等转强"
    if row["背景分"] >= 22 and row["风险总惩罚"] < 22:
        return "B｜观察"
    if row["技术总分"] >= 15:
        return "C｜中性"
    return "回避"


def add_news_to_candidates(df_rank: pd.DataFrame, n=12):
    records = df_rank.head(n).to_dict("records")
    news_map = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_news, r["代码"]): r["代码"] for r in records}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                items = fut.result()
            except Exception:
                items = []
            ns, label = score_news(items)
            news_map[code] = (ns, label, items)
    return news_map


def format_num(v, digits=1):
    return "—" if v is None or not math.isfinite(v) else f"{v:.{digits}f}"


def scan_all(codes, budget=300000):
    batch = download_daily(tuple(codes))
    rows = []
    raw = {}
    for c in codes:
        d = extract_one_daily(batch, c)
        a = analyze_daily(d, c)
        if a:
            raw[c] = a.pop("_df")
            rows.append(a)
    if not rows:
        return pd.DataFrame(), {}, {}
    base = pd.DataFrame(rows)
    base["新闻分"] = 0.0
    base["新闻判断"] = "—"
    # Capital friendliness is a tie-breaker only. It is added later only for non-weak candidates.
    aff = base["现价"].apply(lambda x: affordability_score(x, budget))
    base["资金友好分"] = [x[0] for x in aff]
    base["一手资金"] = [x[1] for x in aff]
    base["预算可买一手"] = [x[2] for x in aff]
    base["综合分"] = base["技术总分"]
    base = base.sort_values("综合分", ascending=False).reset_index(drop=True)

    news_map = add_news_to_candidates(base, n=min(15, len(base)))
    for idx, row in base.iterrows():
        c = row["代码"]
        if c in news_map:
            ns, label, _items = news_map[c]
            base.at[idx, "新闻分"] = ns
            base.at[idx, "新闻判断"] = label
            base.at[idx, "综合分"] = float(np.clip(base.at[idx, "技术总分"] + ns, -50, 100))
    base["结论"] = base.apply(classify, axis=1)
    bo = base.apply(lambda r: breakout_chase_score(r), axis=1)
    base["追强分"] = [x[0] for x in bo]
    base["追强资格"] = [x[1] for x in bo]
    base["追强理由"] = [x[2] for x in bo]
    base["追强风险"] = [x[3] for x in bo]

    # Only healthy/neutral candidates can receive the affordability bonus. Weak names never get rescued by low price.
    good_mask = base["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])
    base.loc[good_mask, "综合分"] = (base.loc[good_mask, "综合分"] + base.loc[good_mask, "资金友好分"]).clip(-50, 100)
    base = base.sort_values(["综合分", "背景分", "触发分", "一手资金"], ascending=[False, False, False, True]).reset_index(drop=True)
    return base, raw, news_map


def chart_for(code, raw_df, support=None):
    d = raw_df.tail(60).copy()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name=stock_label(code)))
    ma5 = d["Close"].rolling(5).mean()
    ma20 = d["Close"].rolling(20).mean()
    fig.add_trace(go.Scatter(x=d.index, y=ma5, mode="lines", name="MA5"))
    fig.add_trace(go.Scatter(x=d.index, y=ma20, mode="lines", name="MA20"))
    if support is not None and math.isfinite(support):
        fig.add_hline(y=support, line_dash="dash", annotation_text="关键支撑")
    fig.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=35,b=10))
    return fig



# ---------- One-click historical backtest / similarity calibration ----------
BT_FEATURES = [
    "ret1","ret5","ret20","dist_high20","dist_low20",
    "ma5_gap","ma20_gap","ma20_slope5","vol_ratio20",
    "atr14_pct","retention10","failed_pop10","structure6"
]
BT_WEIGHTS = {
    "ret1":0.7, "ret5":1.0, "ret20":1.15, "dist_high20":1.30, "dist_low20":0.75,
    "ma5_gap":0.75, "ma20_gap":1.0, "ma20_slope5":1.05, "vol_ratio20":0.80,
    "atr14_pct":1.0, "retention10":1.25, "failed_pop10":1.20, "structure6":1.10
}

@st.cache_data(ttl=21600, show_spinner=False)
def download_backtest_daily(codes_tuple):
    """Two years of adjusted daily OHLCV for technical backtesting.
    auto_adjust=True reduces split-related discontinuities in return features.
    """
    symbols = [ticker(c) for c in codes_tuple]
    return yf.download(
        tickers=symbols,
        period="2y",
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False,
        timeout=30,
    )

def _bt_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "Close" not in df.columns:
        return pd.DataFrame()
    d = df.copy().dropna(subset=["Close"])
    for col in ["Open","High","Low","Volume"]:
        if col not in d.columns:
            d[col] = np.nan
    c = d["Close"].astype(float)
    h = d["High"].astype(float)
    l = d["Low"].astype(float)
    v = d["Volume"].astype(float).fillna(0)

    f = pd.DataFrame(index=d.index)
    f["ret1"] = c.pct_change() * 100
    f["ret5"] = c.pct_change(5) * 100
    f["ret20"] = c.pct_change(20) * 100

    ma5 = c.rolling(5).mean()
    ma20 = c.rolling(20).mean()
    f["ma5_gap"] = (c / ma5 - 1) * 100
    f["ma20_gap"] = (c / ma20 - 1) * 100
    f["ma20_slope5"] = (ma20 / ma20.shift(5) - 1) * 100

    h20 = h.rolling(20).max()
    l20 = l.rolling(20).min()
    f["dist_high20"] = (c / h20 - 1) * 100
    f["dist_low20"] = (c / l20 - 1) * 100
    f["vol_ratio20"] = v / v.rolling(20).mean().replace(0, np.nan)

    prev_c = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev_c).abs(), (l-prev_c).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    f["atr14_pct"] = atr14 / c * 100

    # Rally retention: when intraday high rose >=2% versus prior close,
    # measure how much of that excursion survived into the close.
    excursion = (h / prev_c - 1) * 100
    close_gain = (c / prev_c - 1) * 100
    daily_retention = pd.Series(np.nan, index=d.index)
    rally_mask = excursion >= 2.0
    daily_retention.loc[rally_mask] = (close_gain.loc[rally_mask] / excursion.loc[rally_mask] * 100).clip(-100, 120)
    f["retention10"] = daily_retention.rolling(10, min_periods=2).mean()

    failed = ((excursion >= 2.0) & (daily_retention <= 15)).astype(float)
    f["failed_pop10"] = failed.rolling(10, min_periods=5).sum()

    # Compact price-structure feature: compare recent 3-bar highs/lows with prior 3 bars.
    hi_recent = h.rolling(3).max()
    lo_recent = l.rolling(3).min()
    hi_prev = hi_recent.shift(3)
    lo_prev = lo_recent.shift(3)
    f["structure6"] = (
        np.where((hi_recent > hi_prev) & (lo_recent > lo_prev), 1.0,
        np.where((hi_recent < hi_prev) & (lo_recent < lo_prev), -1.0,
        np.where(lo_recent > lo_prev, 0.35, np.where(lo_recent < lo_prev, -0.35, 0.0))))
        * 10.0
    )

    # Future outcomes. These are labels only and are never used as current features.
    f["next1_close"] = (c.shift(-1) / c - 1) * 100
    f["next1_high"] = (h.shift(-1) / c - 1) * 100
    f["next1_low"] = (l.shift(-1) / c - 1) * 100
    future_high3 = pd.concat([h.shift(-1), h.shift(-2), h.shift(-3)], axis=1).max(axis=1)
    future_low3 = pd.concat([l.shift(-1), l.shift(-2), l.shift(-3)], axis=1).min(axis=1)
    f["next3_high"] = (future_high3 / c - 1) * 100
    f["next3_low"] = (future_low3 / c - 1) * 100
    f["next3_close"] = (c.shift(-3) / c - 1) * 100

    # "Continuation" and "fake breakout" are deliberately symmetric risk labels.
    f["continued3"] = ((f["next3_high"] >= 4.0) & (f["next3_close"] > 0)).astype(float)
    f["fake3"] = ((f["next3_low"] <= -5.0) | (f["next3_close"] <= -3.0)).astype(float)
    return f.replace([np.inf, -np.inf], np.nan)

def build_backtest_cases(batch: pd.DataFrame, codes):
    cases = []
    for code in codes:
        d = extract_one_daily(batch, code)
        if d.empty:
            continue
        f = _bt_feature_frame(d)
        if f.empty:
            continue
        f = f.copy()
        f["代码"] = code
        f["日期"] = f.index
        # Need at least a basic 20-day structure and known future labels.
        valid = f["next3_close"].notna() & f["ret5"].notna()
        f = f.loc[valid]
        if not f.empty:
            cases.append(f.reset_index(drop=True))
    if not cases:
        return pd.DataFrame()
    out = pd.concat(cases, ignore_index=True)
    # Keep finite-ish rows with enough usable feature dimensions.
    usable = out[BT_FEATURES].notna().sum(axis=1) >= 8
    return out.loc[usable].reset_index(drop=True)

def _robust_center_scale(cases: pd.DataFrame):
    med = cases[BT_FEATURES].median()
    q75 = cases[BT_FEATURES].quantile(0.75)
    q25 = cases[BT_FEATURES].quantile(0.25)
    scale = (q75 - q25) / 1.349
    std = cases[BT_FEATURES].std()
    scale = scale.where(scale > 1e-9, std)
    scale = scale.where(scale > 1e-9, 1.0)
    return med, scale

def _similar_cases(cases, target, med, scale, code=None, peer=False, limit=120):
    if cases is None or cases.empty:
        return pd.DataFrame()
    cols = [c for c in BT_FEATURES if c in target and math.isfinite(safe_float(target.get(c)))]
    if len(cols) < 6:
        return pd.DataFrame()

    base = cases.copy()
    if code is not None and not peer:
        base = base[base["代码"] == code]
    if base.empty:
        return base

    # Robust standardized weighted distance, using only dimensions available in each sample.
    dist_num = pd.Series(0.0, index=base.index)
    dist_den = pd.Series(0.0, index=base.index)
    for c in cols:
        zt = (safe_float(target[c]) - safe_float(med[c], 0)) / safe_float(scale[c], 1)
        z = (base[c] - med[c]) / scale[c]
        ok = z.notna()
        w = BT_WEIGHTS.get(c, 1.0)
        dist_num.loc[ok] += w * (z.loc[ok] - zt) ** 2
        dist_den.loc[ok] += w
    base = base.assign(_dims=(dist_den > 0).astype(int), _dist=np.sqrt(dist_num / dist_den.replace(0, np.nan)))
    base = base[base["_dist"].notna()].sort_values("_dist")

    if peer:
        # Prevent one long-listed stock from dominating the peer sample.
        base = base.groupby("代码", group_keys=False).head(5).sort_values("_dist")
    return base.head(limit).copy()

def _bt_stats(sample: pd.DataFrame):
    if sample is None or sample.empty:
        return None
    s = sample.copy()
    n = len(s)

    # Small-sample shrinkage toward neutral rather than pretending 3 cases are certainty.
    alpha = 5.0
    p_up1 = ((s["next1_close"] > 0).sum() + alpha) / (n + 2*alpha)
    p_cont = (s["continued3"].sum() + alpha) / (n + 2*alpha)
    p_fake = (s["fake3"].sum() + alpha) / (n + 2*alpha)

    def clipped_mean(col):
        x = s[col].dropna()
        if x.empty:
            return np.nan
        lo, hi = x.quantile(0.02), x.quantile(0.98)
        return float(x.clip(lo, hi).mean())

    return {
        "n": n,
        "p_up1": float(p_up1),
        "p_cont3": float(p_cont),
        "p_fake3": float(p_fake),
        "next1_close_mean": clipped_mean("next1_close"),
        "next1_high_med": safe_float(s["next1_high"].median()),
        "next1_low_med": safe_float(s["next1_low"].median()),
        "next3_high_med": safe_float(s["next3_high"].median()),
        "next3_low_med": safe_float(s["next3_low"].median()),
    }

def _current_bt_target(df):
    f = _bt_feature_frame(df)
    if f.empty:
        return {}
    row = f.iloc[-1]
    return {c: safe_float(row.get(c)) for c in BT_FEATURES}

def calibrate_one(code, raw_df, cases, med, scale):
    target = _current_bt_target(raw_df)
    if not target:
        return None
    own = _similar_cases(cases, target, med, scale, code=code, peer=False, limit=45)
    peers = _similar_cases(cases, target, med, scale, code=code, peer=True, limit=140)
    own_s, peer_s = _bt_stats(own), _bt_stats(peers)
    if peer_s is None:
        return None

    own_n = own_s["n"] if own_s else 0
    # Long-lived stocks get up to 35% self-history weight; IPOs automatically rely on peers.
    self_w = min(0.35, max(0.0, own_n / 60.0 * 0.35))
    peer_w = 1.0 - self_w

    def blend(k):
        if own_s is None or not math.isfinite(safe_float(own_s.get(k))):
            return safe_float(peer_s.get(k))
        return self_w * safe_float(own_s[k]) + peer_w * safe_float(peer_s[k])

    p_up = blend("p_up1")
    p_cont = blend("p_cont3")
    p_fake = blend("p_fake3")
    n1c = blend("next1_close_mean")
    n1h = blend("next1_high_med")
    n1l = blend("next1_low_med")
    n3h = blend("next3_high_med")
    n3l = blend("next3_low_med")

    raw_cal = (p_up - 0.50) * 28 + (p_cont - p_fake) * 26
    if math.isfinite(n1c):
        raw_cal += np.clip(n1c, -3, 3) * 1.2
    cal = float(np.clip(raw_cal, -12, 12))

    if peer_s["n"] >= 40 and p_fake >= 0.52 and p_cont <= 0.40:
        status = "🔴 历史警戒"
    elif peer_s["n"] >= 40 and p_fake >= 0.44:
        status = "🟡 假突破风险偏高"
    elif peer_s["n"] >= 40 and p_cont >= 0.52 and p_fake <= 0.32 and p_up >= 0.52:
        status = "🟢 历史结构偏强"
    else:
        status = "⚪ 历史中性"

    return {
        "历史校准分": cal,
        "历史状态": status,
        "自身样本": own_n,
        "相似样本": peer_s["n"],
        "自身权重%": self_w * 100,
        "次日上涨概率%": p_up * 100,
        "3日延续概率%": p_cont * 100,
        "3日假突破风险%": p_fake * 100,
        "相似样本次日平均收盘%": n1c,
        "相似样本次日高点中位%": n1h,
        "相似样本次日低点中位%": n1l,
        "相似样本3日高点中位%": n3h,
        "相似样本3日低点中位%": n3l,
    }

def run_one_click_backtest(raw_map):
    hist = download_backtest_daily(tuple(STOCK_CODES))
    cases = build_backtest_cases(hist, STOCK_CODES)
    if cases.empty:
        return {}, 0
    med, scale = _robust_center_scale(cases)
    out = {}
    for code in STOCK_CODES:
        df = raw_map.get(code)
        if df is None or df.empty:
            # Use latest two-year history itself as current source if 4mo scan missed the name.
            df = extract_one_daily(hist, code)
        r = calibrate_one(code, df, cases, med, scale)
        if r:
            out[code] = r
    return out, len(cases)

def apply_backtest_calibration(rank: pd.DataFrame, bt_map: dict):
    r = rank.copy()
    defaults = {
        "历史校准分":0.0, "历史状态":"未回测", "自身样本":0, "相似样本":0, "自身权重%":0.0,
        "次日上涨概率%":np.nan, "3日延续概率%":np.nan, "3日假突破风险%":np.nan,
        "相似样本次日平均收盘%":np.nan, "相似样本次日高点中位%":np.nan,
        "相似样本次日低点中位%":np.nan, "相似样本3日高点中位%":np.nan,
        "相似样本3日低点中位%":np.nan
    }
    for k,v in defaults.items():
        r[k] = v

    for idx,row in r.iterrows():
        b = bt_map.get(str(row["代码"])) if bt_map else None
        if not b:
            continue
        for k,v in b.items():
            r.at[idx,k] = v

    # Calibration is deliberately capped: history can tilt a decision, not overrule live price/news.
    healthy = r["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])
    r.loc[healthy, "模式分"] = (r.loc[healthy, "模式分"] + r.loc[healthy, "历史校准分"]).clip(-50,100)
    red = r["历史状态"].eq("🔴 历史警戒")
    r.loc[red, "模式分"] = (r.loc[red, "模式分"] - 8).clip(-50,100)
    if "追强资格" in r.columns:
        r.loc[red, "追强资格"] = False
    r["综合分"] = r["模式分"]
    return r.sort_values(["模式分","回调质量分","背景分","触发分","一手资金"], ascending=[False,False,False,False,True]).reset_index(drop=True)




# ---------- Automatic Night PTS ingestion ----------
# Yahoo! Finance Japan displays Japannext J-Market night PTS on individual stock pages.
# This is a public webpage rather than a formal market-data API, so failure must degrade to "no signal",
# never to invented data.
YAHOO_QUOTE_URL = "https://finance.yahoo.co.jp/quote/{code}.T"

def _html_to_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    s = re.sub(r"(?is)<script.*?</script>", " ", raw_html)
    s = re.sub(r"(?is)<style.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = s.replace("−", "-").replace("▲", "").replace("▼", "")
    return re.sub(r"\s+", " ", s).strip()

def _parse_pts_timestamp(md_hm: str):
    """Parse strings like 10/7 20:11 into JST, handling year rollover."""
    try:
        now = datetime.now(JST)
        m = re.search(r"(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", md_hm or "")
        if not m:
            return None
        month, day, hour, minute = map(int, m.groups())
        dt = datetime(now.year, month, day, hour, minute, tzinfo=JST)
        if dt > now + timedelta(days=2):
            dt = dt.replace(year=now.year - 1)
        return dt
    except Exception:
        return None

def _current_pts_session_start(now=None):
    """Return the start of the PTS session relevant to the next TSE session.
    17:00-23:59 => today 17:00
    00:00-08:59 => yesterday 17:00
    09:00-16:59 => no relevant live overnight session for next-day scoring yet.
    """
    now = now or datetime.now(JST)
    if now.hour >= 17:
        return now.replace(hour=17, minute=0, second=0, microsecond=0)
    if now.hour < 9:
        prev = now - timedelta(days=1)
        return prev.replace(hour=17, minute=0, second=0, microsecond=0)
    return None

def _num(s):
    try:
        return float(str(s).replace(",", "").replace("+", "").strip())
    except Exception:
        return np.nan

def _parse_yahoo_pts_html(code: str, raw_html: str):
    t = _html_to_text(raw_html)
    if not t or "夜間PTS" not in t:
        return None

    # Prefer the compact header: 夜間PTS 751 東証終値比 0(0.00%) 10/6 20:11
    p = re.search(
        r"夜間PTS\s*([0-9,]+(?:\.[0-9]+)?)\s*東証終値比\s*([+\-]?[0-9,]+(?:\.[0-9]+)?)\s*"
        r"\(([+\-]?[0-9.]+)%\)\s*(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})",
        t
    )

    # Fallback to the detail line: 取引値 / 東証終値比 ...
    if not p:
        p = re.search(
            r"取引値\s*/\s*東証終値比\s*([0-9,]+(?:\.[0-9]+)?)\s*([+\-]?[0-9,]+(?:\.[0-9]+)?)\s*"
            r"\(([+\-]?[0-9.]+)%\).*?(\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})",
            t
        )

    if not p:
        return None

    price = _num(p.group(1))
    change = _num(p.group(2))
    change_pct = _num(p.group(3))
    stamp_text = p.group(4)
    stamp = _parse_pts_timestamp(stamp_text)

    # Slice from the PTS explanatory/detail section to avoid accidentally reading TSE volume.
    detail_pos = t.find("夜間PTSについて")
    detail = t[detail_pos:] if detail_pos >= 0 else t[t.find("夜間PTS"):]
    vm = re.search(r"出来高\s*([0-9,]+)\s*株", detail)
    tm = re.search(r"売買代金\s*([0-9,]+)\s*千円", detail)
    volume = int(_num(vm.group(1))) if vm and math.isfinite(_num(vm.group(1))) else 0
    turnover_yen = _num(tm.group(1)) * 1000 if tm else (price * volume if math.isfinite(price) else np.nan)

    om = re.search(r"始値\s*([0-9,]+(?:\.[0-9]+)?)", detail)
    hm = re.search(r"高値\s*([0-9,]+(?:\.[0-9]+)?)", detail)
    lm = re.search(r"安値\s*([0-9,]+(?:\.[0-9]+)?)", detail)

    return {
        "代码": code,
        "PTS价格": price,
        "PTS涨跌": change,
        "PTS涨跌%": change_pct,
        "PTS时间": stamp.strftime("%m/%d %H:%M") if stamp else stamp_text,
        "PTS_dt": stamp,
        "PTS成交量": volume,
        "PTS成交额": turnover_yen,
        "PTS始值": _num(om.group(1)) if om else np.nan,
        "PTS高值": _num(hm.group(1)) if hm else np.nan,
        "PTS低值": _num(lm.group(1)) if lm else np.nan,
        "PTS来源": "Yahoo! Finance Japan / Japannext J-Market",
    }

def _fetch_pts_one(code: str):
    try:
        url = YAHOO_QUOTE_URL.format(code=code)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.6",
        }
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return None
        r.encoding = r.apparent_encoding or r.encoding
        return _parse_yahoo_pts_html(code, r.text)
    except Exception:
        return None

@st.cache_data(ttl=120, show_spinner=False)
def fetch_pts_universe(codes_tuple):
    """Fetch night PTS for the whole pool concurrently.
    Cached for 2 minutes to avoid repeatedly hitting public pages.
    """
    out = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_pts_one, c): c for c in codes_tuple}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                x = fut.result()
                if x:
                    out[code] = x
            except Exception:
                pass
    return out

def _pts_confidence(pts_turnover_yen, avg_daily_turnover_yen):
    """Liquidity confidence from PTS turnover relative to normal daily turnover.
    Tiny PTS prints receive almost no weight.
    """
    p = safe_float(pts_turnover_yen)
    d = safe_float(avg_daily_turnover_yen)
    if not math.isfinite(p) or p <= 0:
        return 0.0
    if math.isfinite(d) and d > 0:
        ratio = p / d
        # 0.05% daily value = nearly noise; ~2%+ = meaningful overnight participation.
        conf = np.clip((math.log10(max(ratio, 1e-6)) + 3.3) / 1.6, 0.05, 1.0)
    else:
        # Absolute fallback when average turnover is unavailable.
        if p < 300_000:
            conf = 0.05
        elif p < 2_000_000:
            conf = 0.20
        elif p < 10_000_000:
            conf = 0.45
        elif p < 50_000_000:
            conf = 0.70
        else:
            conf = 1.0
    return float(conf)

def apply_pts_features(rank: pd.DataFrame, pts_map: dict, mode: str):
    """Attach PTS fields and cautiously adjust next-session scores.
    PTS matters only in '收盘后预测明天' and '开盘前', and only for the currently relevant PTS session.
    """
    r = rank.copy()
    defaults = {
        "PTS价格":np.nan, "PTS涨跌%":np.nan, "PTS成交量":0, "PTS成交额":np.nan,
        "PTS时间":"—", "PTS可信度%":0.0, "PTS调整分":0.0, "PTS状态":"无有效PTS",
    }
    for k,v in defaults.items():
        r[k] = v

    session_start = _current_pts_session_start()
    active_for_scoring = mode in ["收盘后预测明天", "开盘前"] and session_start is not None

    for idx, row in r.iterrows():
        code = str(row["代码"])
        p = (pts_map or {}).get(code)
        if not p:
            continue

        for k in ["PTS价格","PTS涨跌%","PTS成交量","PTS成交额","PTS时间"]:
            r.at[idx, k] = p.get(k, defaults.get(k))

        stamp = p.get("PTS_dt")
        fresh = bool(stamp and session_start and stamp >= session_start)
        conf = _pts_confidence(p.get("PTS成交额"), row.get("20日均成交额"))
        r.at[idx, "PTS可信度%"] = conf * 100

        if not active_for_scoring:
            r.at[idx, "PTS状态"] = "已取得｜当前时段不计分"
            continue
        if not fresh:
            r.at[idx, "PTS状态"] = "PTS过期/非本轮夜盘｜不计分"
            continue

        pctv = safe_float(p.get("PTS涨跌%"))
        if not math.isfinite(pctv):
            r.at[idx, "PTS状态"] = "已取得但涨跌不可用"
            continue

        # Cap both the move and its influence. PTS is a supporting signal, not the main engine.
        adj = float(np.clip(pctv, -8, 8) * conf * 0.75)

        # Extra caution when a huge move comes from tiny turnover.
        if abs(pctv) >= 5 and conf < 0.20:
            adj *= 0.25
            status = "低成交PTS异动｜仅弱参考"
        elif conf >= 0.65:
            status = "PTS有效｜高可信"
        elif conf >= 0.30:
            status = "PTS有效｜中可信"
        else:
            status = "PTS有效｜低可信"

        r.at[idx, "PTS调整分"] = adj
        r.at[idx, "PTS状态"] = status

    if active_for_scoring:
        r["模式分"] = (r["模式分"] + r["PTS调整分"]).clip(-50, 100)
        r["综合分"] = r["模式分"]
        r = r.sort_values(
            ["模式分","回调质量分","背景分","触发分","一手资金"],
            ascending=[False,False,False,False,True]
        ).reset_index(drop=True)
    return r



# ---------- Overseas / cross-market catalyst layer ----------
# The factor set is intentionally broad. The program does NOT assume every Japanese stock
# cares about every factor. It estimates each stock's own recent lead relationship and only
# uses factors with enough samples and non-trivial correlation.
GLOBAL_FACTORS = {
    "SOX": {"symbol":"^SOX", "kind":"US", "label":"PHLX半导体", "tz":"America/New_York"},
    "Nasdaq100": {"symbol":"QQQ", "kind":"US", "label":"Nasdaq100", "tz":"America/New_York"},
    "SMH": {"symbol":"SMH", "kind":"US", "label":"美股半导体ETF", "tz":"America/New_York"},
    "NVDA": {"symbol":"NVDA", "kind":"US", "label":"NVIDIA", "tz":"America/New_York"},
    "Micron": {"symbol":"MU", "kind":"US", "label":"Micron", "tz":"America/New_York"},
    "SK hynix": {"symbol":"000660.KS", "kind":"KR", "label":"SK hynix", "tz":"Asia/Seoul"},
    "Samsung": {"symbol":"005930.KS", "kind":"KR", "label":"Samsung电子", "tz":"Asia/Seoul"},
    "BTC": {"symbol":"BTC-USD", "kind":"24H", "label":"Bitcoin", "tz":"UTC"},
    "Copper": {"symbol":"HG=F", "kind":"EXTENDED", "label":"铜", "tz":"America/New_York"},
    "Gold": {"symbol":"GC=F", "kind":"EXTENDED", "label":"黄金", "tz":"America/New_York"},
    "Oil": {"symbol":"CL=F", "kind":"EXTENDED", "label":"WTI原油", "tz":"America/New_York"},
    "USDJPY": {"symbol":"JPY=X", "kind":"EXTENDED", "label":"美元/日元", "tz":"UTC"},
    "US10Y": {"symbol":"^TNX", "kind":"US", "label":"美国10年期收益率", "tz":"America/New_York"},
    "US Financials": {"symbol":"XLF", "kind":"US", "label":"美股金融", "tz":"America/New_York"},
    "US Defense": {"symbol":"ITA", "kind":"US", "label":"美股军工", "tz":"America/New_York"},
}

@st.cache_data(ttl=300, show_spinner=False)
def download_global_factors():
    symbols = [v["symbol"] for v in GLOBAL_FACTORS.values()]
    try:
        return yf.download(
            tickers=symbols,
            period="8mo",
            interval="1d",
            auto_adjust=True,
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=25,
        )
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=90, show_spinner=False)
def download_global_factors_intraday():
    """Latest free overseas factor data.
    5-minute bars, including US pre/post market when Yahoo provides them.
    Cache is intentionally short so repeated full analyses stay reasonably fresh.
    """
    symbols = [v["symbol"] for v in GLOBAL_FACTORS.values()]
    try:
        return yf.download(
            tickers=symbols,
            period="5d",
            interval="5m",
            prepost=True,
            auto_adjust=True,
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=25,
        )
    except Exception:
        return pd.DataFrame()

def _extract_factor_df(batch, symbol):
    try:
        if batch is None or batch.empty:
            return pd.DataFrame()
        if isinstance(batch.columns, pd.MultiIndex):
            if symbol not in batch.columns.get_level_values(0):
                return pd.DataFrame()
            d = batch[symbol].copy()
        else:
            d = batch.copy()
        if "Close" not in d.columns:
            return pd.DataFrame()
        d = d.dropna(subset=["Close"]).copy()
        return d
    except Exception:
        return pd.DataFrame()

def _factor_return_series(batch, factor_name):
    meta = GLOBAL_FACTORS[factor_name]
    d = _extract_factor_df(batch, meta["symbol"])
    if d.empty:
        return pd.DataFrame()
    x = pd.DataFrame(index=pd.to_datetime(d.index).tz_localize(None))
    x["factor_ret"] = d["Close"].astype(float).pct_change() * 100
    x = x.dropna()
    return x

def _lead_pair(stock_df, factor_ret_df):
    """Map each Japan trading day to the most recent *prior* overseas factor session.
    This avoids accidentally using same-day future information in historical correlation.
    """
    if stock_df is None or stock_df.empty or factor_ret_df is None or factor_ret_df.empty:
        return pd.DataFrame()
    s = stock_df.dropna(subset=["Close"]).copy()
    if len(s) < 35:
        return pd.DataFrame()
    sidx = pd.to_datetime(s.index).tz_localize(None)
    sr = pd.DataFrame({
        "date": sidx,
        "stock_ret": s["Close"].astype(float).pct_change().values * 100
    }).dropna().sort_values("date")
    fr = factor_ret_df.reset_index().rename(columns={factor_ret_df.index.name or "index":"fdate"})
    if "fdate" not in fr.columns:
        fr = fr.rename(columns={fr.columns[0]:"fdate"})
    fr["fdate"] = pd.to_datetime(fr["fdate"]).dt.tz_localize(None)
    fr = fr.sort_values("fdate")
    paired = pd.merge_asof(
        sr,
        fr,
        left_on="date",
        right_on="fdate",
        direction="backward",
        allow_exact_matches=False,
    )
    paired = paired.dropna(subset=["stock_ret","factor_ret"])
    return paired.tail(100)

def _winsor(s, q=0.03):
    if s is None or len(s) < 8:
        return s
    lo, hi = s.quantile(q), s.quantile(1-q)
    return s.clip(lo, hi)

def _factor_relation(stock_df, factor_ret_df):
    paired = _lead_pair(stock_df, factor_ret_df)
    if paired.empty or len(paired) < 35:
        return None
    x = _winsor(paired["factor_ret"].astype(float))
    y = _winsor(paired["stock_ret"].astype(float))
    # Spearman = Pearson correlation of ranks.
    # Do this explicitly so Streamlit does not require scipy.stats.
    xr = x.rank(method="average")
    yr = y.rank(method="average")
    corr = xr.corr(yr)
    if corr is None or not math.isfinite(float(corr)):
        return None
    n = len(paired)
    # Reliability requires both enough history and a relationship meaningfully above noise.
    abs_c = abs(float(corr))
    rel = min(1.0, n / 70.0) * max(0.0, min(1.0, (abs_c - 0.15) / 0.35))
    return {"corr":float(corr), "n":int(n), "reliability":float(rel)}


def _to_utc_timestamp(ts, tz_name="UTC"):
    try:
        x = pd.Timestamp(ts)
        if x.tzinfo is None:
            x = x.tz_localize(tz_name)
        return x.tz_convert("UTC")
    except Exception:
        return None

def _previous_daily_close(daily_df, latest_utc, tz_name):
    if daily_df is None or daily_df.empty or latest_utc is None:
        return np.nan
    c = daily_df["Close"].astype(float).dropna()
    if c.empty:
        return np.nan
    try:
        local_date = latest_utc.tz_convert(tz_name).date()
    except Exception:
        local_date = latest_utc.date()

    dated = []
    for idx, val in c.items():
        try:
            d = pd.Timestamp(idx)
            if d.tzinfo is not None:
                d = d.tz_convert(tz_name).tz_localize(None)
            dated.append((d.date(), float(val)))
        except Exception:
            continue
    prior = [v for d,v in dated if d < local_date]
    if prior:
        return prior[-1]
    # Last-resort fallback: second-last daily bar is safer than today's partial daily bar.
    if len(c) >= 2:
        return float(c.iloc[-2])
    return float(c.iloc[-1])

def _latest_factor_snapshot(daily_batch, intraday_batch, factor_name):
    """Latest available 5-minute factor snapshot.
    Returns None instead of pretending stale/missing data is current.
    """
    meta = GLOBAL_FACTORS[factor_name]
    intr = _extract_factor_df(intraday_batch, meta["symbol"])
    daily = _extract_factor_df(daily_batch, meta["symbol"])
    if intr.empty or "Close" not in intr.columns:
        return None

    c5 = intr["Close"].astype(float).dropna()
    if c5.empty:
        return None

    latest_price = float(c5.iloc[-1])
    latest_utc = _to_utc_timestamp(c5.index[-1], meta.get("tz","UTC"))
    if latest_utc is None:
        return None

    now_utc = pd.Timestamp.now(tz="UTC")
    age_min = max(0.0, float((now_utc - latest_utc).total_seconds() / 60.0))

    ref = _previous_daily_close(daily, latest_utc, meta.get("tz","UTC"))
    if not math.isfinite(ref) or ref <= 0:
        return None

    ret = (latest_price / ref - 1) * 100

    dc = daily["Close"].astype(float).dropna() if not daily.empty and "Close" in daily.columns else pd.Series(dtype=float)
    hist_ret = dc.pct_change().dropna() * 100
    vol = float(hist_ret.tail(60).std()) if len(hist_ret) >= 15 else (float(hist_ret.std()) if len(hist_ret) >= 5 else np.nan)
    if math.isfinite(vol) and vol > 1e-9:
        z = float(np.clip(ret / vol, -3.5, 3.5))
    else:
        z = float(np.clip(ret / 2.0, -3.5, 3.5))

    try:
        local_ts = latest_utc.tz_convert(meta.get("tz","UTC"))
        time_text = local_ts.strftime("%m/%d %H:%M")
    except Exception:
        time_text = latest_utc.strftime("%m/%d %H:%M UTC")

    return {
        "ret":float(ret),
        "z":z,
        "date":latest_utc,
        "age_min":age_min,
        "kind":meta["kind"],
        "label":meta["label"],
        "time_text":time_text,
        "latest_price":latest_price,
        "interval":"5m",
    }

def _latest_jp_date(raw_map):
    dates = []
    for d in (raw_map or {}).values():
        if d is not None and not d.empty:
            try:
                idx = pd.to_datetime(d.index[-1])
                if getattr(idx, "tzinfo", None) is not None:
                    idx = idx.tz_localize(None)
                dates.append(idx.normalize())
            except Exception:
                pass
    return max(dates) if dates else None

def _age_freshness(age_min, kind, mode):
    """Freshness from actual bar age, not merely date labels."""
    if not math.isfinite(safe_float(age_min)):
        return 0.0
    a = float(age_min)

    if kind in ["24H", "EXTENDED"]:
        if a <= 15: return 1.0
        if a <= 45: return 0.90
        if a <= 120: return 0.70
        if a <= 360: return 0.45
        if a <= 720: return 0.20
        return 0.0

    if kind == "KR":
        if mode in ["盘中", "收盘前大引不成"]:
            if a <= 15: return 0.85
            if a <= 45: return 0.70
            if a <= 120: return 0.40
            return 0.0
        # Korea is mostly peer breadth for next-session analysis.
        if a <= 180: return 0.40
        if a <= 720: return 0.22
        return 0.0

    if kind == "US":
        if mode in ["开盘前", "收盘后预测明天"]:
            # Fresh US regular/pre/post data can be several hours old by Japan morning
            # and still be the newest information for the next TSE open.
            if a <= 30: return 1.0
            if a <= 120: return 0.95
            if a <= 360: return 0.90
            if a <= 720: return 0.75
            if a <= 1080: return 0.45
            return 0.0
        # During Japan trading, last night's US move is mostly already in the opening price.
        if a <= 180: return 0.25
        return 0.0

    return 0.0

def _global_freshness(snapshot, last_jp_date, mode):
    if snapshot is None:
        return 0.0
    return _age_freshness(snapshot.get("age_min", np.nan), snapshot.get("kind"), mode)

def compute_global_catalysts(raw_map, mode):
    """Estimate stock-specific overseas catalyst scores.
    The stock itself chooses its relevant factors via recent historical lead correlation.
    """
    batch = download_global_factors()
    intraday_batch = download_global_factors_intraday()
    if batch is None or batch.empty:
        return {}

    factor_returns = {}
    snapshots = {}
    for name in GLOBAL_FACTORS:
        factor_returns[name] = _factor_return_series(batch, name)
        snapshots[name] = _latest_factor_snapshot(batch, intraday_batch, name)

    last_jp_date = _latest_jp_date(raw_map)
    out = {}

    for code, stock_df in (raw_map or {}).items():
        candidates = []
        for name in GLOBAL_FACTORS:
            rel = _factor_relation(stock_df, factor_returns[name])
            snap = snapshots[name]
            if rel is None or snap is None:
                continue

            fresh = _global_freshness(snap, last_jp_date, mode)
            if fresh <= 0:
                continue

            # Dynamic contribution:
            # signed lead correlation × current standardized factor move × reliability × freshness.
            raw_contrib = rel["corr"] * snap["z"] * rel["reliability"] * fresh * 3.2
            contrib = float(np.clip(raw_contrib, -3.0, 3.0))

            # Ignore trivial signals; they add clutter but no information.
            if abs(contrib) < 0.18:
                continue

            candidates.append({
                "name":name,
                "label":snap["label"],
                "corr":rel["corr"],
                "n":rel["n"],
                "reliability":rel["reliability"],
                "factor_ret":snap["ret"],
                "z":snap["z"],
                "freshness":fresh,
                "age_min":snap.get("age_min", np.nan),
                "time_text":snap.get("time_text","—"),
                "contrib":contrib,
            })

        # Keep only the strongest distinct signals, positive or negative.
        candidates = sorted(candidates, key=lambda x: abs(x["contrib"]), reverse=True)[:3]
        total = float(np.clip(sum(x["contrib"] for x in candidates), -8.0, 8.0))
        if candidates:
            detail = "；".join(
                f"{x['label']} {x['factor_ret']:+.2f}% / 相关{x['corr']:+.2f} / {x['contrib']:+.1f}分 / 更新{x['time_text']}({x['age_min']:.0f}分钟前)"
                for x in candidates
            )
            if total >= 2:
                status = "🟢 海外催化偏正面"
            elif total <= -2:
                status = "🔴 海外催化偏负面"
            else:
                status = "⚪ 海外催化中性"
        else:
            detail = "未发现足够可靠且新鲜的海外关联信号"
            status = "⚪ 海外催化中性"

        newest = min([safe_float(x.get("age_min")) for x in candidates if math.isfinite(safe_float(x.get("age_min")))], default=np.nan)
        latest_time = candidates[0].get("time_text","—") if candidates else "—"
        out[str(code)] = {
            "海外催化分":total,
            "海外催化状态":status,
            "海外催化明细":detail,
            "海外有效因子数":len(candidates),
            "海外最新数据时间":latest_time,
            "海外最新数据年龄分钟":newest,
        }
    return out

def apply_global_catalysts(rank: pd.DataFrame, catalyst_map: dict, mode: str):
    r = rank.copy()
    for c, default in [
        ("海外催化分",0.0),
        ("海外催化状态","⚪ 海外催化中性"),
        ("海外催化明细","未运行"),
        ("海外有效因子数",0),
        ("海外最新数据时间","—"),
        ("海外最新数据年龄分钟",np.nan),
    ]:
        r[c] = default

    for idx, row in r.iterrows():
        d = (catalyst_map or {}).get(str(row["代码"]))
        if not d:
            continue
        for k,v in d.items():
            r.at[idx,k] = v

    # Overseas data can matter in all four modes, but it matters most before the next session.
    # During Japan trading, already-known US overnight moves are heavily freshness-discounted,
    # while live Korea / FX / crypto / futures can still contribute modestly.
    if mode in ["开盘前", "收盘后预测明天"]:
        adj = r["海外催化分"].astype(float).clip(-8,8)
    else:
        adj = r["海外催化分"].astype(float).clip(-4,4)
    r["模式分"] = (r["模式分"].astype(float) + adj).clip(-50,100)
    r["综合分"] = r["模式分"]
    r = r.sort_values(
        ["模式分","回调质量分","背景分","触发分","一手资金"],
        ascending=[False,False,False,False,True]
    ).reset_index(drop=True)
    return r



# ---------- V20.1: frozen Top5 predictions / pullback plans / optional persistent memory ----------
MODEL_VERSION = "V20.1.1"

def prediction_validation_rule(mode: str) -> str:
    return {
        "开盘前": "验证当日开盘后→收盘；记录最高/最低/收盘、是否到止盈/失效位",
        "盘中": "只验证预测时间之后→当日收盘；预测前高点不算成绩",
        "收盘前大引不成": "验证下一交易日；记录最高/最低/收盘、止盈/失效",
        "收盘后预测明天": "验证下一交易日；记录最高/最低/收盘、止盈/失效",
    }.get(mode, "按下一交易阶段验证")

def pullback_buy_plan(row):
    """Create a pre-committed pullback zone using only information already visible now.
    This is especially useful for true breakout names that are strong but too extended to chase blindly.
    """
    current = safe_float(row.get("盘中现价", np.nan))
    if not math.isfinite(current):
        current = safe_float(row.get("现价", np.nan))
    if not math.isfinite(current) or current <= 0:
        return {"类型":"无数据","回踩下沿":np.nan,"回踩上沿":np.nan,"回踩中心":np.nan,"失效位":np.nan,"说明":"—"}

    atr_pct = safe_float(row.get("ATR14%", np.nan))
    atr_abs = current * atr_pct / 100.0 if math.isfinite(atr_pct) and atr_pct > 0 else current * 0.035
    atr_abs = max(atr_abs, current * 0.015)

    support = safe_float(row.get("关键支撑", np.nan))
    ma5 = safe_float(row.get("MA5", np.nan))
    ma20 = safe_float(row.get("MA20", np.nan))
    dayp = safe_float(row.get("盘中涨跌%", row.get("日涨跌%", np.nan)))
    chase_ok = bool(row.get("追强资格", False))
    chase_score = safe_float(row.get("追强分", np.nan))
    bg = safe_float(row.get("背景分", np.nan))
    pull = safe_float(row.get("回调质量分", np.nan))

    is_breakout = chase_ok or (math.isfinite(chase_score) and chase_score >= 42) or (
        math.isfinite(dayp) and dayp >= 6 and math.isfinite(bg) and bg >= 25
    )

    # Candidate structural anchors already below price.
    anchors = []
    for name, v in [("MA5", ma5), ("关键支撑", support), ("MA20", ma20)]:
        if math.isfinite(v) and current * 0.82 <= v < current * 0.998:
            anchors.append((name, v))

    if is_breakout:
        # Do not require a strong stock to become "cheap"; target a normal 0.25~0.70 ATR digestion.
        floor = current - 0.70 * atr_abs
        ceiling = current - 0.25 * atr_abs
        structural = max([v for _,v in anchors], default=current - 0.45 * atr_abs)
        center = min(ceiling, max(floor, structural))
        low = center - 0.12 * atr_abs
        high = center + 0.12 * atr_abs
        plan_type = "强势突破回踩"
        note = "真突破/高位强势票：不因价格高自动否决，优先等正常回踩而不是盲目追最高点"
    else:
        # For normal pullback candidates, lean closer to support/short MA.
        structural = max([v for _,v in anchors], default=current - 0.30 * atr_abs)
        center = min(current - 0.10 * atr_abs, max(current - 0.55 * atr_abs, structural))
        low = center - 0.10 * atr_abs
        high = center + 0.10 * atr_abs
        plan_type = "回调埋伏" if math.isfinite(pull) and pull >= 10 else "观察回踩"
        note = "普通候选：回踩区间只作预先计划，不能等跌破结构后再改口说是低吸"

    if math.isfinite(support):
        low = max(low, support * 0.995)
        # Invalidation is intentionally below the support visible at prediction time.
        invalid = support - 0.22 * atr_abs
    else:
        invalid = center - 0.85 * atr_abs

    # Keep zone logical and below current.
    high = min(high, current * 0.997)
    low = min(low, high)
    center = (low + high) / 2.0

    return {
        "类型":plan_type,
        "回踩下沿":float(low),
        "回踩上沿":float(high),
        "回踩中心":float(center),
        "失效位":float(invalid),
        "说明":note,
    }

def build_top5_snapshot(rank: pd.DataFrame, mode: str, run_id: str, analysis_time: str) -> pd.DataFrame:
    rows = []
    for pos, (_, r) in enumerate(rank.head(5).iterrows(), start=1):
        price = safe_float(r.get("盘中现价", np.nan))
        if not math.isfinite(price):
            price = safe_float(r.get("现价", np.nan))
        tp = take_profit_targets(r, price if math.isfinite(price) else None)
        pb = pullback_buy_plan(r)

        # Freeze the important features too, so tomorrow's explanation cannot silently change.
        frozen = {
            "背景分": safe_float(r.get("背景分")),
            "触发分": safe_float(r.get("触发分")),
            "回调质量分": safe_float(r.get("回调质量分")),
            "安全回调分": safe_float(r.get("安全回调分")),
            "空间盈亏比分": safe_float(r.get("空间盈亏比分")),
            "ATR14%": safe_float(r.get("ATR14%")),
            "5日%": safe_float(r.get("5日%")),
            "20日%": safe_float(r.get("20日%")),
            "距20日高%": safe_float(r.get("距20日高%")),
            "距支撑%": safe_float(r.get("距支撑%")),
            "量比20日": safe_float(r.get("量比20日")),
            "结构持续分": safe_float(r.get("结构持续分")),
            "近10日冲高保留率%": safe_float(r.get("近10日冲高保留率%")),
            "冲高失败次数": safe_float(r.get("冲高失败次数")),
            "风险总惩罚": safe_float(r.get("风险总惩罚")),
            "追强资格": bool(r.get("追强资格", False)),
            "追强分": safe_float(r.get("追强分")),
            "资金友好分": safe_float(r.get("资金友好分")),
            "一手资金": safe_float(r.get("一手资金")),
            "PTS涨跌%": safe_float(r.get("PTS涨跌%")),
            "PTS可信度%": safe_float(r.get("PTS可信度%")),
            "海外催化分": safe_float(r.get("海外催化分")),
            "历史校准分": safe_float(r.get("历史校准分")),
            "次日上涨概率%": safe_float(r.get("次日上涨概率%")),
            "3日延续概率%": safe_float(r.get("3日延续概率%")),
            "3日假突破风险%": safe_float(r.get("3日假突破风险%")),
        }

        rows.append({
            "模型版本": MODEL_VERSION,
            "run_id": run_id,
            "预测时间": analysis_time,
            "模式": mode,
            "验证规则": prediction_validation_rule(mode),
            "排名": pos,
            "代码": str(r.get("代码","")),
            "日文名": str(r.get("日文名","")),
            "中文名": str(r.get("中文名","")),
            "预测价格": price,
            "综合分": safe_float(r.get("综合分")),
            "结论": str(r.get("结论","")),
            "风险": str(r.get("风险标签","")),
            "新闻": str(r.get("新闻判断","")),
            "海外催化": str(r.get("海外催化状态","")),
            "历史状态": str(r.get("历史状态","")),
            "买入计划类型": pb["类型"],
            "回踩买入下沿": pb["回踩下沿"],
            "回踩买入上沿": pb["回踩上沿"],
            "回踩买入中心": pb["回踩中心"],
            "失效位": pb["失效位"],
            "第一止盈": safe_float(tp.get("第一止盈")),
            "强势目标": safe_float(tp.get("强势续抱目标")),
            "冻结指标JSON": json.dumps(frozen, ensure_ascii=False, allow_nan=False) if all(
                not (isinstance(v, float) and math.isnan(v)) for v in frozen.values()
            ) else json.dumps({k:(None if isinstance(v,float) and math.isnan(v) else v) for k,v in frozen.items()}, ensure_ascii=False),
        })
    return pd.DataFrame(rows)

def _db_secret():
    """Prefer Supabase's current server-side secret key; support legacy service_role during migration."""
    try:
        return st.secrets.get("SUPABASE_SECRET_KEY") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    except Exception:
        return None

def _db_url():
    try:
        return st.secrets.get("SUPABASE_URL")
    except Exception:
        return None

def supabase_configured():
    return bool(_db_url() and _db_secret())

def save_predictions_supabase(snapshot: pd.DataFrame):
    if snapshot is None or snapshot.empty or not supabase_configured():
        return False, "未配置Supabase"
    base = str(_db_url()).rstrip("/")
    key = str(_db_secret())
    url = base + "/rest/v1/predictions?on_conflict=run_id,rank_no"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    def num(v):
        x = safe_float(v)
        return float(x) if math.isfinite(x) else None

    payload = []
    for _, r in snapshot.iterrows():
        payload.append({
            "model_version": str(r["模型版本"]),
            "run_id": str(r["run_id"]),
            "analysis_time": str(r["预测时间"]),
            "mode": str(r["模式"]),
            "validation_rule": str(r["验证规则"]),
            "rank_no": int(r["排名"]),
            "code": str(r["代码"]),
            "jp_name": str(r["日文名"]),
            "cn_name": str(r["中文名"]),
            "price": num(r["预测价格"]),
            "score": num(r["综合分"]),
            "grade": str(r["结论"]),
            "risk": str(r["风险"]),
            "news": str(r["新闻"]),
            "global_catalyst": str(r["海外催化"]),
            "history_state": str(r["历史状态"]),
            "plan_type": str(r["买入计划类型"]),
            "buy_zone_low": num(r["回踩买入下沿"]),
            "buy_zone_high": num(r["回踩买入上沿"]),
            "buy_zone_center": num(r["回踩买入中心"]),
            "invalidation": num(r["失效位"]),
            "tp1": num(r["第一止盈"]),
            "tp2": num(r["强势目标"]),
            "features": json.loads(str(r["冻结指标JSON"])),
        })
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if 200 <= resp.status_code < 300:
            return True, "已保存"
        return False, f"HTTP {resp.status_code}: {resp.text[:160]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def load_recent_predictions_supabase(limit=100):
    if not supabase_configured():
        return pd.DataFrame()
    base = str(_db_url()).rstrip("/")
    key = str(_db_secret())
    url = base + f"/rest/v1/predictions?select=*&order=analysis_time.desc,rank_no.asc&limit={int(limit)}"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if 200 <= resp.status_code < 300:
            return pd.DataFrame(resp.json())
    except Exception:
        pass
    return pd.DataFrame()



# ---------- V20.1: upload yesterday's frozen CSV and grade it automatically ----------
def _parse_jst_time(s):
    try:
        s = str(s).replace(" JST","")
        ts = pd.Timestamp(s)
        if ts.tzinfo is None:
            ts = ts.tz_localize("Asia/Tokyo")
        else:
            ts = ts.tz_convert("Asia/Tokyo")
        return ts
    except Exception:
        return None

def _next_jp_trading_day(code: str, after_date):
    ticker = f"{code}.T" if str(code).isdigit() else f"{code}.T"
    try:
        d = yf.download(ticker, start=str(pd.Timestamp(after_date).date()),
                        end=str((pd.Timestamp(after_date) + pd.Timedelta(days=10)).date()),
                        interval="1d", auto_adjust=False, progress=False, threads=False)
        if d is None or d.empty:
            return None
        idx = pd.to_datetime(d.index)
        for x in idx:
            if pd.Timestamp(x).date() > pd.Timestamp(after_date).date():
                return pd.Timestamp(x).date()
    except Exception:
        return None
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_daily_for_verify(code: str, start_date: str, end_date: str):
    ticker = f"{code}.T"
    try:
        d = yf.download(ticker, start=start_date, end=end_date,
                        interval="1d", auto_adjust=False,
                        progress=False, threads=False, timeout=20)
        if isinstance(d.columns, pd.MultiIndex):
            # yfinance may return ticker level even for one symbol
            try:
                d.columns = d.columns.get_level_values(0)
            except Exception:
                pass
        return d
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_for_verify(code: str, period="10d"):
    ticker = f"{code}.T"
    try:
        d = yf.download(ticker, period=period, interval="5m",
                        auto_adjust=False, progress=False,
                        threads=False, timeout=20)
        if isinstance(d.columns, pd.MultiIndex):
            try:
                d.columns = d.columns.get_level_values(0)
            except Exception:
                pass
        return d
    except Exception:
        return pd.DataFrame()

def _one_day_ohlc(daily_df, target_date):
    if daily_df is None or daily_df.empty:
        return None
    idx = pd.to_datetime(daily_df.index)
    mask = [pd.Timestamp(x).date() == pd.Timestamp(target_date).date() for x in idx]
    if not any(mask):
        return None
    row = daily_df.loc[mask].iloc[0]
    def g(k):
        try:
            v = row[k]
            if hasattr(v, "iloc"):
                v = v.iloc[0]
            return float(v)
        except Exception:
            return np.nan
    return {"open":g("Open"), "high":g("High"), "low":g("Low"), "close":g("Close")}

def _intraday_after_prediction(code, pred_ts):
    d = fetch_intraday_for_verify(code, "10d")
    if d is None or d.empty:
        return None
    idx = pd.to_datetime(d.index)
    # yfinance JP intraday index is usually tz-aware; normalize to JST
    try:
        if idx.tz is None:
            idx = idx.tz_localize("Asia/Tokyo")
        else:
            idx = idx.tz_convert("Asia/Tokyo")
    except Exception:
        pass
    d = d.copy()
    d.index = idx
    same = d[(d.index.date == pred_ts.date()) & (d.index >= pred_ts)]
    if same.empty:
        return None
    def col(name):
        s = same[name]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:,0]
        return pd.to_numeric(s, errors="coerce")
    return {
        "open": float(col("Open").dropna().iloc[0]),
        "high": float(col("High").max()),
        "low": float(col("Low").min()),
        "close": float(col("Close").dropna().iloc[-1]),
    }

def grade_prediction_row(r):
    code = str(r.get("代码","")).strip()
    mode = str(r.get("模式","")).strip()
    pred_ts = _parse_jst_time(r.get("预测时间",""))
    price = safe_float(r.get("预测价格"))
    tp1 = safe_float(r.get("第一止盈"))
    tp2 = safe_float(r.get("强势目标"))
    invalid = safe_float(r.get("失效位"))
    buy_low = safe_float(r.get("回踩买入下沿"))
    buy_high = safe_float(r.get("回踩买入上沿"))

    if pred_ts is None or not code or not math.isfinite(price) or price <= 0:
        return {"验证状态":"无法验证","验证说明":"预测时间/代码/预测价格缺失"}

    if mode == "盘中":
        ohlc = _intraday_after_prediction(code, pred_ts)
        eval_date = pred_ts.date()
    else:
        if mode == "开盘前":
            eval_date = pred_ts.date()
        else:
            eval_date = _next_jp_trading_day(code, pred_ts.date())

        if eval_date is None:
            return {"验证状态":"未到验证日","验证说明":"下一交易日尚无可用行情"}

        start = str(pd.Timestamp(eval_date).date())
        end = str((pd.Timestamp(eval_date) + pd.Timedelta(days=2)).date())
        daily = fetch_daily_for_verify(code, start, end)
        ohlc = _one_day_ohlc(daily, eval_date)

    if not ohlc:
        return {"验证状态":"未到验证日/无行情","验证说明":"Yahoo暂未返回对应交易日行情"}

    high, low, close, opn = ohlc["high"], ohlc["low"], ohlc["close"], ohlc["open"]
    max_up = (high / price - 1) * 100 if math.isfinite(high) else np.nan
    max_down = (low / price - 1) * 100 if math.isfinite(low) else np.nan
    close_ret = (close / price - 1) * 100 if math.isfinite(close) else np.nan

    buy_touch = (
        math.isfinite(buy_low) and math.isfinite(buy_high) and
        math.isfinite(low) and math.isfinite(high) and
        low <= buy_high and high >= buy_low
    )
    tp1_hit = math.isfinite(tp1) and math.isfinite(high) and high >= tp1
    tp2_hit = math.isfinite(tp2) and math.isfinite(high) and high >= tp2
    invalid_hit = math.isfinite(invalid) and math.isfinite(low) and low <= invalid

    # Pre-committed grading, no after-the-fact explanations.
    if invalid_hit and not tp1_hit:
        result = "❌ 失败"
    elif tp1_hit and not invalid_hit:
        result = "✅ 成功"
    elif tp1_hit and invalid_hit:
        result = "🟡 路径混乱"
    elif math.isfinite(close_ret) and close_ret >= 2:
        result = "✅ 偏成功"
    elif math.isfinite(close_ret) and close_ret <= -3:
        result = "❌ 偏失败"
    else:
        result = "🟡 一般"

    rebound = np.nan
    if math.isfinite(low) and low > 0 and math.isfinite(close):
        rebound = (close / low - 1) * 100

    return {
        "验证状态":"已验证",
        "验证日期":str(eval_date),
        "实际开盘":opn,
        "实际最高":high,
        "实际最低":low,
        "实际收盘":close,
        "最大浮盈%":max_up,
        "最大浮亏%":max_down,
        "收盘收益%":close_ret,
        "回踩买入区间触及":bool(buy_touch),
        "第一止盈命中":bool(tp1_hit),
        "强势目标命中":bool(tp2_hit),
        "失效位触及":bool(invalid_hit),
        "低点后收盘反弹%":rebound,
        "判卷结果":result,
        "验证说明":"按冻结预测参数自动判卷",
    }

def verify_prediction_csv(uploaded_file):
    try:
        data = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        df = pd.read_csv(io.BytesIO(data), dtype={"代码":str})
    except Exception as e:
        return None, f"CSV读取失败：{type(e).__name__}"

    required = ["预测时间","模式","排名","代码","预测价格","第一止盈","强势目标","失效位"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return None, "不是V20/V20.1预测CSV，缺少：" + "、".join(missing)

    results = []
    for _, row in df.iterrows():
        base = row.to_dict()
        base.update(grade_prediction_row(row))
        results.append(base)
    return pd.DataFrame(results), None


# ---------- UI ----------
st.title("🎲 四时段强势回踩资金友好大师 V20.1")

st.caption("开盘前 / 盘中 / 收盘前大引不成 / 收盘后预测明天 · 四套侧重不同的评分 · 股票池固定 72 只 · 一键2年历史回测/相似结构校准 · 夜间PTS自动参考（Yahoo/Japannext） · 免费行情可能延迟")

with st.expander("先看核心纪律（网站会强制执行）", expanded=True):
    for x in RULES:
        st.markdown(f"- **{x}**")

colA, colB, colC = st.columns([1.2, 1, 1])
with colA:
    st.metric("股票池", f"{len(STOCK_CODES)} 只")
with colB:
    st.metric("重复代码", f"{len(STOCK_CODES)-len(set(STOCK_CODES))} 个")
with colC:
    st.metric("数据刷新", datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))

st.warning("这不是自动下单系统。免费公开行情可能延迟或缺失；推荐结果是筛选/排序，不是收益保证。尤其盘中快速波动时，请用券商盘口确认价格后再行动。")
st.caption("身份显示统一为：代码｜日文名｜中文译名。行情仍按代码.T抓取；代码与公司名分开保存，避免把名字当代码或串票。新股历史不足20日时仍保留在股票池与诊断中，缺失的MA20/20日指标显示为不可用，不会凭空补数。")

if "scan" not in st.session_state:
    st.session_state.scan = None
if "raw" not in st.session_state:
    st.session_state.raw = None
if "news" not in st.session_state:
    st.session_state.news = None
if "bt_map" not in st.session_state:
    st.session_state.bt_map = None
if "bt_case_count" not in st.session_state:
    st.session_state.bt_case_count = 0
if "bt_time" not in st.session_state:
    st.session_state.bt_time = None
if "pts_map" not in st.session_state:
    st.session_state.pts_map = None
if "pts_fetch_time" not in st.session_state:
    st.session_state.pts_fetch_time = None
if "global_catalysts" not in st.session_state:
    st.session_state.global_catalysts = None
if "global_fetch_time" not in st.session_state:
    st.session_state.global_fetch_time = None
if "global_mode" not in st.session_state:
    st.session_state.global_mode = None
if "analysis_run_id" not in st.session_state:
    st.session_state.analysis_run_id = None
if "analysis_time" not in st.session_state:
    st.session_state.analysis_time = None
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = None
if "prediction_snapshots" not in st.session_state:
    st.session_state.prediction_snapshots = {}
if "prediction_saved_runs" not in st.session_state:
    st.session_state.prediction_saved_runs = set()

st.markdown("### 🕒 分析时段")
mode = st.radio("你现在是在什么时候选股？", ["开盘前", "盘中", "收盘前大引不成", "收盘后预测明天"], horizontal=True)
st.info(MODE_DESCRIPTIONS[mode])

st.markdown("### 💴 资金偏好")
budget = st.slider("单只股票最多愿意占用多少一手资金？", 100000, 1000000, 300000, 50000, format="¥%d")
st.caption("资金权重已提高到中等：质量接近时，100股占用资金更少的票会明显占优；但便宜不会救活弱票。")


if st.button("🧠 全自动分析", type="primary", use_container_width=True):
    _now = datetime.now(JST)
    st.session_state.analysis_time = _now.strftime("%Y-%m-%d %H:%M:%S JST")
    st.session_state.analysis_run_id = f"{_now.strftime('%Y%m%dT%H%M%S')}_{mode}"
    st.session_state.analysis_mode = mode
    with st.spinner("正在自动扫描行情、新闻、PTS、技术结构、历史回测和相似案例，并生成最终结论…"):
        # 1) Current market scan
        rank0, raw0, news0 = scan_all(STOCK_CODES, budget)

        # 2) Intraday structure when relevant
        if mode in ["盘中", "收盘前大引不成"]:
            intra0 = download_intraday(tuple(STOCK_CODES))
            rank0 = apply_intraday_features(rank0, intra0)

        st.session_state.scan = rank0
        st.session_state.raw = raw0
        st.session_state.news = news0
        st.session_state.scan_mode = mode

        # 3) Night PTS, only when relevant for next-session decisions
        if mode in ["收盘后预测明天", "开盘前"] and _current_pts_session_start() is not None:
            st.session_state.pts_map = fetch_pts_universe(tuple(STOCK_CODES))
            st.session_state.pts_fetch_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
        else:
            st.session_state.pts_map = None
            st.session_state.pts_fetch_time = None

        # 4) Overseas / Korean / crypto / macro catalyst layer.
        # The model first checks each stock's own historical relationship, then only uses
        # factors that are both relevant and fresh for the next Japanese session.
        st.session_state.global_catalysts = compute_global_catalysts(raw0 or {}, mode)
        st.session_state.global_fetch_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
        st.session_state.global_mode = mode

        # 5) One-click historical backtest + similarity calibration
        bt_map, bt_n = run_one_click_backtest(raw0 or {})
        st.session_state.bt_map = bt_map
        st.session_state.bt_case_count = bt_n
        st.session_state.bt_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

st.caption(
    f"当前模式：{mode}。每次点击『全自动分析』都会生成并冻结本模式Top5：当时价格、回踩买入区间、止盈、失效位和关键指标都一起记录，方便之后按真实走势验算。"
)

rank = st.session_state.scan
raw_map = st.session_state.raw or {}
news_map = st.session_state.news or {}

if rank is not None and not rank.empty:
    rank = rank.copy()
    # If user changed mode after scanning, reuse daily scan and fetch intraday only when needed.
    if mode in ["盘中", "收盘前大引不成"] and "盘中量价分" not in rank.columns:
        intra = download_intraday(tuple(STOCK_CODES))
        rank = apply_intraday_features(rank, intra)
    if st.session_state.get("global_mode") != mode:
        st.session_state.global_catalysts = compute_global_catalysts(raw_map, mode)
        st.session_state.global_mode = mode
    rank = mode_score(rank, mode, budget)
    # Night PTS is automatically incorporated when a relevant overnight session is active.
    if mode in ["收盘后预测明天", "开盘前"] and _current_pts_session_start() is not None:
        if st.session_state.pts_map is None:
            st.session_state.pts_map = fetch_pts_universe(tuple(STOCK_CODES))
            st.session_state.pts_fetch_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
        rank = apply_pts_features(rank, st.session_state.pts_map or {}, mode)
    else:
        rank = apply_pts_features(rank, {}, mode)

    # Overseas catalyst is stock-specific and dynamic; no fixed "tech stock = Nasdaq" shortcut.
    if st.session_state.global_catalysts is None:
        st.session_state.global_catalysts = compute_global_catalysts(raw_map, mode)
        st.session_state.global_fetch_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    rank = apply_global_catalysts(rank, st.session_state.global_catalysts or {}, mode)

    if st.session_state.bt_map:
        rank = apply_backtest_calibration(rank, st.session_state.bt_map)
    else:
        rank["综合分"] = rank["模式分"]  # backward-compatible display name
    heading = {"开盘前":"今天开盘前优先盯谁", "盘中":"盘中现在优先看谁", "收盘前大引不成":"收盘前大引不成优先候选", "收盘后预测明天":"明天优先观察谁"}[mode]
    st.subheader(heading)
    top = rank.iloc[0].copy()


    st.markdown("### ✅ 最终结论")
    final_label = stock_label(str(top["代码"]))
    final_grade = str(top.get("结论", "—"))
    hist_state = str(top.get("历史状态", "未回测"))
    pts_state = str(top.get("PTS状态", "—"))
    news_state = str(top.get("新闻判断", "—"))
    risk_label = str(top.get("风险标签", "—"))

    if final_grade.startswith("A"):
        st.success(
            f"**首选：{final_label}**｜{final_grade}｜综合分 {safe_float(top.get('综合分')):.1f}\n\n"
            f"历史：{hist_state}｜新闻：{news_state}｜海外：{str(top.get('海外催化状态','—'))}｜风险：{risk_label}"
        )
    elif final_grade.startswith("B+"):
        st.warning(
            f"**优先观察：{final_label}**｜{final_grade}｜综合分 {safe_float(top.get('综合分')):.1f}\n\n"
            f"还差一次明确转强确认。历史：{hist_state}｜新闻：{news_state}｜风险：{risk_label}"
        )
    else:
        st.info(
            f"**当前没有很强的买点。排名第一：{final_label}**｜{final_grade}｜综合分 {safe_float(top.get('综合分')):.1f}\n\n"
            f"不要为了必须买而硬买。历史：{hist_state}｜新闻：{news_state}｜风险：{risk_label}"
        )
    top_ns, top_news_label, top_news_items = force_news_check(str(top["代码"]))
    top["新闻分"] = top_ns
    top["新闻判断"] = top_news_label
    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric("第一名", stock_label(str(top["代码"])))
    c2.metric(f"{mode}分", format_num(top["综合分"],1))
    c3.metric("背景 / 触发", f"{format_num(top['背景分'],0)} / {format_num(top['触发分'],0)}")
    c4.metric("一手资金", f"¥{top['一手资金']:,.0f}" if math.isfinite(top['一手资金']) else "—")
    c5.metric("结论", top["结论"])
    if math.isfinite(safe_float(top.get("PTS涨跌%"))):
        c6.metric("夜间PTS", f"{format_num(top.get('PTS涨跌%'))}%", help=str(top.get("PTS状态","")))
    else:
        c6.metric("夜间PTS", "—")
    c7.metric("海外催化", f"{format_num(top.get('海外催化分'),1)}", help=f"{top.get('海外催化明细','—')}\n最新数据：{top.get('海外最新数据时间','—')}")
    st.info(f"第一名 {stock_label(str(top['代码']))}｜{top['模式说明']}｜风险：{top['风险标签']}；新闻：{top['新闻判断']}。第一名也不是收益保证。")
    st.caption(f"海外关联：{top.get('海外催化明细','未发现足够可靠且新鲜的海外关联信号')}")

    # Freeze Top5 only for an explicit full-analysis click in this mode.
    _run_id = st.session_state.analysis_run_id
    _analysis_time = st.session_state.analysis_time
    if _run_id and st.session_state.analysis_mode == mode:
        if _run_id not in st.session_state.prediction_snapshots:
            st.session_state.prediction_snapshots[_run_id] = build_top5_snapshot(
                rank, mode, _run_id, _analysis_time
            )
        snap = st.session_state.prediction_snapshots[_run_id]

        st.markdown("### 🏆 本模式 Top 5｜冻结预测")
        st.caption(f"预测时间：{_analysis_time}｜{prediction_validation_rule(mode)}")
        top5_cols = [
            "排名","代码","日文名","中文名","预测价格","综合分","结论",
            "买入计划类型","回踩买入下沿","回踩买入上沿","失效位","第一止盈","强势目标","风险"
        ]
        top5_view = snap[top5_cols].copy()
        for c in ["预测价格","综合分","回踩买入下沿","回踩买入上沿","失效位","第一止盈","强势目标"]:
            top5_view[c] = pd.to_numeric(top5_view[c], errors="coerce").round(2)
        st.dataframe(top5_view, use_container_width=True, hide_index=True)

        st.download_button(
            "💾 下载这次Top5预测快照（明天可直接拿来验）",
            data=snap.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"prediction_{_run_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if supabase_configured():
            if _run_id not in st.session_state.prediction_saved_runs:
                _ok, _msg = save_predictions_supabase(snap)
                if _ok:
                    st.session_state.prediction_saved_runs.add(_run_id)
                    st.success("☁️ 本次Top5已自动写入外部预测日志。")
                else:
                    st.warning(f"外部日志保存失败：{_msg}。CSV仍可正常保存。")
            else:
                st.caption("☁️ 本次Top5已保存到外部预测日志。")
        else:
            st.caption("☁️ 未接外部数据库也没关系：先下载CSV，明天收盘后把CSV给ChatGPT即可逐条验。")

    if st.session_state.bt_map:
        st.caption("下面是辅助细节；如果你只想要结论，看上面的最终结论和止盈计划即可。")
        st.markdown("#### 🧪 一键历史回测校准")
        b1,b2,b3,b4,b5,b6 = st.columns(6)
        b1.metric("历史状态", str(top.get("历史状态","—")))
        b2.metric("次日上涨", f"{format_num(top.get('次日上涨概率%'))}%")
        b3.metric("3日延续", f"{format_num(top.get('3日延续概率%'))}%")
        b4.metric("假突破风险", f"{format_num(top.get('3日假突破风险%'))}%")
        b5.metric("相似样本", f"{int(top.get('相似样本',0))}")
        b6.metric("历史校准", f"{format_num(top.get('历史校准分'),1)}")
        st.caption(
            f"历史样本总数约 {st.session_state.bt_case_count:,} 条；"
            f"个股自身样本 {int(top.get('自身样本',0))} 条，自身权重 {format_num(top.get('自身权重%'),1)}%。"
            f" 新股自身样本不足时会自动更多依赖相似股票，不需要手动设置。"
        )

    if mode == "收盘前大引不成":
        st.markdown("#### 🌙 大引不成隔夜资格")
        moc = rank[rank["大引不成资格"] == True].copy()
        if moc.empty:
            st.error("今天没有通过大引不成硬门槛的股票：宁可不隔夜，也不为了下单硬凑一只。")
        else:
            best_moc = moc.iloc[0]
            st.success(f"优先候选：**{stock_label(str(best_moc['代码']))}**｜大引不成分 {best_moc['综合分']:.1f}｜尾盘强度 {best_moc['尾盘强度分']:.1f}")
            mc1,mc2,mc3,mc4,mc5 = st.columns(5)
            mc1.metric("尾盘30分钟", f"{format_num(best_moc['尾盘30分钟%'])}%")
            mc2.metric("当日位置", f"{format_num(best_moc['当日位置%'])}%")
            mc3.metric("VWAP偏离", f"{format_num(best_moc['VWAP偏离%'])}%")
            mc4.metric("尾盘量能", f"{format_num(best_moc['尾盘量能倍率'])}x")
            mc5.metric("涨幅留存", f"{format_num(best_moc['日内涨幅保留率%'])}%")
            st.caption("思路：先挂你愿意接的低价限价；若盘中未成交，再由‘不成’在收盘集合竞价转为市价。这里只筛隔夜质量，不保证次日高开。免费5分钟行情可能延迟，收盘前务必再看券商盘口。")


    st.markdown("#### 🚀 强势突破追强通道")
    st.caption("默认仍优先健康回调；但真正的强趋势股如果接近/突破近期高点、冲高留存好且风险不过高，也允许追强。弱票突然暴拉不会被当成真突破。")
    if "追强资格" in rank.columns:
        breakout_pool = rank[rank["追强资格"] == True].copy()
        if breakout_pool.empty:
            st.caption("今天没有股票通过『强势突破追强』风险门槛。宁可不追，也不把弱票突然暴拉当成主升突破。")
        else:
            breakout_pool = breakout_pool.sort_values(["追强分","综合分"], ascending=False).head(8)
            breakout_pool["回踩计划"] = breakout_pool.apply(lambda rr: pullback_buy_plan(rr), axis=1)
            breakout_pool["回踩买入下沿"] = breakout_pool["回踩计划"].apply(lambda x: x["回踩下沿"])
            breakout_pool["回踩买入上沿"] = breakout_pool["回踩计划"].apply(lambda x: x["回踩上沿"])
            breakout_pool["回踩失效位"] = breakout_pool["回踩计划"].apply(lambda x: x["失效位"])
            bo_cols = ["代码","日文名","中文名","现价","一手资金","日涨跌%","20日%","距20日高%","追强分","回踩买入下沿","回踩买入上沿","回踩失效位","近10日冲高保留率%","冲高失败次数","弱势惩罚","PTS涨跌%","PTS可信度%","PTS调整分","追强理由","追强风险"]
            bo_cols = [c for c in bo_cols if c in breakout_pool.columns]
            bo_df = breakout_pool.loc[:, bo_cols].copy()
            bo_num = [c for c in bo_cols if c not in ["代码","日文名","中文名","追强理由","追强风险"]]
            bo_df[bo_num] = bo_df[bo_num].round(2)
            st.dataframe(bo_df, use_container_width=True, hide_index=True)

    # Fun layer: rules first, randomness second. Weak/broken names are never admitted to the draw.
    st.markdown("#### 🎲 大师点兵：先过纪律，再交给一点运气")
    eligible = rank[(rank["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])) & (rank["风险总惩罚"] < 18) & (~rank.get("历史状态", pd.Series("未回测", index=rank.index)).eq("🔴 历史警戒"))].copy()
    if eligible.empty:
        st.caption("今天没有足够合格的票，大师拒绝硬抽。")
    else:
        pool = eligible.head(min(8, len(eligible))).copy()
        pool["点兵权重"] = np.maximum(pool["综合分"] - pool["综合分"].min() + 8, 1)
        b1, b2 = st.columns([1, 2])
        with b1:
            if st.button("🎯 从合格前排里点一只", use_container_width=True):
                choice = random.choices(pool["代码"].tolist(), weights=pool["点兵权重"].tolist(), k=1)[0]
                st.session_state["master_pick"] = choice
        with b2:
            st.caption("不是 72 只瞎抽：先剔除破位、连续创新低和高风险弱票，只在前排合格候选里按评分加权随机。")
        pick = st.session_state.get("master_pick")
        if pick in pool["代码"].values:
            pr = pool[pool["代码"] == pick].iloc[0]
            st.success(f"今日点兵：**{stock_label(pick)}**｜综合分 {pr['综合分']:.1f}｜安全回调分 {pr['安全回调分']:.1f}｜{pr['结论']}")

    st.markdown("#### 🛡️ 回调埋伏候选")
    dip = rank[(rank["回调质量分"] >= 14) & (rank["背景分"] >= 22) & (rank["风险总惩罚"] < 18)].sort_values(["回调质量分","空间盈亏比分","综合分"], ascending=False).head(8)
    if dip.empty:
        st.caption("今天没有满足‘强势 + 小回调 + 守支撑’的明显候选。")
    else:
        dip["回踩计划"] = dip.apply(lambda rr: pullback_buy_plan(rr), axis=1)
        dip["回踩买入下沿"] = dip["回踩计划"].apply(lambda x: x["回踩下沿"])
        dip["回踩买入上沿"] = dip["回踩计划"].apply(lambda x: x["回踩上沿"])
        dip["回踩失效位"] = dip["回踩计划"].apply(lambda x: x["失效位"])
        st.dataframe(dip[["代码","日文名","中文名","现价","一手资金","日涨跌%","20日%","距支撑%","距20日高%","回踩买入下沿","回踩买入上沿","回踩失效位","回调质量分","上方空间/支撑风险比","背景分","触发分","综合分","结论"]].round(2), use_container_width=True, hide_index=True)

    st.markdown("#### 排名表")
    show_cols = ["代码","日文名","中文名","结论","综合分","现价","一手资金","预算可买一手","资金友好分","背景分","触发分","回调质量分","上方空间/支撑风险比","ATR14%","日涨跌%","5日%","20日%","距20日高%","距支撑%","量比20日","结构持续分","涨幅保留分","近10日冲高保留率%","冲高失败次数","强势分","回踩分","转强分","安全回调分","风险总惩罚","追强资格","追强分","追强理由","追强风险","历史状态","历史校准分","次日上涨概率%","3日延续概率%","3日假突破风险%","相似样本","自身样本","PTS价格","PTS涨跌%","PTS成交量","PTS成交额","PTS可信度%","PTS调整分","PTS状态","PTS时间","海外催化分","海外催化状态","海外有效因子数","海外最新数据时间","海外最新数据年龄分钟","海外催化明细","新闻判断","风险标签"]
    if mode in ["盘中", "收盘前大引不成"]:
        extras = ["盘中现价","盘中涨跌%","当日位置%","距日高%","盘中量价分"]
        if mode == "收盘前大引不成":
            extras += ["大引不成资格","5分MA20","距5分MA20%","5分MA20斜率%","5分结构分","尾盘30分钟%","尾盘量能倍率","VWAP偏离%","日内涨幅保留率%","尾盘强度分"]
        for extra in extras:
            if extra in rank.columns:
                show_cols.insert(6, extra)
    # Some columns exist only after optional modules (e.g. backtest). Never crash the whole app for a missing display-only column.
    show_cols = [c for c in show_cols if c in rank.columns]
    display_df = rank.loc[:, show_cols].copy()
    num_cols = [c for c in show_cols if c not in ["代码","日文名","中文名","结论","预算可买一手","历史状态","PTS状态","PTS时间","海外催化状态","海外最新数据时间","海外催化明细","新闻判断","风险标签","追强理由","追强风险"]]
    display_df[num_cols] = display_df[num_cols].round(2)
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=620)

    st.divider()
    st.subheader("问大师：现在买哪个？")
    q = st.text_input("可以直接问：‘现在买哪个？’、‘6203 和 5801 哪个更好？’、‘9984 还能追吗？’", placeholder="输入问题")
    if q:
        codes_in_q = [c for c in STOCK_CODES if re.search(rf"(?<![0-9A-Z]){re.escape(c)}(?![0-9A-Z])", q.upper())]
        scope = rank[rank["代码"].isin(codes_in_q)] if codes_in_q else rank.head(10)
        if scope.empty:
            st.error("没识别到股票池里的代码。直接输入代码最稳，例如：6203 和 5801 哪个更好？")
        else:
            best = scope.sort_values("综合分", ascending=False).iloc[0].copy()
            q_ns, q_news_label, q_items = force_news_check(str(best["代码"]))
            best["新闻分"] = q_ns
            best["新闻判断"] = q_news_label
            if "追" in q and math.isfinite(safe_float(best.get("日涨跌%"))) and safe_float(best.get("日涨跌%")) >= 6:
                if bool(best.get("追强资格", False)) and str(best.get("历史状态","")) != "🔴 历史警戒":
                    st.success(f"{stock_label(str(best['代码']))} 属于可评估的**强势突破追强**候选：不是因为涨得多就放行，而是趋势/留存/风险门槛已通过。")
                else:
                    st.error(f"{stock_label(str(best['代码']))} 虽然暴拉，但没有通过追强风险门槛；这种更接近需要防范的弱势反弹/假突破，不建议因为怕踏空硬追。")
            else:
                st.success(f"当前规则下更优的是 **{stock_label(str(best['代码']))}**（综合分 {best['综合分']:.1f}，结论：{best['结论']}）。")
                st.write(
                    f"理由：背景 {format_num(best['背景分'])} / 触发 {format_num(best['触发分'])}｜20日 {format_num(best['20日%'])}%｜"
                    f"距支撑 {format_num(best['距支撑%'])}%｜ATR {format_num(best['ATR14%'])}%｜一手约 ¥{best['一手资金']:,.0f}｜资金友好 {format_num(best['资金友好分'])}。"
                )
                st.write(f"风险：{best['风险标签']}。新闻：{best['新闻判断']}。")
                tp = take_profit_targets(best, best["现价"])
                is_a = str(best["结论"]).startswith("A｜")
                note = tp["说明"] if is_a else "当前还不是‘已触发’A级买点：以下止盈位只是按当前价做的预演，不代表现在就应该买。"
                render_take_profit_banner(tp, is_recommended=is_a, note=note)

    st.divider()
    st.subheader("单票诊断")
    selected = st.selectbox("股票", rank["代码"].tolist(), format_func=stock_label)
    row = rank[rank["代码"] == selected].iloc[0].copy()
    single_ns, single_news_label, single_news_items = force_news_check(str(selected))
    row["新闻分"] = single_ns
    row["新闻判断"] = single_news_label
    # Keep this explicit check in session so the news list and label come from the same lookup.
    if st.session_state.news is None:
        st.session_state.news = {}
    st.session_state.news[str(selected)] = (single_ns, single_news_label, single_news_items)
    news_map = st.session_state.news
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("现价", format_num(row["现价"],1))
    m2.metric("一手资金", f"¥{row['一手资金']:,.0f}")
    m3.metric("背景 / 触发", f"{format_num(row['背景分'],0)} / {format_num(row['触发分'],0)}")
    m4.metric("距支撑", f"{format_num(row['距支撑%'])}%")
    m5.metric("ATR14", f"{format_num(row['ATR14%'])}%")
    m6.metric("综合分", format_num(row["综合分"]))
    st.write(f"**结论：{row['结论']}**｜{row['风险标签']}｜{row['新闻判断']}")


    if st.session_state.bt_map and str(selected) in st.session_state.bt_map:
        br = st.session_state.bt_map[str(selected)]
        st.markdown("#### 🧪 这只股票的历史相似结构")
        h1,h2,h3,h4,h5 = st.columns(5)
        h1.metric("历史状态", br["历史状态"])
        h2.metric("次日上涨", f"{br['次日上涨概率%']:.1f}%")
        h3.metric("3日延续", f"{br['3日延续概率%']:.1f}%")
        h4.metric("假突破风险", f"{br['3日假突破风险%']:.1f}%")
        h5.metric("相似样本", f"{br['相似样本']}")
        st.caption(
            f"个股自身相似样本 {br['自身样本']} 条（自动权重 {br['自身权重%']:.1f}%）；"
            f"相似样本次日高点中位 {format_num(br['相似样本次日高点中位%'])}% / "
            f"次日低点中位 {format_num(br['相似样本次日低点中位%'])}% / "
            f"3日高点中位 {format_num(br['相似样本3日高点中位%'])}% / "
            f"3日低点中位 {format_num(br['相似样本3日低点中位%'])}%。"
        )
    if "历史完整度" in row.index and row["历史完整度"] != "完整":
        st.warning(f"⚠️ {row['历史完整度']}：MA20、20日涨幅等长周期指标可能不可用或参考价值较低；系统不会因此把这只新股从股票池删除。")
    p1,p2,p3 = st.columns(3)
    p1.metric("通常涨停价", format_num(row["正常涨停价"],1))
    p2.metric("通常跌停价", format_num(row["正常跌停价"],1))
    p3.metric("制限值幅", f"±{format_num(row['制限值幅'],1)} 円")
    st.caption("涨跌停按东证通常制限值幅、以前一交易日基准价估算；连续无成交封板等情形可能触发次日扩大制限值幅，应以 JPX 当日公告为准。")

    pb_single = pullback_buy_plan(row)
    st.markdown("### 🪂 回踩买入计划（预测时固定）")
    pb1,pb2,pb3 = st.columns(3)
    pb1.metric("计划类型", pb_single["类型"])
    pb2.metric("回踩买入区间", f"¥{pb_single['回踩下沿']:.0f} ～ ¥{pb_single['回踩上沿']:.0f}" if math.isfinite(pb_single["回踩下沿"]) else "—")
    pb3.metric("失效参考", f"¥{pb_single['失效位']:.0f}" if math.isfinite(pb_single["失效位"]) else "—")
    st.caption(pb_single["说明"])

    st.markdown("### 🎯 止盈计划（固定显示）")
    default_entry = float(row["现价"]) if math.isfinite(safe_float(row["现价"])) else 0.0
    entry_price = st.number_input("你的参考买入价 / 实际成本价", min_value=0.0, value=default_entry, step=1.0, key=f"entry_{selected}")
    tp = take_profit_targets(row, entry_price if entry_price > 0 else row["现价"])
    is_a = str(row["结论"]).startswith("A｜")
    note = tp["说明"] if is_a else "当前不是A级已触发买点：下面止盈位固定显示给你做交易计划，但属于测算，不等于建议此刻买入。"
    render_take_profit_banner(tp, is_recommended=is_a, note=note)
    t1,t2 = st.columns(2)
    t1.metric("📈 近10日冲高保留率", f"{format_num(row['近10日冲高保留率%'])}%")
    t2.metric("⚠️ 冲高失败次数", f"{int(row['冲高失败次数']) if math.isfinite(safe_float(row['冲高失败次数'])) else '-'}")
    if row["冲高失败次数"] >= 3:
        st.warning("这只票近期多次出现‘盘中冲高、收盘吐回去’，即使触及止盈附近，也更适合分批兑现，不宜默认它一定继续冲。")

    if selected in raw_map:
        st.plotly_chart(chart_for(selected, raw_map[selected], row["关键支撑"]), use_container_width=True)
    items = single_news_items
    if items:
        st.markdown("**近期公开新闻**")
        for it in items[:6]:
            title = it['title'].replace('[','').replace(']','')
            st.markdown(f"- [{title}]({it['link']})")
    else:
        st.caption("暂未抓到公开新闻；不要把‘没抓到’理解成‘公司没有新闻’。")
else:
    st.info("点击上面的“扫描 72 只股票”开始。首次加载可能稍慢。")

with st.expander("📊 验证昨天/之前的预测 CSV", expanded=False):
    st.markdown("""
今天下载网站生成的 `prediction_....csv`。  
到了验证日，把文件**直接拖到下面的框里**，然后点“开始判卷”。网站会自己抓实际行情，不用手填。
""")
    uploaded_pred = st.file_uploader(
        "把之前下载的 prediction_....csv 拖到这里",
        type=["csv"],
        key="prediction_verify_upload",
        accept_multiple_files=False,
    )
    if uploaded_pred is not None:
        st.caption(f"已载入：{uploaded_pred.name}")
        if st.button("📊 开始判卷", use_container_width=True, key="verify_prediction_btn"):
            with st.spinner("正在抓实际行情并对照冻结预测…"):
                verified_df, verify_err = verify_prediction_csv(uploaded_pred)
            if verify_err:
                st.error(verify_err)
            elif verified_df is not None:
                st.session_state["verified_prediction_df"] = verified_df

    verified_df = st.session_state.get("verified_prediction_df")
    if verified_df is not None and not verified_df.empty:
        show_cols = [c for c in [
            "排名","代码","日文名","中文名","模式","预测时间","预测价格",
            "回踩买入下沿","回踩买入上沿","失效位","第一止盈","强势目标",
            "验证日期","实际开盘","实际最高","实际最低","实际收盘",
            "最大浮盈%","最大浮亏%","收盘收益%","回踩买入区间触及",
            "第一止盈命中","强势目标命中","失效位触及","低点后收盘反弹%","判卷结果"
        ] if c in verified_df.columns]
        view = verified_df[show_cols].copy()
        for c in ["预测价格","回踩买入下沿","回踩买入上沿","失效位","第一止盈","强势目标",
                  "实际开盘","实际最高","实际最低","实际收盘",
                  "最大浮盈%","最大浮亏%","收盘收益%","低点后收盘反弹%"]:
            if c in view.columns:
                view[c] = pd.to_numeric(view[c], errors="coerce").round(2)
        st.dataframe(view, use_container_width=True, hide_index=True)

        ok_count = verified_df["判卷结果"].astype(str).str.startswith("✅").sum() if "判卷结果" in verified_df.columns else 0
        fail_count = verified_df["判卷结果"].astype(str).str.startswith("❌").sum() if "判卷结果" in verified_df.columns else 0
        neutral_count = verified_df["判卷结果"].astype(str).str.startswith("🟡").sum() if "判卷结果" in verified_df.columns else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("成功", int(ok_count))
        c2.metric("一般/混乱", int(neutral_count))
        c3.metric("失败", int(fail_count))

        st.download_button(
            "💾 下载判卷后的CSV",
            data=verified_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="verified_predictions.csv",
            mime="text/csv",
            use_container_width=True,
        )

with st.expander("☁️ 跨天预测日志 / Supabase连接"):
    if supabase_configured():
        st.success("已检测到Supabase配置。每次『全自动分析』的Top5会自动写入外部日志。")
        recent = load_recent_predictions_supabase(100)
        if recent.empty:
            st.caption("暂时没有读到历史记录，或数据库表尚未创建。")
        else:
            cols = [c for c in ["analysis_time","mode","rank_no","code","jp_name","cn_name","price","score","plan_type","buy_zone_low","buy_zone_high","invalidation","tp1","tp2","verified_at","eval_close","close_return_pct"] if c in recent.columns]
            st.dataframe(recent[cols], use_container_width=True, hide_index=True)
    else:
        st.markdown("""
**不接数据库也能验证：** 每次分析下载Top5 CSV，第二天收盘后把CSV给ChatGPT。

**要让网站自己跨天记住：**
1. 创建一个 Supabase 免费项目。
2. 在项目 SQL Editor 创建 `predictions` 表（完整SQL在 README）。
3. Streamlit Cloud → App settings / Secrets 填：
```toml
SUPABASE_URL = "https://你的项目.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_你的服务器密钥"
```
密钥只放 Streamlit Secrets，不要传到GitHub。
""")

with st.expander("股票池（72只）"):
    st.dataframe(pd.DataFrame(STOCKS, columns=["代码","日文正式/常用名","中文译名"]), use_container_width=True, hide_index=True)

with st.expander("四个时段为什么分开算"):
    st.markdown("""
- **开盘前**：重昨收结构、趋势背景、回踩位置和隔夜新闻；触发分只作参考，因为今天还没真正走出来。  
- **盘中**：重实时重新转强、当日位置、距日高、冲高回落和追高风险；这是最严格的“现在能不能买”。  
- **收盘前大引不成**：专门服务收盘集合竞价前的隔夜候选。重尾盘30分钟动量、尾盘量能、VWAP、日内位置和涨幅留存；尾盘跳水、冲高全吐、当天已经失控加速会被重罚。  
- **收盘后预测明天**：重收盘质量、涨幅保留、全天量价和关键位是否守住；用于做第二天观察清单。  

同一只票在四个模式得分不同是正常的。**资金友好度现在是合格候选之间的中等权重加分项，不会救活弱票。**
""")

with st.expander("评分怎么判"):
    st.markdown("""
**先过硬门槛，再比较谁更值得花钱。**

**1. 趋势背景**：20/60日动量只是参考，不再把“一次暴涨”当成持续强势；同时看 MA20 斜率、过去20日站在 MA20 上方的比例、分段高低点是否抬升。  
**2. 回踩质量**：靠近真实支撑、未破 MA20/近期平台、从高点适度回撤更好；下跌时缩量比放量砸盘更健康。  
**3. 买点触发**：重新站上前高、连续回升、上涨伴随合理放量才给“触发分”。所以会出现“背景很好，但还没到买点”。  
**4. 波动风险**：增加 ATR14；波动极端、长上影、冲高回落会扣分，避免只看涨幅。  
**5. 流动性**：日均成交额太低会扣分，减少小票被一次异动误判成强势。  
**6. akippa式弱票**：刷新20日低点、低点连续下移、5/20日持续走弱、放量不涨，硬惩罚；跌得多不自动抄底。  
**7. 资金友好度**：按日本现物常见100股一手估算 `现价×100`，并相对你设定的单票预算动态评分。只在 A/B 档候选里加最多14分；质量接近时明显优先占用资金少的，弱票不会靠“便宜”翻身。  
**8. 新闻催化**：只做佐证。业绩上修、受注、提携、自社株买等可加分；下修、增资、MS warrant 等扣分，但新闻不能覆盖技术面硬伤。  
**9. 日股涨跌停**：按 JPX 通常制限值幅估算正常涨停/跌停；特殊扩大幅度日仍应以 JPX 公告为准。  
**10. 涨幅保留率**：统计近期真正出现过盘中拉升的交易日，看收盘还能留下多少涨幅；能留住、收盘重心抬升加分，反复冲高全吐且失败次数多则扣分。  
**11. 动态止盈**：对A级已触发候选，以实际买入价/参考价为基准，结合 ATR、20/60日前高压力位和通常涨停价，给“第一止盈 + 强势续抱目标”；不是统一死板+5%。  
**12. 大师点兵**：先把明显弱票排掉，再在前排合格候选中加权随机。随机承认短线的不确定性，但不替代纪律。  
**13. 盘中短周期结构**：只使用实际抓到的 5 分钟 OHLCV 计算。增加 5分钟MA20（约100分钟均价）、MA20短期斜率，以及最近6根5分钟K线的高点/低点是否抬高。价格在上行MA20附近、且高低点同步抬高加分；跌破下行MA20、且高低点同步下移扣分。数据取不到就显示为空，不补猜。  
**14. 收盘前大引不成**：只在尾盘结构健康时考虑隔夜。优先“强背景 + 价格在日内高位区但没有失控加速 + 最后30分钟不跳水 + 站在VWAP上方 + 5分钟结构不弱 + 尾盘量能温和增强 + 涨幅留存较高”的股票；尾盘突然直线拉升、离VWAP过远、当天涨幅过大或冲高回落明显则扣分。

**15. 一键历史回测/相似结构校准**：自动抓取股票池约2年日线，用每个历史时点“当时已经能看到的数据”生成样本，再统计之后1天/3天结果，避免未来数据泄漏。程序同时找“这只股票自身过去的相似形态”和“整个股票池里的相似形态”；老股票自身样本充足时最多占35%，新股样本少时自动更多依赖相似股票。小样本概率会向中性收缩，不把3次历史当成100%规律。历史校准最多只加减有限分数；若相似样本显示假突破风险明显偏高，会取消追强资格，但不会覆盖实时新闻和实时价格结构。
""")

st.caption("数据说明：Yahoo Finance/yfinance 为免费公开数据入口，不是东京证券交易所官方低延迟行情。资金友好度按100股一手估算，仅作排序辅助。新闻来自 Google News RSS。东证通常制限值幅规则按 JPX 公布表计算；连续封板等特殊扩大情形不由免费行情自动识别。")
