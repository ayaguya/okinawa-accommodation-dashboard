"""
# okinawa_accommodation_dashboard.py
# -------------------------------------------------------------
# 沖縄県宿泊施設ダッシュボード  (H30〜R5・Excel 自動取込版)
# -------------------------------------------------------------
# * Excel は data/raw/*.xlsx に保存（4 シート構成）
# * サイドバーでエリア・市町村・年度・指標を柔軟に選択
# * 軒数(折れ線) + 客室数/収容人数(積み上げ棒) の 2 軸表示
# * 地域／市町村ごとの推移・データテーブル
# * オプションで前年比増減数も計算
#
# 依存ライブラリ: streamlit, pandas, plotly, openpyxl
"""
from pathlib import Path
from functools import lru_cache
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 0. 定数・設定
# -----------------------------------------------------------------------------
DATA_DIR = Path(r"C:/Users/y-ham/CascadeProjects/okinawa-accommodation-dashboard/data/processed/all")

# データマップ
METRIC_MAP = {
    "施設数": "facilities",
    "客室数": "rooms",
    "収容人数": "capacity",
    "届出数": "notifications"
}

# エリア定義
REGION_DEFS = {
    "南部": ["那覇市", "糸満市", "豊見城市", "八重瀬町", "南城市", "与那原町", "南風原町"],
    "中部": ["沖縄市", "宜野湾市", "浦添市", "うるま市", "読谷村", "嘉手納町", "北谷町", "北中城村", "中城村", "西原町"],
    "北部": ["名護市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町", "恩納村", "宜野座村", "金武町"],
    "宮古": ["宮古島市", "多良間村"],
    "八重山": ["石垣市", "竹富町", "与那国町"],
    "離島": ["久米島町", "渡嘉敷村", "座間味村", "粟国村", "渡名喜村", "南大東村", "北大東村", "伊江村", "伊平屋村", "伊是名村"]
}

# -----------------------------------------------------------------------------
# 1. ストリームリット ページ設定
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="沖縄県宿泊施設ダッシュボード",
    page_icon="🏨",
    layout="wide",
)

st.markdown("""
<h1 style="text-align:center;">🏨 沖縄県宿泊施設データ<br>可視化ダッシュボード</h1>
""", unsafe_allow_html=True)

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

raw_df = load_data()

# -----------------------------------------------------------------------------
# 3. データ加工
# -----------------------------------------------------------------------------
df_all = raw_df[raw_df["metric"].isin(METRIC_MAP.values())].copy()
df_all["指標"] = df_all["metric"].map({v: k for k, v in METRIC_MAP.items()})
YEARS = sorted(df_all["year"].unique())

# 年度合計 (県全体表示用)
agg_pref = (
    df_all.groupby(["year", "指標"])["value"].sum()
    .reset_index()
    .pivot(index="year", columns="指標", values="value")
)

# -----------------------------------------------------------------------------
# 4. サイドバー フィルタ
# -----------------------------------------------------------------------------
st.sidebar.header("データ選択")
region_sel = st.sidebar.multiselect(
    "エリアを選択してください",
    options=list(REGION_DEFS.keys()),
    default=list(REGION_DEFS.keys())
)

city_options = sorted(df_all["municipality"].unique())
city_sel = st.sidebar.multiselect(
    "市町村を選択してください",
    options=city_options
)

min_year, max_year = st.sidebar.slider(
    "期間を選択してください",
    min_value=min(YEARS),
    max_value=max(YEARS),
    value=(min(YEARS), max(YEARS))
)

metric_multi = st.sidebar.multiselect(
    "要素を選択してください",
    options=list(METRIC_MAP.keys()),
    default=["施設数"]
)

show_delta = st.sidebar.checkbox("増減数(前年比)を表示", value=True)

# -----------------------------------------------------------------------------
# 5. 沖縄県全体の状況
# -----------------------------------------------------------------------------
st.header("沖縄県全体の状況")

fig_pref = go.Figure()

# 客室数と収容人数の積み上げ棒グラフ
if "客室数" in metric_multi:
    fig_pref.add_trace(
        go.Bar(
            x=agg_pref.index,
            y=agg_pref["客室数"],
            name="客室数（室）",
            marker_color="lightblue",
            yaxis="y2"
        )
    )
if "収容人数" in metric_multi:
    fig_pref.add_trace(
        go.Bar(
            x=agg_pref.index,
            y=agg_pref["収容人数"],
            name="収容人数（人）",
            marker_color="cornflowerblue",
            yaxis="y2"
        )
    )

# 軒数の折れ線グラフ
if "施設数" in metric_multi:
    fig_pref.add_trace(
        go.Scatter(
            x=agg_pref.index,
            y=agg_pref["施設数"],
            mode="lines+markers",
            name="施設数（軒）",
            line=dict(color="darkblue", width=2),
            marker=dict(size=8),
            yaxis="y1",
            hovertemplate="年: %{x}<br>軒数: %{y:,}軒<extra></extra>"
        )
    )

fig_pref.update_layout(
    title="沖縄県宿泊施設推移状況",
    xaxis=dict(title="年"),
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
    height=450
)

st.plotly_chart(fig_pref, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. エリア別の状況
# -----------------------------------------------------------------------------
st.header("エリアの状況")
if region_sel:
    for metric in metric_multi:
        st.subheader(f"選択エリアの{metric}の推移")
        fig_reg = go.Figure()
        tbl_reg = pd.DataFrame()

        for reg in region_sel:
            cities = REGION_DEFS[reg]
            df_reg = df_all[
                (df_all["指標"] == metric) &
                df_all["municipality"].isin(cities) &
                df_all["year"].between(min_year, max_year)
            ]
            if df_reg.empty:
                continue
            
            series = df_reg.groupby("year")["value"].sum()
            fig_reg.add_trace(
                go.Scatter(
                    x=series.index,
                    y=series.values,
                    mode="lines+markers",
                    name=reg
                )
            )
            tbl_reg[reg] = series

        fig_reg.update_layout(
            xaxis_title="年",
            yaxis_title=metric,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                y=1.02,
                x=0.5,
                xanchor="center"
            ),
            height=400
        )
        st.plotly_chart(fig_reg, use_container_width=True)
        
        if not tbl_reg.empty:
            st.dataframe(
                tbl_reg.T.astype(int).style.format(thousands=","),
                use_container_width=True
            )
else:
    st.info("エリアを選択するとグラフが表示されます。")

# -----------------------------------------------------------------------------
# 7. 市町村別の状況
# -----------------------------------------------------------------------------
st.header("市町村の状況")
if city_sel:
    for metric in metric_multi:
        st.subheader(f"{metric}の推移")
        fig_city = go.Figure()
        df_city = df_all[
            (df_all["指標"] == metric) &
            df_all["municipality"].isin(city_sel) &
            df_all["year"].between(min_year, max_year)
        ]

        # 表示順を最終年の値で並べ替え
        order = df_city[df_city["year"] == max_year]
        order = order.sort_values("value", ascending=False)["municipality"].tolist()
        
        for city in order:
            grp = df_city[df_city["municipality"] == city]
            fig_city.add_trace(
                go.Scatter(
                    x=grp["year"],
                    y=grp["value"],
                    mode="lines+markers",
                    name=city
                )
            )

        fig_city.update_layout(
            xaxis_title="年",
            yaxis_title=metric,
            hovermode="x unified",
            height=400
        )
        st.plotly_chart(fig_city, use_container_width=True)

        tbl_city = df_city.pivot(
            index="municipality",
            columns="year",
            values="value"
        ).fillna(0).astype(int)
        
        st.dataframe(
            tbl_city.style.format(thousands=","),
            use_container_width=True
        )
else:
    st.info("市町村を選択するとグラフが表示されます。")

# -----------------------------------------------------------------------------
# 8. エリア定義 (フッター)
# -----------------------------------------------------------------------------
st.markdown("""
---  
### エリアの内訳  
- **南部**: 那覇市、糸満市、豊見城市、八重瀬町、南城市、与那原町、南風原町  
- **中部**: 沖縄市、宜野湾市、浦添市、うるま市、読谷村、嘉手納町、北谷町、北中城村、中城村、西原町  
- **北部**: 名護市、国頭村、大宜味村、東村、今帰仁村、本部町、恩納村、宜野座村、金武町  
- **宮古**: 宮古島市、多良間村  
- **八重山**: 石垣市、竹富町、与那国町  
- **離島**: 久米島町、渡嘉敷村、座間味村、粟国村、渡名喜村、南大東村、北大東村、伊江村、伊平屋村、伊是名村  
""")
