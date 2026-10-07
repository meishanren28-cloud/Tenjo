import math
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

st.set_page_config(page_title="四时段强势回踩大师", page_icon="🎲", layout="wide")

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
    "原本就强 + 回踩不破关键位 + 再次转强，才考虑买。",
    "连续创新低、收盘重心持续下移的弱票，直接重罚；不能因为“跌很多了”就自动抄底。",
    "有量不等于强：如果放量但价格不涨、冲高回落、收盘仍弱，视为派发/承接不足风险。",
    "类似 akippa：没有趋势、没有材料、没有惊喜，只靠突然暴拉，不追。",
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


def affordability_score(price, budget=300000):
    """Capital friendliness for a standard 100-share cash lot. Never rescues a weak stock."""
    if price is None or not math.isfinite(price) or price <= 0:
        return 0.0, np.nan, False
    lot_cash = price * 100
    fits = lot_cash <= budget
    # modest tie-breaker only; cap at 10 points
    if lot_cash <= 100000:
        s = 10
    elif lot_cash <= 150000:
        s = 9
    elif lot_cash <= 200000:
        s = 8
    elif lot_cash <= 300000:
        s = 6
    elif lot_cash <= 500000:
        s = 3
    elif lot_cash <= 800000:
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
    pull = r["安全回调分"].astype(float)
    retain = r["涨幅保留分"].astype(float)
    cheap = r["资金友好分"].astype(float)

    if mode == "开盘前":
        # Yesterday's structure + news + affordable execution. Trigger is only a minor prior-session clue.
        score = 0.58*bg + 0.22*np.maximum(pull,0) + 0.18*trig + 0.75*news - 0.72*risk
        r["模式说明"] = "盘前：重背景/支撑/隔夜新闻，少依赖尚未发生的盘中触发"
    elif mode == "盘中":
        intra = r.get("盘中量价分", pd.Series(0.0,index=r.index)).astype(float)
        short_struct = r.get("5分结构分", pd.Series(0.0,index=r.index)).astype(float)
        score = 0.38*bg + 0.72*trig + 0.32*np.maximum(pull,0) + 0.82*intra + 0.55*short_struct + 0.45*news - 0.82*risk
        r["模式说明"] = "盘中：重实时转强/日内位置/量价，严惩追高和冲高回落"
    elif mode == "收盘前大引不成":
        close_strength = r.get("尾盘强度分", pd.Series(0.0,index=r.index)).astype(float)
        intra = r.get("盘中量价分", pd.Series(0.0,index=r.index)).astype(float)
        short_struct = r.get("5分结构分", pd.Series(0.0,index=r.index)).astype(float)
        # For overnight MOC, closing behavior dominates. Background must still be healthy; cheapness remains a tie-breaker.
        score = 0.40*bg + 0.30*trig + 0.22*np.maximum(pull,0) + 1.18*close_strength + 0.20*intra + 0.45*short_struct + 0.48*news - 0.90*risk
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
        score = 0.48*bg + 0.42*trig + 0.38*np.maximum(pull,0) + 0.85*retain + 0.58*news - 0.76*risk
        r["模式说明"] = "收盘后：重收盘质量/涨幅留存/全天量价，筛明日候选"

    if "大引不成资格" not in r.columns:
        r["大引不成资格"] = False

    # Cheapness is a tie-breaker only for healthy candidates, never a rescue factor.
    healthy = r["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])
    score = pd.Series(score, index=r.index)
    score.loc[healthy] += cheap.loc[healthy]
    r["模式分"] = score.clip(-50,100)
    r = r.sort_values(["模式分","背景分","触发分","一手资金"], ascending=[False,False,False,True]).reset_index(drop=True)
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
    if df is None or df.empty or "Close" not in df.columns or len(df.dropna(subset=["Close"])) < 22:
        return None
    d = df.dropna(subset=["Close"]).copy()
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
    background_score = float(np.clip(strong_score * 0.55 + structure_score * 1.05 + pullback_score * 0.45 + safe_pullback_score * 0.35 + pullback_volume_score + retention_score * 0.8, -30, 70))
    trigger_score = float(np.clip(turn_score * 1.5 + max(0, safe_pullback_score) * 0.25, 0, 35))
    risk_penalty = float(penalties + vol_penalty + liquidity_penalty)
    technical = float(np.clip(background_score + trigger_score - risk_penalty, -50, 100))

    meta = STOCK_META.get(code, {})
    return {
        "代码": code,
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


def scan_all(codes):
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
    base["新闻判断"] = "未精查"
    # Capital friendliness is a tie-breaker only. It is added later only for non-weak candidates.
    aff = base["现价"].apply(lambda x: affordability_score(x, 300000))
    base["资金友好分"] = [x[0] for x in aff]
    base["一手资金"] = [x[1] for x in aff]
    base["30万预算可买一手"] = [x[2] for x in aff]
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
    # Only healthy/neutral candidates can receive affordability bonus. Weak names never get rescued by low price.
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


# ---------- UI ----------
st.title("🎲 四时段强势回踩资金友好大师")
st.caption("开盘前 / 盘中 / 收盘前大引不成 / 收盘后预测明天 · 四套侧重不同的评分 · 股票池固定 72 只 · 免费行情可能延迟")

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
st.caption("身份显示统一为：代码｜日文名｜中文译名。行情仍按代码.T抓取；代码与公司名分开保存，避免把名字当代码或串票。")

if "scan" not in st.session_state:
    st.session_state.scan = None
if "raw" not in st.session_state:
    st.session_state.raw = None
if "news" not in st.session_state:
    st.session_state.news = None

st.markdown("### 🕒 分析时段")
mode = st.radio("你现在是在什么时候选股？", ["开盘前", "盘中", "收盘前大引不成", "收盘后预测明天"], horizontal=True)
st.info(MODE_DESCRIPTIONS[mode])

st.markdown("### 💴 资金偏好")
budget = st.slider("单只股票最多愿意占用多少一手资金？", 100000, 1000000, 300000, 50000, format="¥%d")
st.caption("这里只影响合格候选之间的排序。便宜不会救活弱票；真正抓行情仍按股票代码进行。")

left, right = st.columns([1, 2])
with left:
    if st.button("🚀 扫描 72 只股票", type="primary", use_container_width=True):
        with st.spinner("正在拉取行情、计算趋势，并对前排候选精查新闻…"):
            rank, raw, news = scan_all(STOCK_CODES)
            if mode in ["盘中", "收盘前大引不成"]:
                intra = download_intraday(tuple(STOCK_CODES))
                rank = apply_intraday_features(rank, intra)
            st.session_state.scan = rank
            st.session_state.raw = raw
            st.session_state.news = news
            st.session_state.scan_mode = mode
with right:
    st.caption(f"当前模式：{mode}。先过弱势/破位硬门槛，再按该时段的权重排序；便宜只在合格候选之间加分。")

rank = st.session_state.scan
raw_map = st.session_state.raw or {}
news_map = st.session_state.news or {}

if rank is not None and not rank.empty:
    rank = rank.copy()
    # If user changed mode after scanning, reuse daily scan and fetch intraday only when needed.
    if mode in ["盘中", "收盘前大引不成"] and "盘中量价分" not in rank.columns:
        intra = download_intraday(tuple(STOCK_CODES))
        rank = apply_intraday_features(rank, intra)
    rank = mode_score(rank, mode, budget)
    rank["综合分"] = rank["模式分"]  # backward-compatible display name
    heading = {"开盘前":"今天开盘前优先盯谁", "盘中":"盘中现在优先看谁", "收盘前大引不成":"收盘前大引不成优先候选", "收盘后预测明天":"明天优先观察谁"}[mode]
    st.subheader(heading)
    top = rank.iloc[0]
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("第一名", stock_label(str(top["代码"])))
    c2.metric(f"{mode}分", format_num(top["综合分"],1))
    c3.metric("背景 / 触发", f"{format_num(top['背景分'],0)} / {format_num(top['触发分'],0)}")
    c4.metric("一手资金", f"¥{top['一手资金']:,.0f}" if math.isfinite(top['一手资金']) else "—")
    c5.metric("结论", top["结论"])
    st.info(f"第一名 {stock_label(str(top['代码']))}｜{top['模式说明']}｜风险：{top['风险标签']}；新闻：{top['新闻判断']}。第一名也不是收益保证。")

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

    # Fun layer: rules first, randomness second. Weak/broken names are never admitted to the draw.
    st.markdown("#### 🎲 大师点兵：先过纪律，再交给一点运气")
    eligible = rank[(rank["结论"].isin(["A｜强背景+已触发", "B+｜好候选，等转强", "B｜观察"])) & (rank["风险总惩罚"] < 18)].copy()
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
    dip = rank[(rank["安全回调分"] >= 10) & (rank["背景分"] >= 22) & (rank["风险总惩罚"] < 18)].sort_values(["安全回调分","综合分"], ascending=False).head(8)
    if dip.empty:
        st.caption("今天没有满足‘强势 + 小回调 + 守支撑’的明显候选。")
    else:
        st.dataframe(dip[["代码","日文名","中文名","现价","一手资金","日涨跌%","20日%","距支撑%","距20日高%","背景分","触发分","安全回调分","综合分","结论"]].round(2), use_container_width=True, hide_index=True)

    st.markdown("#### 排名表")
    show_cols = ["代码","日文名","中文名","结论","综合分","现价","一手资金","预算可买一手","资金友好分","背景分","触发分","ATR14%","日涨跌%","5日%","20日%","距20日高%","距支撑%","量比20日","结构持续分","涨幅保留分","近10日冲高保留率%","冲高失败次数","强势分","回踩分","转强分","安全回调分","风险总惩罚","新闻判断","风险标签"]
    if mode in ["盘中", "收盘前大引不成"]:
        extras = ["盘中现价","盘中涨跌%","当日位置%","距日高%","盘中量价分"]
        if mode == "收盘前大引不成":
            extras += ["大引不成资格","5分MA20","距5分MA20%","5分MA20斜率%","5分结构分","尾盘30分钟%","尾盘量能倍率","VWAP偏离%","日内涨幅保留率%","尾盘强度分"]
        for extra in extras:
            if extra in rank.columns:
                show_cols.insert(6, extra)
    display_df = rank[show_cols].copy()
    num_cols = [c for c in show_cols if c not in ["代码","日文名","中文名","结论","预算可买一手","新闻判断","风险标签"]]
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
            best = scope.sort_values("综合分", ascending=False).iloc[0]
            if "追" in q and math.isfinite(best["日涨跌%"] or np.nan) and best["日涨跌%"] >= 6:
                st.error(f"{best['代码']} 今天已经明显拉升。按你的纪律：**不追突然暴拉**。等回踩守住关键位、再度转强再看。")
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
    row = rank[rank["代码"] == selected].iloc[0]
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("现价", format_num(row["现价"],1))
    m2.metric("一手资金", f"¥{row['一手资金']:,.0f}")
    m3.metric("背景 / 触发", f"{format_num(row['背景分'],0)} / {format_num(row['触发分'],0)}")
    m4.metric("距支撑", f"{format_num(row['距支撑%'])}%")
    m5.metric("ATR14", f"{format_num(row['ATR14%'])}%")
    m6.metric("综合分", format_num(row["综合分"]))
    st.write(f"**结论：{row['结论']}**｜{row['风险标签']}｜{row['新闻判断']}")
    p1,p2,p3 = st.columns(3)
    p1.metric("通常涨停价", format_num(row["正常涨停价"],1))
    p2.metric("通常跌停价", format_num(row["正常跌停价"],1))
    p3.metric("制限值幅", f"±{format_num(row['制限值幅'],1)} 円")
    st.caption("涨跌停按东证通常制限值幅、以前一交易日基准价估算；连续无成交封板等情形可能触发次日扩大制限值幅，应以 JPX 当日公告为准。")

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
    if selected in news_map:
        items = news_map[selected][2]
    else:
        items = fetch_news(selected)
    if items:
        st.markdown("**近期公开新闻**")
        for it in items[:6]:
            title = it['title'].replace('[','').replace(']','')
            st.markdown(f"- [{title}]({it['link']})")
    else:
        st.caption("暂未抓到公开新闻；不要把‘没抓到’理解成‘公司没有新闻’。")
else:
    st.info("点击上面的“扫描 72 只股票”开始。首次加载可能稍慢。")

with st.expander("股票池（72只）"):
    st.dataframe(pd.DataFrame(STOCKS, columns=["代码","日文正式/常用名","中文译名"]), use_container_width=True, hide_index=True)

with st.expander("四个时段为什么分开算"):
    st.markdown("""
- **开盘前**：重昨收结构、趋势背景、回踩位置和隔夜新闻；触发分只作参考，因为今天还没真正走出来。  
- **盘中**：重实时重新转强、当日位置、距日高、冲高回落和追高风险；这是最严格的“现在能不能买”。  
- **收盘前大引不成**：专门服务收盘集合竞价前的隔夜候选。重尾盘30分钟动量、尾盘量能、VWAP、日内位置和涨幅留存；尾盘跳水、冲高全吐、当天已经失控加速会被重罚。  
- **收盘后预测明天**：重收盘质量、涨幅保留、全天量价和关键位是否守住；用于做第二天观察清单。  

同一只票在四个模式得分不同是正常的。**资金友好度始终只作为合格候选之间的加分项，不会救活弱票。**
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
**7. 资金友好度**：按日本现物常见100股一手估算 `现价×100`。只在 A/B 档候选里加最多10分；同样好时优先占用资金少的，弱票不会靠“便宜”翻身。  
**8. 新闻催化**：只做佐证。业绩上修、受注、提携、自社株买等可加分；下修、增资、MS warrant 等扣分，但新闻不能覆盖技术面硬伤。  
**9. 日股涨跌停**：按 JPX 通常制限值幅估算正常涨停/跌停；特殊扩大幅度日仍应以 JPX 公告为准。  
**10. 涨幅保留率**：统计近期真正出现过盘中拉升的交易日，看收盘还能留下多少涨幅；能留住、收盘重心抬升加分，反复冲高全吐且失败次数多则扣分。  
**11. 动态止盈**：对A级已触发候选，以实际买入价/参考价为基准，结合 ATR、20/60日前高压力位和通常涨停价，给“第一止盈 + 强势续抱目标”；不是统一死板+5%。  
**12. 大师点兵**：先把明显弱票排掉，再在前排合格候选中加权随机。随机承认短线的不确定性，但不替代纪律。  
**13. 盘中短周期结构**：只使用实际抓到的 5 分钟 OHLCV 计算。增加 5分钟MA20（约100分钟均价）、MA20短期斜率，以及最近6根5分钟K线的高点/低点是否抬高。价格在上行MA20附近、且高低点同步抬高加分；跌破下行MA20、且高低点同步下移扣分。数据取不到就显示为空，不补猜。  
**14. 收盘前大引不成**：只在尾盘结构健康时考虑隔夜。优先“强背景 + 价格在日内高位区但没有失控加速 + 最后30分钟不跳水 + 站在VWAP上方 + 5分钟结构不弱 + 尾盘量能温和增强 + 涨幅留存较高”的股票；尾盘突然直线拉升、离VWAP过远、当天涨幅过大或冲高回落明显则扣分。
""")

st.caption("数据说明：Yahoo Finance/yfinance 为免费公开数据入口，不是东京证券交易所官方低延迟行情。资金友好度按100股一手估算，仅作排序辅助。新闻来自 Google News RSS。东证通常制限值幅规则按 JPX 公布表计算；连续封板等特殊扩大情形不由免费行情自动识别。")
