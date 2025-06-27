# -*- coding: utf-8 -*-
# dashboard.py
# =============================================================
# 沖縄県宿泊施設ダッシュボード  (S47〜R6)
# -------------------------------------------------------------
#  フォーマット統一:
#   - long CSV 列を  municipalty,value,0,1,cat1,metric,cat2,table,year に合わせる
#   - city → municipality にリネーム
#   - 0,1 は cat1,metric のバックアップ列 (melt 由来) を保持
# -------------------------------------------------------------

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RAW_DIR = Path("data/raw")
ALL_DIR = Path("data/processed/all")
TRANSITION_XLSX = RAW_DIR / "Transition.xlsx"
CSV_LONG = ALL_DIR / "all_years_long.csv"
ALL_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- 地域マスター ----------------
REGION_MAP = {
    "南部": ["那覇市", "糸満市", "豊見城市", "八重瀬町", "南城市", "与那原町", "南風原町"],
    "中部": ["沖縄市", "宜野湾市", "浦添市", "うるま市", "読谷村", "嘉手納町", "北谷町", "北中城村", "中城村", "西原町"],
    "北部": ["名護市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町", "恩納村", "宜野座村", "金武町"],
    "宮古": ["宮古島市", "多良間村"],
    "八重山": ["石垣市", "竹富町", "与那国町"],
    "離島": [
        "久米島町", "渡嘉敷村", "座間味村", "粟国村", "渡名喜村",
        "南大東村", "北大東村", "伊江村", "伊平屋村", "伊是名村",
    ],
}

# ---------------- 読み込みヘルパ ----------------
ALIASES = {
    "facilities": {"facilities", "facility", "軒数"},
    "rooms": {"rooms", "room", "客室数"},
    "capacity": {"capacity", "capac", "capacit", "収容人数"},
}

# ------------------------------------------------------------
# メイン
# ------------------------------------------------------------

def main():
    st.set_page_config(page_title="沖縄県宿泊施設データ可視化", page_icon="🏨", layout="wide")
    st.title("沖縄県宿泊施設データ可視化アプリ")

    # ===== ロング CSV 読み込み & クリーニング =====
    if not CSV_LONG.exists():
        st.error("all_years_long.csv が見つかりません"); return

    cols_needed = ["municipality", "value", "cat1", "metric", "cat2", "table", "year"]
    df_long = pd.read_csv(CSV_LONG)

    # --- 旧フォーマット互換: city→municipality へリネーム --------
    if "municipality" not in df_long.columns and "city" in df_long.columns:
        df_long = df_long.rename(columns={"city": "municipality"})

    # --- cat1,metric が小文字で total 抽出 ------------------------
    df_long["cat1"]   = df_long["cat1"].fillna("").astype(str).str.strip().str.lower()
    df_long["metric"] = df_long["metric"].astype(str).str.strip().str.lower()
    df_long["value"]  = pd.to_numeric(df_long["value"], errors="coerce").fillna(0)

    # ===== サイドバー =============================================
    st.sidebar.header("🎛️ 表示オプション")
    regions = list(REGION_MAP.keys())
    sel_regions = st.sidebar.multiselect("エリア", regions)

    excluded = set(regions) | {"沖縄県"}
    muni_all = sorted([m for m in df_long["municipality"].unique() if m not in excluded])
    sel_muni = st.sidebar.multiselect("市町村", muni_all)

    min_y, max_y = df_long["year"].min(), df_long["year"].max()
    year_range = st.sidebar.slider("年範囲", int(min_y), int(max_y), (int(min_y), int(max_y)))

    elem_map = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}
    sel_elems = st.sidebar.multiselect("指標", list(elem_map.keys()), default=["軒数"])

    # ===== 県全体 (total) 表示 =====================================
    pref_total = (df_long[(df_long["municipality"] == "沖縄県") & (df_long["cat1"] == "total")]
                       .pivot_table(index="year", columns="metric", values="value", aggfunc="sum")
                       .rename(columns={"facilities": "軒数", "rooms": "客室数", "capacity": "収容人数"})
                       .sort_index())

    if not pref_total.empty:
        st.header("📈 沖縄県全体の状況")
        latest_year = int(pref_total.index.max())
        latest = pref_total.loc[latest_year]
        c1,c2,c3 = st.columns(3)
        c1.metric(f"総施設数（{latest_year}年）", f"{int(latest['軒数']):,} 軒")
        c2.metric(f"総客室数（{latest_year}年）", f"{int(latest['客室数']):,} 室")
        c3.metric(f"総収容人数（{latest_year}年）", f"{int(latest['収容人数']):,} 人")

    # ===== エリア別 ================================================
    if sel_regions:
        st.header("🗺️ エリア別の状況")
        for label,jp_col in elem_map.items():
            if label not in sel_elems: continue
            st.subheader(f"{label} の推移（エリア合計）")
            fig=go.Figure();tbl=[]
            for reg in sel_regions:
                cities = REGION_MAP[reg]
                sub = df_long[(df_long["municipality"].isin(cities)) &
                              (df_long["year"].between(*year_range)) &
                              (df_long["metric"]==jp_col) &
                              (df_long["cat1"]=="total")]
                if sub.empty: continue
                series = sub.groupby("year")["value"].sum()
                fig.add_scatter(x=series.index, y=series.values, mode="lines+markers", name=reg)
                tbl.append(series.rename(reg))
            fig.update_layout(height=400, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)
            if tbl:
                st.dataframe(pd.concat(tbl, axis=1).fillna(0).astype(int).style.format(thousands=","), use_container_width=True)

    # ===== 市町村別 ===============================================
    if sel_muni:
        st.header("🏘️ 市町村別の状況")
        for label,jp_col in elem_map.items():
            if label not in sel_elems: continue
            st.subheader(f"{label} の推移（市町村別）")
            fig=go.Figure();tbl=[]
            for city in sel_muni:
                sub = df_long[(df_long["municipality"]==city) &
                              (df_long["year"].between(*year_range)) &
                              (df_long["metric"]==jp_col) &
                              (df_long["cat1"]=="total")]
                if sub.empty: continue
                fig.add_scatter(x=sub["year"], y=sub["value"], mode="lines+markers", name=city)
                tbl.append(sub.set_index("year")["value"].rename(city))
            fig.update_layout(height=400, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)
            if tbl:
                st.dataframe(pd.concat(tbl, axis=1).fillna(0).astype(int).style.format(thousands=","), use_container_width=True)

if __name__ == "__main__":
    main()
