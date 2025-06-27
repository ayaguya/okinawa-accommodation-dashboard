# -*- coding: utf-8 -*-
# okinawa_accommodation_dashboard.py
# =============================================================
# 沖縄県宿泊施設ダッシュボード  (S47〜R6)
# -------------------------------------------------------------
# ・県全体  : Transition.xlsx (total)
# ・エリア別 : REGION_MAP で定義した市町村を合算
# ・市町村別: all_years_long.csv (cat1==total)
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

# by_yearディレクトリのCSVファイルも統合して読み込む
BY_YEAR_DIR = Path("data/processed/by_year")

def load_all_data():
    """すべてのデータを統合して読み込む"""
    dfs = []
    
    # 既存のall_years_long.csvがあれば読み込む
    if CSV_LONG.exists():
        df_main = pd.read_csv(CSV_LONG, dtype={"year": int})
        dfs.append(df_main)
    
    # by_yearディレクトリから最新データを読み込む
    if BY_YEAR_DIR.exists():
        for csv_file in BY_YEAR_DIR.glob("long_*.csv"):
            try:
                df_year = pd.read_csv(csv_file, dtype={"year": int})
                # municipality列をcity列に統一
                if "municipality" in df_year.columns:
                    df_year = df_year.rename(columns={"municipality": "city"})
                dfs.append(df_year)
            except Exception as e:
                st.warning(f"ファイル {csv_file} の読み込みでエラー: {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    # すべてのデータを結合
    df_combined = pd.concat(dfs, ignore_index=True)
    
    # 重複を除去（同じyear, city, cat1, metric, tableの組み合わせ）
    df_combined = df_combined.drop_duplicates(subset=["year", "city", "cat1", "metric", "table"])
    
    return df_combined

ALL_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- 市町村コード ----------------
CITY_CODE = {
    # 市部
    "那覇市": 47201, "宜野湾市": 47205, "石垣市": 47207, "浦添市": 47208,
    "名護市": 47209, "糸満市": 47211, "沖縄市": 47212, "豊見城市": 47213,
    "うるま市": 47214, "宮古島市": 47215, "南城市": 47216,
    # 国頭郡
    "国頭村": 47301, "大宜味村": 47302, "東村": 47303,
    # 中頭郡
    "今帰仁村": 47322, "恩納村": 47323, "宜野座村": 47324, "金武町": 47325,
    "読谷村": 47326, "嘉手納町": 47327, "北谷町": 47328,
    "北中城村": 47329, "中城村": 47330, "西原町": 47331,
    # 島尻郡
    "与那原町": 47351, "南風原町": 47352, "渡嘉敷村": 47353,
    "座間味村": 47354, "粟国村": 47355, "渡名喜村": 47356,
    "南大東村": 47357, "北大東村": 47358,
    "伊平屋村": 47360, "伊是名村": 47361, "久米島町": 47362, "八重瀬町": 47363,
    # 宮古郡
    "多良間村": 47371,
    # 八重山郡
    "竹富町": 47381, "与那国町": 47382,
}

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

# ---------------- 宿泊形態の日本語ラベル ----------------
CAT1_JP2EN = {
    "ホテル・旅館":          "hotel_ryokan",
    "民宿":                  "minshuku",
    "ペンション・貸別荘":    "pension_villa",
    "ドミトリー・ゲストハウス": "dormitory_guesthouse",
    "ウィークリーマンション":    "weekly_mansion",
    "団体経営施設":          "group_facilities",
    "ユースホステル":        "youth_hostel",
}

# ---------------- 列名エイリアス ----------------
ALIASES = {
    "facilities": {"facilities", "facility", "軒数"},
    "rooms":      {"rooms", "room", "客室数"},
    "capacity":   {"capacity", "capac", "capacit", "収容人数"},
}

# ---------------- 県全体データ読み込み ----------------
def load_transition_total(path: Path) -> pd.DataFrame:
    """県全体 total (Transition.xlsx) を tidy 形式で返す"""
    if not path.exists():
        return pd.DataFrame()

    xls = pd.ExcelFile(path)
    sheet = next((s for s in xls.sheet_names if "total" in s.strip().lower()), xls.sheet_names[0])
    df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)

    # --- ヘッダ行検出 ------------------------------------------------
    hdr_idx = None
    for i, row in df_raw.iterrows():
        row_lc = row.astype(str).str.lower()
        if row_lc.str.contains("facilities|facility|軒数").any() and row_lc.str.contains("rooms|客室数").any():
            hdr_idx = i
            break
    if hdr_idx is None:
        st.error("Transition.xlsx → 必須列が見つかりません")
        return pd.DataFrame()

    header = df_raw.iloc[hdr_idx].fillna("").astype(str).str.strip().str.lower().tolist()
    data = df_raw.iloc[hdr_idx + 1:].reset_index(drop=True)
    data.columns = header

    # year 列を統一
    if data.columns[0] != "year":
        data = data.rename(columns={data.columns[0]: "year"})

    # 列名正規化
    ren = {}
    for std, alis in ALIASES.items():
        for c in data.columns:
            if c.strip().lower() in alis:
                ren[c] = std
                break
    data = data.rename(columns=ren)
    if not {"facilities", "rooms", "capacity"}.issubset(data.columns):
        st.error("Transition.xlsx → facilities/rooms/capacity 列不足")
        return pd.DataFrame()

    # 数値化
    for col in ["facilities", "rooms", "capacity"]:
        data[col] = (
            pd.to_numeric(
                data[col].astype(str)
                       .str.replace(r"[,　\s]", "", regex=True)
                       .str.replace("－", "0"), errors="coerce")
              .fillna(0)
              .astype(int)
        )

    # 和暦→西暦
    def to_yyyy(s):
        s = str(s).strip().upper().replace("年", "")
        if s.startswith("S") or s.startswith("昭和"):
            return 1925 + int(s.lstrip("S昭和"))
        if s.startswith("H") or s.startswith("平成"):
            return 1988 + int(s.lstrip("H平成"))
        if s.startswith("R") or s.startswith("令和"):
            return 2018 + int(s.lstrip("R令和"))
        return int(s)

    data["year"] = data["year"].apply(to_yyyy)

    tidy = data.melt(id_vars="year", var_name="metric", value_name="value")
    tidy[["city", "table", "cat1", "cat2"]] = ["沖縄県", "pref_transition", "total", ""]
    return tidy

# ---------------- ヘルパー関数 ----------------
def create_line_chart(df, target_list, title, y_label="軒数", show_legend=False, df_all=None, show_ranking=True):
    """共通のライングラフ作成関数
    
    Args:
        df: 表示用データフレーム
        target_list: 表示対象のリスト
        title: グラフタイトル
        y_label: Y軸ラベル
        show_legend: 凡例表示フラグ（デフォルト：False）
        df_all: 全体データ（41市町村全体での順位計算用）
        show_ranking: 順位表示フラグ（デフォルト：True）
    """
    # 41市町村のみの順位計算
    all_rankings = {}
    if show_ranking and df_all is not None and len(df_all) > 0:
        # 沖縄県とエリアを除外した41市町村のみのリスト
        exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
        municipalities_only = [col for col in df_all.columns if col not in exclude_list]
        
        for year in df.index:
            if year in df_all.index:
                # その年の市町村のみの値を取得
                year_data = df_all.loc[year, municipalities_only]
                year_data_clean = year_data.fillna(0)
                
                # 値で降順ソート
                sorted_data = year_data_clean.sort_values(ascending=False)
                
                # 順位を計算
                rankings = {}
                for rank, (city, value) in enumerate(sorted_data.items(), 1):
                    rankings[city] = rank
                
                all_rankings[year] = rankings
    
    # 最終年の値で降順ソート（初期表示順序）
    if len(df) > 0 and len(df.columns) > 0:
        latest_year = df.index.max()
        if latest_year in df.index:
            latest_values = df.loc[latest_year].fillna(0)
            sorted_targets = sorted([t for t in target_list if t in df.columns], 
                                  key=lambda x: latest_values.get(x, 0), 
                                  reverse=True)
        else:
            sorted_targets = [t for t in target_list if t in df.columns]
    else:
        sorted_targets = target_list
    
    fig = go.Figure()
    
    # カスタムカラーパレット
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
              '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for i, item in enumerate(sorted_targets):
        if item not in df.columns:
            continue
        
        if show_ranking and all_rankings:
            # 市町村別：順位情報を含めたホバーテンプレート
            custom_data = []
            for year in df.index:
                rank = all_rankings.get(year, {}).get(item, '-')
                custom_data.append(rank)
            
            hovertemplate = (f"<b>{item}</b><br>" +
                           f"{y_label}: %{{y:,}}<br>" +
                           f"順位: %{{customdata}}/41" +
                           "<extra></extra>")
        else:
            # エリア別：順位なしのホバーテンプレート
            custom_data = None
            hovertemplate = (f"<b>{item}</b><br>" +
                           f"{y_label}: %{{y:,}}" +
                           "<extra></extra>")
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[item],
                mode="lines+markers",
                name=item,
                customdata=custom_data,
                hovertemplate=hovertemplate,
                line=dict(width=2, color=colors[i % len(colors)]),
                marker=dict(size=6, color=colors[i % len(colors)])
            )
        )
    
    fig.update_layout(
        title=title,
        hovermode="x unified",
        height=450,
        showlegend=show_legend,
        xaxis_title="年",
        yaxis_title=y_label,
        margin=dict(l=60, r=30, t=60, b=40)
    )
    
    return fig

# ---------------- メイン ----------------
def main():
    st.set_page_config(page_title="沖縄県宿泊施設データ可視化", page_icon="🏨", layout="wide")
    st.title("沖縄県宿泊施設データ可視化アプリ")

    # ===== 県全体 =====
    st.header("📈 沖縄県全体の状況")
    pref_df = load_transition_total(TRANSITION_XLSX)
    if pref_df.empty:
        st.error("Transition.xlsx を読み込めませんでした")
        return

    pref_pivot = (
        pref_df.pivot_table(index="year", columns="metric", values="value", aggfunc="sum")
                .sort_index()
                .rename(columns={"facilities": "軒数", "rooms": "客室数", "capacity": "収容人数"})
    )

    latest_year = pref_pivot.index.max()
    latest = pref_pivot.loc[latest_year]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"総施設数（{latest_year}年）", f"{latest['軒数']:,} 軒")
    c2.metric(f"総客室数（{latest_year}年）", f"{latest['客室数']:,} 室")
    c3.metric(f"総収容人数（{latest_year}年）", f"{latest['収容人数']:,} 人")

    fig_pref = make_subplots(specs=[[{"secondary_y": True}]])
    fig_pref.add_bar(
        x=pref_pivot.index,
        y=pref_pivot["客室数"],
        name="客室数（室）",
        marker_color="lightblue",
        opacity=0.8,
        hovertemplate="客室数 %{y:,} 室<extra></extra>",
    )
    fig_pref.add_bar(
        x=pref_pivot.index,
        y=pref_pivot["収容人数"],
        name="収容人数（人）",
        marker_color="cornflowerblue",
        opacity=0.8,
        hovertemplate="収容人数 %{y:,} 人<extra></extra>",
    )
    fig_pref.add_scatter(
        x=pref_pivot.index,
        y=pref_pivot["軒数"],
        mode="lines+markers",
        name="軒数（軒）",
        line=dict(color="darkblue", width=3),
        marker=dict(size=8),
        hovertemplate="軒数 %{y:,} 軒<extra></extra>",
        secondary_y=True,
    )
    fig_pref.update_layout(
        title="沖縄県宿泊施設推移状況 (S47→R6, total)",
        xaxis_title="年",
        yaxis_title="客室数・収容人数",
        yaxis2_title="軒数（軒）",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
        height=550,
        margin=dict(l=60, r=30, t=80, b=50),
    )
    st.plotly_chart(fig_pref, use_container_width=True)

    # ===== データ読み込み =====
    df_long = load_all_data()
    if df_long.empty:
        st.warning("データファイルが見つかりません")
        return

    df_long = df_long.assign(
        city=lambda d: d["city"].str.strip(),
        cat1=lambda d: d["cat1"].fillna("").str.lower().str.strip(),
        metric=lambda d: d["metric"].str.lower().str.strip(),
        value=lambda d: pd.to_numeric(d["value"], errors="coerce").fillna(0).astype(int)
    )
    df_long = df_long.query("table == 'accommodation_type' & metric in ['facilities','rooms','capacity']")

    # 市町村リスト（市町村コード順）
    all_municipalities = sorted(CITY_CODE.keys(), key=CITY_CODE.get)
    
    st.markdown("---")

    # ===== タブで分離 =====
    tab1, tab2 = st.tabs(["🗺️ エリア別分析", "🏘️ 市町村別分析"])

    # =================================================
    # エリア別分析タブ
    # =================================================
    with tab1:
        st.header("🗺️ エリア別の状況")
        
        # サイドバー（エリア用）
        with st.sidebar:
            st.header("📊 エリア別設定")
            
            area_names = list(REGION_MAP.keys())
            sel_areas = st.multiselect(
                "エリアを選択してください",
                area_names,
                default=["南部", "中部"],
                key="areas"
            )
            
            # 宿泊形態
            st.subheader("🏨 宿泊形態")
            cat1_jp_all = list(CAT1_JP2EN.keys())
            sel_cat1_jp_area = st.multiselect(
                "宿泊形態（複数選択可）", 
                cat1_jp_all, 
                default=["ホテル・旅館"],
                key="cat1_area"
            )
            sel_cat1_en_area = [CAT1_JP2EN[jp] for jp in sel_cat1_jp_area]
            
            # 指標
            elem_map = {"軒数":"facilities","客室数":"rooms","収容人数":"capacity"}
            sel_elems_area = st.multiselect(
                "指標", 
                list(elem_map.keys()), 
                default=["軒数"],
                key="elems_area"
            )
            
            # 年度
            max_y = int(df_long["year"].max()) if not df_long.empty else 2024
            min_y = int(df_long["year"].min()) if not df_long.empty else 2007
            year_range_area = st.slider(
                "期間", min_y, max_y, (2007, 2024), step=1, key="year_area"
            )

        if sel_areas:
            # city → area の逆引き辞書
            city_to_area = {c: r for r, lst in REGION_MAP.items() for c in lst}
            
            # 選択された指標ごとに処理
            for element in sel_elems_area:
                metric_en = elem_map[element]
                
                st.subheader(f"📊 {element}の推移")
                
                # 1. Total（全宿泊形態合計）のグラフ
                st.write(f"**{element} (Total - 全宿泊形態合計)**")
                df_area_total = (
                    df_long.query(
                        f"metric == '{metric_en}' & cat1 == 'total' & "
                        "city in @city_to_area.keys() & "
                        f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                    )
                    .assign(area=lambda d: d["city"].map(city_to_area))
                    .groupby(["area", "year"])['value'].sum()
                    .unstack("area")
                    .reindex(columns=sel_areas)
                    .sort_index()
                )

                fig_area_total = create_line_chart(
                    df_area_total, sel_areas, 
                    f"エリア別{element}推移（Total） ({year_range_area[0]}-{year_range_area[1]})",
                    element,
                    show_legend=False,
                    df_all=None,  # エリア別では順位計算不要
                    show_ranking=False  # エリア別では順位表示なし
                )
                st.plotly_chart(fig_area_total, use_container_width=True)

                # Total のデータテーブル（グラフの下に配置）
                st.dataframe(
                    df_area_total.transpose().style.format(thousands=","),
                    use_container_width=True
                )

                # 2. 選択された宿泊形態ごとのグラフ
                if sel_cat1_en_area:
                    for i, (cat1_jp, cat1_en) in enumerate(zip(sel_cat1_jp_area, sel_cat1_en_area)):
                        st.write(f"**{element} ({cat1_jp})**")
                        
                        df_area_category = (
                            df_long.query(
                                f"metric == '{metric_en}' & cat1 == '{cat1_en}' & "
                                "city in @city_to_area.keys() & "
                                f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                            )
                            .assign(area=lambda d: d["city"].map(city_to_area))
                            .groupby(["area", "year"])['value'].sum()
                            .unstack("area")
                            .reindex(columns=sel_areas)
                            .sort_index()
                        )

                        fig_area_category = create_line_chart(
                            df_area_category, sel_areas,
                            f"エリア別{element}推移（{cat1_jp}） ({year_range_area[0]}-{year_range_area[1]})",
                            element,
                            show_legend=False,
                            df_all=None,  # エリア別では順位計算不要
                            show_ranking=False  # エリア別では順位表示なし
                        )
                        st.plotly_chart(fig_area_category, use_container_width=True)

                        # 宿泊形態別データテーブル（グラフの下に配置）
                        st.dataframe(
                            df_area_category.transpose().style.format(thousands=","),
                            use_container_width=True
                        )
                
                # 指標間の区切り
                if element != sel_elems_area[-1]:  # 最後の指標でなければ区切り線を追加
                    st.markdown("---")
        else:
            st.info("左のサイドバーからエリアを選択してください。")

    # =================================================
    # 市町村別分析タブ
    # =================================================
    with tab2:
        st.header("🏘️ 市町村別の状況")
        
        # サイドバー（市町村用）
        with st.sidebar:
            st.header("📊 市町村別設定")
            
            sel_cities = st.multiselect(
                "市町村を選択してください",
                all_municipalities,  # 既にコード順でソート済み
                default=[],
                key="cities"
            )
            
            # 宿泊形態
            st.subheader("🏨 宿泊形態")
            sel_cat1_jp_city = st.multiselect(
                "宿泊形態（複数選択可）", 
                cat1_jp_all, 
                default=["ホテル・旅館"],
                key="cat1_city"
            )
            sel_cat1_en_city = [CAT1_JP2EN[jp] for jp in sel_cat1_jp_city]
            
            # 指標
            sel_elems_city = st.multiselect(
                "指標", 
                list(elem_map.keys()), 
                default=["軒数"],
                key="elems_city"
            )
            
            # 年度
            year_range_city = st.slider(
                "期間", min_y, max_y, (2007, 2024), step=1, key="year_city"
            )

        if sel_cities:
            # 選択された指標ごとに処理
            for element in sel_elems_city:
                metric_en = elem_map[element]
                
                st.subheader(f"📊 {element}の推移")
                
                # 1. Total（全宿泊形態合計）のグラフ
                st.write(f"**{element} (Total - 全宿泊形態合計)**")
                total_df = (
                    df_long.query(
                        f"metric=='{metric_en}' & cat1=='total' & city in @sel_cities & "
                        f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                    )
                    .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                    .reindex(columns=[city for city in all_municipalities if city in sel_cities])
                    .sort_index()
                )

                # 41市町村全体データを取得
                df_all_cities = (
                    df_long.query(
                        f"metric=='{metric_en}' & cat1=='total' & "
                        f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                    )
                    .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                    .sort_index()
                )

                fig_total = create_line_chart(
                    total_df, [city for city in all_municipalities if city in sel_cities],
                    f"市町村別{element}推移（Total） ({year_range_city[0]}-{year_range_city[1]})",
                    element,
                    show_legend=False,
                    df_all=df_all_cities,  # 41市町村全体での順位計算用
                    show_ranking=True  # 市町村別では順位表示あり
                )
                st.plotly_chart(fig_total, use_container_width=True)

                # Total のデータテーブル（グラフの下に配置）
                sorted_cities = [city for city in all_municipalities if city in total_df.columns]
                st.dataframe(
                    total_df[sorted_cities].transpose().style.format(thousands=","),
                    use_container_width=True
                )

                # 2. 選択された宿泊形態ごとのグラフ
                if sel_cat1_en_city:
                    for i, (cat1_jp, cat1_en) in enumerate(zip(sel_cat1_jp_city, sel_cat1_en_city)):
                        st.write(f"**{element} ({cat1_jp})**")
                        
                        df_category = (
                            df_long.query(
                                f"metric == '{metric_en}' & cat1 == '{cat1_en}' & "
                                "city in @sel_cities & "
                                f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                            )
                            .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                            .reindex(columns=[city for city in all_municipalities if city in sel_cities])
                            .sort_index()
                        )

                        # 宿泊形態別の41市町村全体データを取得
                        df_all_cities_cat = (
                            df_long.query(
                                f"metric == '{metric_en}' & cat1 == '{cat1_en}' & "
                                f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                            )
                            .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                            .sort_index()
                        )

                        fig_category = create_line_chart(
                            df_category, [city for city in all_municipalities if city in sel_cities],
                            f"市町村別{element}推移（{cat1_jp}） ({year_range_city[0]}-{year_range_city[1]})",
                            element,
                            show_legend=False,
                            df_all=df_all_cities_cat,  # 宿泊形態別の41市町村全体での順位計算用
                            show_ranking=True  # 市町村別では順位表示あり
                        )
                        st.plotly_chart(fig_category, use_container_width=True)

                        # 宿泊形態別データテーブル（グラフの下に配置）
                        sorted_cities = [city for city in all_municipalities if city in df_category.columns]
                        st.dataframe(
                            df_category[sorted_cities].transpose().style.format(thousands=","),
                            use_container_width=True
                        )
                
                # 指標間の区切り
                if element != sel_elems_city[-1]:  # 最後の指標でなければ区切り線を追加
                    st.markdown("---")
        else:
            st.info("左のサイドバーから市町村を選択してください。")

    # ===== エリア構成 & 出典 =====
    st.markdown("---")
    st.header("🗾 エリアの内訳")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """**南部**: 那覇市, 糸満市, 豊見城市, 八重瀬町, 南城市, 与那原町, 南風原町  
**中部**: 沖縄市, 宜野湾市, 浦添市, うるま市, 読谷村, 嘉手納町, 北谷町, 北中城村, 中城村, 西原町  
**北部**: 名護市, 国頭村, 大宜味村, 東村, 今帰仁村, 本部町, 恩納村, 宜野座村, 金武町"""
        )
    with col2:
        st.markdown(
            """**宮古**: 宮古島市, 多良間村  
**八重山**: 石垣市, 竹富町, 与那国町  
**離島**: 久米島町, 渡嘉敷村, 座間味村, 粟国村, 渡名喜村, 南大東村, 北大東村, 伊江村, 伊平屋村, 伊是名村"""
        )

    st.markdown("---")
    st.markdown(
        "本データは、[沖縄県宿泊施設実態調査](https://www.pref.okinawa.jp/shigoto/kankotokusan/1011671/1011816/1003416/1026290.html) を基に独自に集計・加工したものです。"
    )

if __name__ == "__main__":
    main()