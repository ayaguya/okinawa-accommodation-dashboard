"""
# okinawa_accommodation_dashboard.py
# =============================================================
# 沖縄県宿泊施設ダッシュボード  (H26〜R5)
# -------------------------------------------------------------
# 1) Excel → long 変換         : convert_excels_to_long()
# 2) long → clean & unify CSV  : clean_long_csvs()
# 3) Streamlit ダッシュボード   : streamlit_main()
# -------------------------------------------------------------
# フォルダ構成 (プロジェクト直下)
# ├─ data
# │   ├─ raw/            … 元 Excel ファイル (H26〜R5)
# │   ├─ processed/      … 変換後 long_YYYY.csv
# │   └─ unified/        … all_years_long.csv (クリーン済)
# └─ okinawa_accommodation_dashboard.py (本ファイル)
"""
from pathlib import Path
import pandas as pd
import re
import streamlit as st
import plotly.graph_objects as go
from app.type_map import METRIC_DISPLAY_NAMES, YEARS, YEAR_DISPLAY_NAMES, AREA_MAP

# ディレクトリ設定
DATA_DIR = Path(__file__).parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
UNIFY_DIR = DATA_DIR / "unified"

# ディレクトリ作成
for p in (PROC_DIR, UNIFY_DIR):
    p.mkdir(parents=True, exist_ok=True)

# エリアマップ
CITY_TO_AREA = {city: area for area, cities in AREA_MAP.items() for city in cities}

# ----------------------------
# 1. Excel → long 変換
# ----------------------------
def jp_year_to_yyyy(tag: str) -> int | None:
    """和暦/令和表記を西暦に変換"""
    m = re.search(r"([rh])(\d{1,2})", tag.lower())
    if not m:
        return None
    era, num = m.group(1), int(m.group(2))
    return 1988 + num if era == "h" else 2018 + num  # H1=1989, R1=2019

def convert_excels_to_long():
    """data/raw/*.xlsx → data/processed/long_YYYY.csv"""
    for fp in RAW_DIR.glob("*.xlsx"):
        year = jp_year_to_yyyy(fp.stem)
        if not year:
            st.warning(f"{fp.name}: 年の判定に失敗しました。スキップします。")
            continue
        out = PROC_DIR / f"long_{year}.csv"
        if out.exists():
            st.info(f"{out.name} は既に存在します。スキップ。")
            continue
        
        dfs = []
        for table in ["accommodation_type", "scale_class", "hotel_breakdown", "residential_act"]:
            try:
                df = pd.read_excel(fp, sheet_name=table, header=[0, 1])
            except ValueError:
                st.warning(f"{fp.name}: {table} シートが見つかりません。スキップ。")
                continue
            
            # フラット化処理
            df = df.rename(columns={df.columns[0]: "municipality"})
            df.columns = ["municipality"] + ["/".join(map(str, col)).replace("Unnamed: 0_level_", "").strip("/") for col in df.columns[1:]]
            df = df.melt(id_vars="municipality", var_name="key", value_name="value")
            
            # key列を分解 (cat1/cat2/metric)
            key_parts = df["key"].str.split("/", expand=True)
            if key_parts.shape[1] == 2:  # cat1 / metric
                key_parts[["cat1", "metric"]] = key_parts[[0, 1]]
                key_parts["cat2"] = ""
            elif key_parts.shape[1] == 3:
                key_parts[["cat1", "cat2", "metric"]] = key_parts[[0, 1, 2]]
            else:
                key_parts = key_parts.reindex(columns=range(3)).fillna("")
                key_parts.columns = ["cat1", "cat2", "metric"]
            
            df = pd.concat([df.drop(columns="key"), key_parts], axis=1)
            df["table"] = table
            df["year"] = year
            dfs.append(df)
        
        if dfs:
            long_df = pd.concat(dfs, ignore_index=True)
            long_df.to_csv(out, index=False)
            st.success(f"{out.name} を作成しました → {len(long_df):,} 行")

# ----------------------------
# 2. long → clean & unify
# ----------------------------
def clean_long_csvs():
    """CSVファイルを統合・クリーン化"""
    csv_files = sorted(PROC_DIR.glob("long_*.csv"))
    all_dfs = []
    
    for p in csv_files:
        df = pd.read_csv(p)
        # 市町村名の前後空白除去
        df["municipality"] = df["municipality"].str.strip()
        # エリア付与
        df["area"] = df["municipality"].map(CITY_TO_AREA).fillna("未分類")
        # 列名 & 順序統一
        df = df[[
            "year", "municipality", "area", "table", "cat1", "cat2", "metric", "value"
        ]]
        all_dfs.append(df)
    
    if not all_dfs:
        st.error("processed ディレクトリに CSV が見つかりません。")
        return None
    
    all_df = pd.concat(all_dfs, ignore_index=True)
    out_path = UNIFY_DIR / "all_years_long.csv"
    all_df.to_csv(out_path, index=False)
    st.success(f"統合ファイルを作成しました → {out_path.relative_to(Path.cwd())} ({len(all_df):,} 行)")
    return all_df

# ----------------------------
# 3. Streamlit ダッシュボード
# ----------------------------
def streamlit_main():
    st.set_page_config(page_title="沖縄県宿泊施設ダッシュボード", page_icon="🏨", layout="wide")
    st.markdown("""
    <h1 style="text-align:center;">🏨 沖縄県宿泊施設データ<br>可視化ダッシュボード</h1>
    """, unsafe_allow_html=True)

    # データ変換処理
    with st.expander("📥 Excel → CSV 変換を実行する", expanded=False):
        if st.button("Excel 変換実行", key="convert"):
            convert_excels_to_long()
    
    with st.expander("🔄 CSV 統合を実行する", expanded=False):
        if st.button("統合実行", key="clean"):
            clean_long_csvs()

    # データ読み込み
    unified_path = UNIFY_DIR / "all_years_long.csv"
    if not unified_path.exists():
        st.info("先に CSV の統合を実行してください。")
        return
    
    df = pd.read_csv(unified_path)
    
    # サイドバー
    st.sidebar.header("絞り込み条件")
    
    # 年度範囲
    min_year, max_year = st.sidebar.select_slider(
        "年度範囲",
        options=sorted(df["year"].unique()),
        value=(df["year"].min(), df["year"].max())
    )
    
    # エリア選択
    areas = st.sidebar.multiselect(
        "エリア",
        options=list(AREA_MAP.keys()),
        default=list(AREA_MAP.keys())
    )
    
    # 市町村選択
    cities = st.sidebar.multiselect(
        "市町村",
        options=sorted(df["municipality"].unique()),
        default=[]
    )
    
    # 指標選択
    metrics = st.sidebar.multiselect(
        "指標",
        options=list(METRIC_DISPLAY_NAMES.keys()),
        default=["facilities"]
    )
    
    # テーブル選択
    tables = st.sidebar.multiselect(
        "集計表",
        options=df["table"].unique().tolist(),
        default=df["table"].unique().tolist()
    )

    # フィルタリング
    q = df.query(
        "table in @tables and metric in @metrics and year >= @min_year and year <= @max_year and area in @areas"
    )
    
    if cities:
        q = q[q["municipality"].isin(cities)]
    
    if q.empty:
        st.warning("該当データがありません。サイドバーで条件を変更してください。")
        return

    # ピボットテーブル
    st.header("ピボットテーブル (市町村 × 年)")
    pivot = q.pivot_table(
        index=["municipality", "area"],
        columns="year",
        values="value",
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    
    st.dataframe(
        pivot.style.format(thousands=","),
        use_container_width=True
    )

    # グラフ表示
    st.header("市町村別推移グラフ")
    
    # 1軸: 軒数 (折れ線)
    fig = go.Figure()
    if "facilities" in metrics:
        facilities = q[q["metric"] == "facilities"]
        for city, g in facilities.groupby("municipality"):
            g = g.groupby("year")["value"].sum().reset_index()
            fig.add_trace(go.Scatter(
                x=g["year"],
                y=g["value"],
                mode="lines+markers",
                name=f"軒数: {city}",
                line=dict(width=2),
                yaxis="y1"
            ))

    # 2軸: 客室数/収容人数 (積み上げ棒)
    if any(m in metrics for m in ["rooms", "capacity"]):
        for metric in ["rooms", "capacity"]:
            if metric not in metrics: continue
            metric_df = q[q["metric"] == metric]
            for city, g in metric_df.groupby("municipality"):
                g = g.groupby("year")["value"].sum().reset_index()
                fig.add_trace(go.Bar(
                    x=g["year"],
                    y=g["value"],
                    name=f"{METRIC_DISPLAY_NAMES[metric]}: {city}",
                    yaxis="y2"
                ))

    # グラフ設定
    fig.update_layout(
        title="宿泊施設推移状況",
        xaxis_title="年",
        yaxis=dict(
            title="軒数（軒）",
            titlefont=dict(color="darkblue"),
            tickfont=dict(color="darkblue"),
            showgrid=True
        ),
        yaxis2=dict(
            title="客室数・収容人数",
            titlefont=dict(color="cornflowerblue"),
            tickfont=dict(color="cornflowerblue"),
            overlaying="y",
            side="right",
            showgrid=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode="x unified",
        barmode="stack",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    streamlit_main()
