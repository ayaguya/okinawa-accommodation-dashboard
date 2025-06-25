from pathlib import Path
from functools import lru_cache
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

DATA_DIR = Path(r"C:/Users/y-ham/CascadeProjects/okinawa-accommodation-dashboard/data/processed/all")

# -----------------------------------------------------------------------------
# 1. ページ設定
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="沖縄県宿泊施設ダッシュボード",
    page_icon="🏨",
    layout="wide",
)

st.title("🏨 沖縄県宿泊施設ダッシュボード")

# -----------------------------------------------------------------------------
# 2. データ読み込み
# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_data():
    """処理済み CSV ファイルを読み込む"""
    try:
        df = pd.read_csv(DATA_DIR / "okinawa_accommodation_tidy.csv")
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        st.stop()
    return df

# -----------------------------------------------------------------------------
# 3. データ加工
# -----------------------------------------------------------------------------
df = load_data()

# 年度順ソート
YEARS = sorted(df["year"].unique())

# 指標マップ
METRIC_MAP = {
    "施設数": "facilities",
    "客室数": "rooms",
    "収容人数": "capacity",
    "届出数": "notifications"
}

# エリアマップ
AREA_MAP = {
    "南部": ["那覇市", "糸満市", "豊見城市", "南城市", "与那原町", "南風原町", "八重瀬町"],
    "中部": ["沖縄市", "宜野湾市", "浦添市", "うるま市", "読谷村", "嘉手納町", "北谷町", "北中城村", "中城村", "西原町"],
    "北部": ["名護市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町", "恩納村", "宜野座村", "金武町"],
    "宮古": ["宮古島市", "多良間村"],
    "八重山": ["石垣市", "竹富町", "与那国町"],
    "離島": ["久米島町", "渡嘉敷村", "座間味村", "粟国村", "渡名喜村", "南大東村", "北大東村", "伊江村", "伊平屋村", "伊是名村"]
}

# -----------------------------------------------------------------------------
# 4. サイドバー
# -----------------------------------------------------------------------------
st.sidebar.header("フィルタ")

# エリア選択
selected_areas = st.sidebar.multiselect(
    "エリア",
    options=list(AREA_MAP.keys()),
    default=list(AREA_MAP.keys())
)

# 市町村選択
if selected_areas:
    cities = [city for area in selected_areas for city in AREA_MAP[area]]
    selected_cities = st.sidebar.multiselect(
        "市町村",
        options=cities,
        default=cities
    )
else:
    selected_cities = st.sidebar.multiselect(
        "市町村",
        options=sorted(df["municipality"].unique())
    )

# 年度範囲選択
min_year, max_year = st.sidebar.select_slider(
    "年度範囲",
    options=YEARS,
    value=(YEARS[0], YEARS[-1])
)

# 指標選択
metric = st.sidebar.selectbox(
    "指標",
    options=list(METRIC_MAP.keys())
)

# グラフタイプ選択
graph_type = st.sidebar.selectbox(
    "グラフタイプ",
    options=["折れ線", "棒グラフ"]
)

# -----------------------------------------------------------------------------
# 5. メイン表示
# -----------------------------------------------------------------------------

# データフィルタリング
filtered_df = df[
    (df["year"].between(min_year, max_year)) &
    (df["metric"] == METRIC_MAP[metric]) &
    (df["municipality"].isin(selected_cities))
]

# グラフ作成
if graph_type == "折れ線":
    fig = go.Figure()
    for city, grp in filtered_df.groupby("municipality"):
        fig.add_scatter(
            x=grp["year"],
            y=grp["value"],
            mode="lines+markers",
            name=city
        )
    fig.update_layout(
        title=f"{metric}の推移",
        xaxis_title="年度",
        yaxis_title=metric,
        hovermode="x unified",
        height=600
    )
else:  # 棒グラフ
    latest_year = filtered_df["year"].max()
    latest_df = filtered_df[filtered_df["year"] == latest_year]
    fig = go.Figure(
        data=[
            go.Bar(
                x=latest_df["municipality"],
                y=latest_df["value"],
                text=latest_df["value"],
                textposition="auto"
            )
        ]
    )
    fig.update_layout(
        title=f"{metric} ({latest_year}年)",
        xaxis_title="市町村",
        yaxis_title=metric,
        height=600
    )

# グラフ表示
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. データテーブル
# -----------------------------------------------------------------------------
with st.expander("🔍 データテーブル"):
    st.dataframe(
        filtered_df.sort_values(["municipality", "year"]),
        use_container_width=True,
        height=400
    )
