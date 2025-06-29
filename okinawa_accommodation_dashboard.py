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

# Streamlitページ設定（最初に実行する必要がある）
st.set_page_config(page_title="沖縄県宿泊施設データ可視化", page_icon="🏨", layout="wide")

RAW_DIR = Path("data/raw")
ALL_DIR = Path("data/processed/all")
TRANSITION_XLSX = RAW_DIR / "Transition.xlsx"
CSV_LONG = ALL_DIR / "all_years_long.csv"

# by_yearディレクトリのCSVファイルも統合して読み込む
BY_YEAR_DIR = Path("data/processed/by_year")

def load_all_data():
    """
    すべてのデータを統合して読み込む。
    アプリが利用できる整形済みの「long_」で始まるファイルのみを対象とする。
    """
    dfs = []
    
    # by_year ディレクトリから 'long_' で始まるCSVを読み込む
    if BY_YEAR_DIR.exists():
        # sortedでファイル読み込み順を固定し、一貫性を担保
        for csv_file in sorted(BY_YEAR_DIR.glob("long_*.csv")):
            try:
                df = pd.read_csv(csv_file, dtype={"year": int})
                
                # 列名の統一
                if "municipality" in df.columns:
                    df = df.rename(columns={"municipality": "city"})
                
                # hotel_breakdownデータの特別処理
                if "hotel_breakdown" in str(csv_file):
                    df = process_hotel_breakdown_data_fixed(df)
                
                if not df.empty:
                    dfs.append(df)
                    
            except Exception as e:
                st.warning(f"ファイル {csv_file} の読み込みでエラー: {e}")

    # 既存の統合ファイル(all_years_long.csv)も読み込む
    if CSV_LONG.exists():
        try:
            df_existing = pd.read_csv(CSV_LONG, dtype={"year": int})
            if not df_existing.empty:
                dfs.append(df_existing)
        except Exception as e:
            st.warning(f"統合ファイル読み込みエラー: {e}")

    if not dfs:
        return pd.DataFrame()

    # すべてのデータを結合
    df_combined = pd.concat(dfs, ignore_index=True)
    
    # 重複除去：'last'を保持することで、新しい年のデータ（例：long_2024.csv）が古い統合データ（all_years_long.csv）を上書きするようにする
    df_combined = df_combined.drop_duplicates(subset=["year", "city", "cat1", "metric", "table"], keep='last')
    
    return df_combined


def process_hotel_breakdown_data_fixed(df):
    """
    hotel_breakdownデータの修正版処理関数
    CSVの構造が正しい場合はそのまま返し、問題がある場合のみ修正を試みる
    """
    try:
        # 期待される列が存在するかチェック
        required_cols = ['year', 'city', 'metric', 'cat1', 'table', 'value']
        
        if all(col in df.columns for col in required_cols):
            # 基本的な列が揃っている場合
            
            # データ型の修正
            df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0).astype(int)
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype(int)
            
            # 空白やNaNの処理
            df['city'] = df['city'].fillna('').astype(str).str.strip()
            df['metric'] = df['metric'].fillna('').astype(str).str.strip()
            df['cat1'] = df['cat1'].fillna('').astype(str).str.strip()
            df['table'] = df['table'].fillna('').astype(str).str.strip()
            
            # 明らかに無効なデータを除外
            df = df[df['city'] != '']
            df = df[df['metric'] != '']
            df = df[df['cat1'] != '']
            
            return df
        else:
            st.warning(f"hotel_breakdownデータの列構造が期待と異なります。期待: {required_cols}, 実際: {list(df.columns)}")
            return df
            
    except Exception as e:
        st.error(f"hotel_breakdownデータの処理でエラー: {e}")
        return df


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
    """共通のライングラフ作成関数"""
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

# ---------------- メイン関数 ----------------
def main():
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
    df_long = df_long.query("metric in ['facilities','rooms','capacity']")

    # 市町村リスト（市町村コード順）
    all_municipalities = sorted(CITY_CODE.keys(), key=CITY_CODE.get)
    
    # 年度範囲の設定
    max_y = int(df_long["year"].max()) if not df_long.empty else 2024
    min_y = int(df_long["year"].min()) if not df_long.empty else 2007
    
    st.markdown("---")

    # ===== タブで分離 =====
    tab1, tab2, tab3, tab4 = st.tabs(["🏘️ 市町村別分析", "🏨 ホテル・旅館特化　規模別分析", "🏛️ ホテル・旅館特化　宿泊形態別分析", "🗺️ エリア別分析"])

    # シート選択オプション
    sheet_options = {
        "宿泊形態別": "accommodation_type",
        "規模分類": "scale_class"
    }
    
    # 宿泊形態の日本語表示マッピング
    accommodation_type_mapping = {
        "hotel_ryokan": "ホテル・旅館",
        "minshuku": "民宿", 
        "pension_villa": "ペンション・貸別荘",
        "dormitory_guesthouse": "ドミトリー・ゲストハウス",
        "weekly_mansion": "ウィークリーマンション",
        "group_facilities": "団体経営施設",
        "youth_hostel": "ユースホステル"
    }
    
    # 規模分類の日本語表示マッピング
    scale_class_mapping = {
        "large": "大規模（300人以上）",
        "medium": "中規模（100人以上300人未満）", 
        "small": "小規模（100人未満）"
    }

    # 指標マッピング
    elem_map = {"軒数":"facilities","客室数":"rooms","収容人数":"capacity"}

    # =================================================
    # TAB 1: 市町村別分析（accommodation_typeのみ）
    # =================================================
    with tab1:
        st.header("🏘️ 市町村別の状況")
        
        # accommodation_type（宿泊形態別）データをフィルタ
        df_accommodation = df_long.query("table == 'accommodation_type'")
        
        if df_accommodation.empty:
            st.warning("accommodation_typeのデータが見つかりません")
            possible_tables = df_long['table'].unique()
            st.write(f"利用可能なテーブル: {possible_tables}")
        else:
            # 市町村選択
            sel_cities = st.multiselect(
                "市町村を選択してください",
                all_municipalities,
                default=[],
                key="cities"
            )
            
            # 宿泊形態別カテゴリの取得
            accommodation_categories = sorted([cat for cat in df_accommodation['cat1'].unique() if cat and cat != 'total'])
            
            # 英語キーを日本語表示に変換
            accommodation_categories_jp = []
            for cat in accommodation_categories:
                if cat in accommodation_type_mapping:
                    accommodation_categories_jp.append(accommodation_type_mapping[cat])
                else:
                    accommodation_categories_jp.append(cat)
            
            show_details_city = st.checkbox("詳細項目を表示", value=False, key="city_show_details")
            if show_details_city:
                # デフォルトでホテル・旅館、民宿、ペンション・貸別荘を選択
                default_categories_jp = ["ホテル・旅館", "民宿", "ペンション・貸別荘"]
                # 利用可能なカテゴリの中からデフォルト項目をフィルタ
                available_defaults = [cat for cat in default_categories_jp if cat in accommodation_categories_jp]
                
                sel_categories_city_jp = st.multiselect(
                    "宿泊形態詳細項目",
                    accommodation_categories_jp,
                    default=available_defaults if available_defaults else accommodation_categories_jp[:3],
                    key="city_categories"
                )
                # 日本語表示から英語キーに逆変換
                reverse_mapping_city = {v: k for k, v in accommodation_type_mapping.items()}
                sel_categories_city = [reverse_mapping_city.get(cat_jp, cat_jp) for cat_jp in sel_categories_city_jp]
            else:
                sel_categories_city = []
            
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
                    
                    st.subheader(f"📊 {element}の推移（宿泊形態別）")
                    
                    # 1. Total（全宿泊形態合計）のグラフ
                    st.write(f"**{element} (Total - 全宿泊形態合計)**")
                    total_df = (
                        df_accommodation.query(
                            f"metric==@metric_en & cat1=='total' & city in @sel_cities & "
                            f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                        )
                        .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                        .reindex(columns=[city for city in all_municipalities if city in sel_cities])
                        .sort_index()
                    )

                    # 41市町村全体データを取得
                    df_all_cities = (
                        df_accommodation.query(
                            f"metric==@metric_en & cat1=='total' & "
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
                        df_all=df_all_cities,
                        show_ranking=True
                    )
                    st.plotly_chart(fig_total, use_container_width=True)

                    # Total のデータテーブル
                    sorted_cities = [city for city in all_municipalities if city in total_df.columns]
                    st.dataframe(
                        total_df[sorted_cities].transpose().style.format(thousands=","),
                        use_container_width=True
                    )

                    # 2. 選択された宿泊形態ごとのグラフ
                    if sel_categories_city:
                        for i, category in enumerate(sel_categories_city):
                            # 日本語表示名を取得
                            category_display = accommodation_type_mapping.get(category, category)
                            st.write(f"**{element} ({category_display})**")
                            
                            df_category = (
                                df_accommodation.query(
                                    f"metric == @metric_en & cat1 == @category & "
                                    "city in @sel_cities & "
                                    f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .reindex(columns=[city for city in all_municipalities if city in sel_cities])
                                .sort_index()
                            )

                            # 詳細項目別の41市町村全体データを取得
                            df_all_cities_cat = (
                                df_accommodation.query(
                                    f"metric == @metric_en & cat1 == @category & "
                                    f"year >= {year_range_city[0]} & year <= {year_range_city[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .sort_index()
                            )

                            fig_category = create_line_chart(
                                df_category, [city for city in all_municipalities if city in sel_cities],
                                f"市町村別{element}推移（{category_display}） ({year_range_city[0]}-{year_range_city[1]})",
                                element,
                                show_legend=False,
                                df_all=df_all_cities_cat,
                                show_ranking=True
                            )
                            st.plotly_chart(fig_category, use_container_width=True)

                            # データテーブル
                            sorted_cities = [city for city in all_municipalities if city in df_category.columns]
                            st.dataframe(
                                df_category[sorted_cities].transpose().style.format(thousands=","),
                                use_container_width=True
                            )
                    
                    # 指標間の区切り
                    if element != sel_elems_city[-1]:
                        st.markdown("---")
            else:
                st.info("市町村を選択してください。")

    # =================================================
    # TAB 2: ホテル・旅館特化　規模別分析
    # =================================================
    with tab2:
        st.header("🏨 ホテル・旅館特化　規模別分析の状況")
        
        # scale_class（規模別）データをフィルタ
        df_scale = df_long.query("table == 'scale_class'")
        
        if df_scale.empty:
            st.warning("scale_classのデータが見つかりません")
            possible_tables = df_long['table'].unique()
            st.write(f"利用可能なテーブル: {possible_tables}")
        else:
            # 規模別カテゴリの取得
            scale_categories = sorted([cat for cat in df_scale['cat1'].unique() if cat and cat != 'total'])
            
            # 英語キーを日本語表示に変換
            scale_categories_jp = []
            for cat in scale_categories:
                if cat in scale_class_mapping:
                    scale_categories_jp.append(scale_class_mapping[cat])
                else:
                    scale_categories_jp.append(cat)
            
            # 市町村選択
            sel_targets_scale = st.multiselect(
                "市町村を選択してください",
                all_municipalities,
                default=[],
                key="scale_cities"
            )
            
            # 規模分類（日本語表示）- デフォルトで全て選択
            sel_scale_categories_jp = st.multiselect(
                "規模分類（複数選択可）",
                scale_categories_jp,
                default=scale_categories_jp,
                key="scale_categories"
            )
            
            # 日本語表示から英語キーに逆変換
            reverse_scale_mapping = {v: k for k, v in scale_class_mapping.items()}
            sel_scale_categories = [reverse_scale_mapping.get(cat_jp, cat_jp) for cat_jp in sel_scale_categories_jp]
            
            # 指標
            sel_elems_scale = st.multiselect(
                "指標", 
                list(elem_map.keys()), 
                default=["軒数"],
                key="elems_scale"
            )
            
            # 年度
            year_range_scale = st.slider(
                "期間", min_y, max_y, (2007, 2024), step=1, key="year_scale"
            )

            if sel_targets_scale:
                # 選択された指標ごとに処理
                for element in sel_elems_scale:
                    metric_en = elem_map[element]
                    
                    st.subheader(f"📊 {element}の推移")
                    
                    # 1. Total（全規模合計）のグラフ
                    st.write(f"**{element} (Total - 全規模合計)**")
                    total_df = (
                        df_scale.query(
                            f"metric==@metric_en & cat1=='total' & city in @sel_targets_scale & "
                            f"year >= {year_range_scale[0]} & year <= {year_range_scale[1]}"
                        )
                        .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                        .reindex(columns=[city for city in all_municipalities if city in sel_targets_scale])
                        .sort_index()
                    )

                    # 41市町村全体データを取得
                    df_all_cities = (
                        df_scale.query(
                            f"metric==@metric_en & cat1=='total' & "
                            f"year >= {year_range_scale[0]} & year <= {year_range_scale[1]}"
                        )
                        .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                        .sort_index()
                    )

                    fig_total = create_line_chart(
                        total_df, [city for city in all_municipalities if city in sel_targets_scale],
                        f"市町村別{element}推移（Total規模） ({year_range_scale[0]}-{year_range_scale[1]})",
                        element,
                        show_legend=False,
                        df_all=df_all_cities,
                        show_ranking=True
                    )
                    st.plotly_chart(fig_total, use_container_width=True)

                    sorted_cities = [city for city in all_municipalities if city in total_df.columns]
                    st.dataframe(
                        total_df[sorted_cities].transpose().style.format(thousands=","),
                        use_container_width=True
                    )

                    # 2. 選択された規模分類ごとのグラフ
                    if sel_scale_categories:
                        for i, cat in enumerate(sel_scale_categories):
                            # 日本語表示名を取得
                            cat_display = scale_class_mapping.get(cat, cat)
                            st.write(f"**{element} ({cat_display})**")
                            
                            df_category = (
                                df_scale.query(
                                    f"metric == @metric_en & cat1 == @cat & "
                                    "city in @sel_targets_scale & "
                                    f"year >= {year_range_scale[0]} & year <= {year_range_scale[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .reindex(columns=[city for city in all_municipalities if city in sel_targets_scale])
                                .sort_index()
                            )

                            # 規模分類別の41市町村全体データを取得
                            df_all_cities_cat = (
                                df_scale.query(
                                    f"metric == @metric_en & cat1 == @cat & "
                                    f"year >= {year_range_scale[0]} & year <= {year_range_scale[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .sort_index()
                            )

                            fig_category = create_line_chart(
                                df_category, [city for city in all_municipalities if city in sel_targets_scale],
                                f"市町村別{element}推移（{cat_display}） ({year_range_scale[0]}-{year_range_scale[1]})",
                                element,
                                show_legend=False,
                                df_all=df_all_cities_cat,
                                show_ranking=True
                            )
                            st.plotly_chart(fig_category, use_container_width=True)

                            sorted_cities = [city for city in all_municipalities if city in df_category.columns]
                            st.dataframe(
                                df_category[sorted_cities].transpose().style.format(thousands=","),
                                use_container_width=True
                            )
                    
                    # 指標間の区切り
                    if element != sel_elems_scale[-1]:
                        st.markdown("---")
            else:
                st.info("市町村を選択してください。")

    # =================================================
    # TAB 3: ホテル・旅館特化　宿泊形態別分析（hotel_breakdown H26-R6）
    # =================================================
    with tab3:
        st.header("🏛️ ホテル・旅館特化　宿泊形態別分析の状況")

        # hotel_breakdown（ホテル・旅館特化）データをフィルタ
        try:
            df_hotel_breakdown = df_long.query("table == 'hotel_breakdown'")
        except Exception as e:
            st.error(f"データクエリエラー: {e}")
            df_hotel_breakdown = pd.DataFrame()
        
        if df_hotel_breakdown.empty:
            st.warning("⚠️ hotel_breakdownのデータが見つかりません。")
            st.info("このタブの分析には、ホテル・旅館の詳細な分類データ（リゾートホテル、ビジネスホテル等）が必要です。")
            st.info("📌 **解決策**: 事前に整形済みの `long_..._hotel_breakdown.csv` ファイルを `data/processed/by_year` に配置してください。")
            
            # データベースの状況を表示
            st.write("**現在のデータ状況:**")
            available_tables = df_long['table'].unique() if not df_long.empty else []
            st.write(f"利用可能なテーブル: {list(available_tables)}")
            
        else:
            # hotel_breakdownのデータをH26-R6に限定
            df_hotel_breakdown = df_hotel_breakdown.query("year >= 2014 & year <= 2024")
            
            if df_hotel_breakdown.empty:
                st.warning("H26～R6期間のhotel_breakdownデータが見つかりません。データの年度範囲を確認してください。")
            else:
                hotel_min_year = 2014
                hotel_max_year = 2024
                
                # ===== 共通設定エリア =====
                st.subheader("🎛️ 分析設定")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 市町村選択
                    sel_targets_hotel = st.multiselect(
                        "市町村を選択",
                        all_municipalities,
                        default=["宮古島市"] if "宮古島市" in all_municipalities else [],
                        key="hotel_cities"
                    )
                    
                    # 指標選択
                    sel_elems_hotel = st.multiselect(
                        "指標", 
                        list(elem_map.keys()), 
                        default=["軒数"],
                        key="elems_hotel"
                    )
                
                with col2:
                    # 年度選択
                    year_range_hotel = st.slider(
                        "期間", hotel_min_year, hotel_max_year, (hotel_min_year, hotel_max_year), step=1, key="year_hotel"
                    )
                    
                    # 表示方法選択
                    view_mode = st.selectbox(
                        "表示方法",
                        ["概要表示", "規模別詳細", "ホテル種別詳細", "マトリックス表示"],
                        key="hotel_view_mode"
                    )

                if not sel_targets_hotel:
                    st.info("👆 市町村を選択してください。")
                else:
                    # ===== 概要表示 =====
                    if view_mode == "概要表示":
                        st.subheader("📈 概要 - Total推移")
                        
                        for element in sel_elems_hotel:
                            metric_en = elem_map[element]
                            
                            # Total データ
                            df_total = (
                                df_hotel_breakdown.query(
                                    f"metric == @metric_en & cat1 == 'total' & city in @sel_targets_hotel & "
                                    f"year >= {year_range_hotel[0]} & year <= {year_range_hotel[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .reindex(columns=[city for city in all_municipalities if city in sel_targets_hotel])
                                .sort_index()
                            )

                            # 全市町村データ（ランキング用）
                            df_all_total = (
                                df_hotel_breakdown.query(
                                    f"metric == @metric_en & cat1 == 'total' & "
                                    f"year >= {year_range_hotel[0]} & year <= {year_range_hotel[1]}"
                                )
                                .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                .sort_index()
                            )

                            fig = create_line_chart(
                                df_total, sel_targets_hotel,
                                f"ホテル・旅館 {element}推移（Total） ({year_range_hotel[0]}-{year_range_hotel[1]})",
                                element, show_legend=False, df_all=df_all_total, show_ranking=True
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            st.dataframe(df_total.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== 規模別詳細表示 =====
                    elif view_mode == "規模別詳細":
                        st.subheader("🏢 規模別詳細分析")
                        
                        scale_mapping = {
                            "large": "大規模（300人以上）",
                            "medium": "中規模（100-299人）", 
                            "small": "小規模（99人以下）"
                        }
                        
                        for element in sel_elems_hotel:
                            metric_en = elem_map[element]
                            st.write(f"**📊 {element}の規模別推移**")
                            
                            for scale_en, scale_jp in scale_mapping.items():
                                # 規模別データ集計（全ホテル種別を合計）
                                df_scale = (
                                    df_hotel_breakdown.query(
                                        f"metric == @metric_en & cat1.str.endswith('_{scale_en}') & "
                                        f"city in @sel_targets_hotel & "
                                        f"year >= {year_range_hotel[0]} & year <= {year_range_hotel[1]}"
                                    )
                                    .groupby(['year', 'city'])['value'].sum().reset_index()
                                    .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                    .reindex(columns=[city for city in all_municipalities if city in sel_targets_hotel])
                                    .sort_index()
                                )

                                if not df_scale.empty and df_scale.sum().sum() > 0:
                                    fig = create_line_chart(
                                        df_scale, sel_targets_hotel,
                                        f"{element} - {scale_jp}",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    with st.expander(f"📋 {scale_jp} データテーブル"):
                                        st.dataframe(df_scale.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== ホテル種別詳細表示 =====
                    elif view_mode == "ホテル種別詳細":
                        st.subheader("🏨 ホテル種別詳細分析")
                        
                        hotel_type_mapping = {
                            "resort_hotel": "リゾートホテル",
                            "business_hotel": "ビジネスホテル",
                            "city_hotel": "シティホテル", 
                            "ryokan": "旅館"
                        }
                        
                        for element in sel_elems_hotel:
                            metric_en = elem_map[element]
                            st.write(f"**📊 {element}のホテル種別推移**")
                            
                            for hotel_type_en, hotel_type_jp in hotel_type_mapping.items():
                                # ホテル種別データ集計（全規模を合計）
                                df_type = (
                                    df_hotel_breakdown.query(
                                        f"metric == @metric_en & cat1.str.startswith('{hotel_type_en}_') & "
                                        f"city in @sel_targets_hotel & "
                                        f"year >= {year_range_hotel[0]} & year <= {year_range_hotel[1]}"
                                    )
                                    .groupby(['year', 'city'])['value'].sum().reset_index()
                                    .pivot_table(index="year", columns="city", values="value", aggfunc="sum")
                                    .reindex(columns=[city for city in all_municipalities if city in sel_targets_hotel])
                                    .sort_index()
                                )

                                if not df_type.empty and df_type.sum().sum() > 0:
                                    fig = create_line_chart(
                                        df_type, sel_targets_hotel,
                                        f"{element} - {hotel_type_jp}",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    with st.expander(f"📋 {hotel_type_jp} データテーブル"):
                                        st.dataframe(df_type.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== マトリックス表示 =====
                    elif view_mode == "マトリックス表示":
                        st.subheader("📊 マトリックス表示（ホテル種別×規模）")
                        
                        # 指標と年度を選択
                        col1, col2 = st.columns(2)
                        with col1:
                            selected_metric = st.selectbox("指標選択", sel_elems_hotel, key="matrix_metric")
                        with col2:
                            available_years = sorted(df_hotel_breakdown['year'].unique(), reverse=True)
                            selected_year = st.selectbox("年度選択", available_years, key="matrix_year")
                        
                        metric_en = elem_map[selected_metric]
                        
                        for city in sel_targets_hotel:
                            st.write(f"**🏙️ {city} - {selected_year}年 {selected_metric}**")
                            
                            # マトリックスデータ作成
                            city_data = df_hotel_breakdown.query(
                                f"city == @city & year == @selected_year & metric == @metric_en & cat1 != 'total'"
                            )
                            
                            if not city_data.empty:
                                # カテゴリの分析と分割
                                matrix_data = []
                                
                                for _, row in city_data.iterrows():
                                    cat1 = row['cat1']
                                    value = row['value']
                                    
                                    # アンダースコアで分割
                                    parts = cat1.split('_')
                                    
                                    if len(parts) >= 2:
                                        # 正常なケース: hotel_type_scale の形式
                                        if len(parts) == 2:
                                            hotel_type, scale = parts
                                        elif len(parts) == 3:
                                            # business_hotel_large などの場合
                                            hotel_type = f"{parts[0]}_{parts[1]}"
                                            scale = parts[2]
                                        else:
                                            # 予期しない形式の場合はスキップ
                                            continue
                                        
                                        matrix_data.append({
                                            'hotel_type': hotel_type,
                                            'scale': scale,
                                            'value': value
                                        })
                                
                                if matrix_data:
                                    # DataFrameに変換
                                    matrix_df = pd.DataFrame(matrix_data)
                                    
                                    # マトリックス作成
                                    try:
                                        matrix = matrix_df.pivot_table(
                                            index='hotel_type', columns='scale', values='value', 
                                            aggfunc='sum', fill_value=0
                                        )
                                        
                                        # 日本語ラベルに変換
                                        hotel_type_jp_map = {
                                            'resort_hotel': 'リゾートホテル',
                                            'business_hotel': 'ビジネスホテル', 
                                            'city_hotel': 'シティホテル',
                                            'ryokan': '旅館'
                                        }
                                        
                                        scale_jp_map = {
                                            'large': '大規模',
                                            'medium': '中規模',
                                            'small': '小規模'
                                        }
                                        
                                        # インデックスと列名を日本語に変換
                                        new_index = []
                                        for idx in matrix.index:
                                            new_index.append(hotel_type_jp_map.get(idx, idx))
                                        matrix.index = new_index
                                        
                                        new_columns = []
                                        for col in matrix.columns:
                                            new_columns.append(scale_jp_map.get(col, col))
                                        matrix.columns = new_columns
                                        
                                        # 規模の順序を調整
                                        desired_column_order = ['大規模', '中規模', '小規模']
                                        available_columns = [col for col in desired_column_order if col in matrix.columns]
                                        matrix = matrix[available_columns]
                                        
                                        # 合計行・列を追加
                                        matrix['合計'] = matrix.sum(axis=1)
                                        matrix.loc['合計'] = matrix.sum(axis=0)
                                        
                                        # ゼロ行を除外（合計行以外）
                                        matrix_display = matrix.copy()
                                        non_zero_rows = (matrix_display.iloc[:-1].sum(axis=1) > 0)
                                        if len(non_zero_rows) > 0:
                                            matrix_display = matrix_display.loc[non_zero_rows.index[non_zero_rows].tolist() + ['合計']]
                                        
                                        # スタイリング付きで表示
                                        if len(matrix_display) > 1:  # 合計行以外にデータがある場合
                                            try:
                                                # matplotlibが利用可能な場合はグラデーション表示
                                                styled_matrix = matrix_display.style.format(thousands=",").background_gradient(
                                                    cmap='Blues', subset=matrix_display.columns[:-1]
                                                )
                                                st.dataframe(styled_matrix, use_container_width=True)
                                            except ImportError:
                                                # matplotlibが無い場合は通常表示
                                                st.dataframe(matrix_display.style.format(thousands=","), use_container_width=True)
                                            except Exception:
                                                # その他のエラーの場合も通常表示
                                                st.dataframe(matrix_display.style.format(thousands=","), use_container_width=True)
                                        else:
                                            st.info("データはありますが、すべて0のため表示をスキップしました。")
                                            
                                    except Exception as e:
                                        st.error(f"マトリックス作成エラー: {e}")
                                        
                                else:
                                    st.warning("有効なマトリックスデータがありません")

                # ===== データ概要情報 =====
                with st.expander("📈 データ概要情報"):
                    years_list = sorted([int(year) for year in df_hotel_breakdown['year'].unique()])
                    st.write("**利用可能な年度:**", years_list)
                    st.write("**市町村数:**", len(df_hotel_breakdown['city'].unique()))
                    st.write("**カテゴリ数:**", len(df_hotel_breakdown['cat1'].unique()))
                    
                    if sel_targets_hotel:
                        latest_year = df_hotel_breakdown['year'].max()
                        st.write(f"**{latest_year}年の選択市町村データサマリー:**")
                        
                        summary_data = df_hotel_breakdown.query(
                            f"year == @latest_year & city in @sel_targets_hotel & cat1 == 'total'"
                        ).pivot_table(index='city', columns='metric', values='value', aggfunc='sum')
                        
                        if not summary_data.empty:
                            # 列名を日本語に変換
                            column_mapping = {'capacity': '収容人数', 'facilities': '軒数', 'rooms': '客室数'}
                            summary_data.columns = [column_mapping.get(col, col) for col in summary_data.columns]
                            
                            # 列の順序を調整
                            desired_order = ['軒数', '客室数', '収容人数']
                            available_cols = [col for col in desired_order if col in summary_data.columns]
                            summary_data = summary_data[available_cols]
                            
                            st.dataframe(summary_data.style.format(thousands=","), use_container_width=True)

    # =================================================
    # TAB 4: エリア別分析（全シート対応）
    # =================================================
    with tab4:
        st.header("🗺️ エリア別の状況")
        
        # ===== 共通設定エリア =====
        st.subheader("🎛️ 分析設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # エリア選択
            area_names = list(REGION_MAP.keys())
            sel_areas = st.multiselect(
                "エリアを選択",
                area_names,
                default=area_names,
                key="areas"
            )
            
            # 指標選択
            sel_elems_area = st.multiselect(
                "指標", 
                list(elem_map.keys()), 
                default=["軒数"],
                key="elems_area"
            )
        
        with col2:
            # 年度選択
            year_range_area = st.slider(
                "期間", min_y, max_y, (2007, 2024), step=1, key="year_area"
            )
            
            # 分析タイプ選択
            analysis_type = st.selectbox(
                "分析タイプ",
                ["全宿泊施設", "ホテル・旅館特化"],
                key="area_analysis_type"
            )

        if not sel_areas:
            st.info("👆 エリアを選択してください。")
        else:
            # city → area の逆引き辞書
            city_to_area = {c: r for r, lst in REGION_MAP.items() for c in lst}
            
            # 分析タイプに応じてデータソースと表示方法を決定
            if analysis_type == "全宿泊施設":
                # accommodation_type データを使用
                df_analysis = df_long.query("table == 'accommodation_type'")
                
                if df_analysis.empty:
                    st.warning("⚠️ 宿泊形態別データが見つかりません。")
                else:
                    # 表示方法選択
                    view_mode_area = st.selectbox(
                        "表示方法",
                        ["概要表示", "宿泊形態別詳細"],
                        key="area_view_mode_all"
                    )
                    
                    st.info("📊 **全宿泊施設**: ホテル・旅館、民宿、ペンション、ゲストハウス等すべての宿泊施設を含む分析")
                    
                    # ===== 概要表示 =====
                    if view_mode_area == "概要表示":
                        st.subheader("📈 概要 - 全宿泊施設推移")
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            
                            # Total データ
                            df_area_total = (
                                df_analysis.query(
                                    f"metric == @metric_en & cat1 == 'total' & "
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
                                f"エリア別{element}推移（全宿泊施設） ({year_range_area[0]}-{year_range_area[1]})",
                                element, show_legend=False, df_all=None, show_ranking=False
                            )
                            st.plotly_chart(fig_area_total, use_container_width=True)
                            st.dataframe(df_area_total.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== 宿泊形態別詳細 =====
                    elif view_mode_area == "宿泊形態別詳細":
                        st.subheader("🏨 宿泊形態別詳細分析")
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            st.write(f"**📊 {element}の宿泊形態別推移**")
                            
                            for cat_en, cat_jp in accommodation_type_mapping.items():
                                # 宿泊形態別データ集計
                                df_area_category = (
                                    df_analysis.query(
                                        f"metric == @metric_en & cat1 == @cat_en & "
                                        "city in @city_to_area.keys() & "
                                        f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                    )
                                    .assign(area=lambda d: d["city"].map(city_to_area))
                                    .groupby(["area", "year"])['value'].sum()
                                    .unstack("area")
                                    .reindex(columns=sel_areas)
                                    .sort_index()
                                )

                                if not df_area_category.empty and df_area_category.sum().sum() > 0:
                                    fig = create_line_chart(
                                        df_area_category, sel_areas,
                                        f"{element} - {cat_jp}",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    with st.expander(f"📋 {cat_jp} データテーブル"):
                                        st.dataframe(df_area_category.transpose().style.format(thousands=","), use_container_width=True)
            
            else:  # ホテル・旅館特化
                # scale_class データまたは hotel_breakdown データを使用
                df_scale = df_long.query("table == 'scale_class'")
                df_hotel = df_long.query("table == 'hotel_breakdown'")
                
                if df_scale.empty and df_hotel.empty:
                    st.warning("⚠️ ホテル・旅館特化データが見つかりません。")
                else:
                    # 表示方法選択
                    available_modes = ["概要表示"]
                    if not df_scale.empty:
                        available_modes.append("規模別詳細")
                    if not df_hotel.empty:
                        available_modes.extend(["ホテル種別詳細", "マトリックス表示"])
                    
                    view_mode_hotel = st.selectbox(
                        "表示方法",
                        available_modes,
                        key="area_view_mode_hotel"
                    )
                    
                    st.info("🏨 **ホテル・旅館特化**: 全宿泊施設のうち「ホテル・旅館」のみに限定した詳細分析")
                    
                    # ===== 概要表示 =====
                    if view_mode_hotel == "概要表示":
                        st.subheader("📈 概要 - ホテル・旅館推移")
                        
                        # accommodation_typeの中のhotel_ryokanを使用
                        df_analysis = df_long.query("table == 'accommodation_type'")
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            
                            # ホテル・旅館のみのデータ
                            df_area_hotel = (
                                df_analysis.query(
                                    f"metric == @metric_en & cat1 == 'hotel_ryokan' & "
                                    "city in @city_to_area.keys() & "
                                    f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                )
                                .assign(area=lambda d: d["city"].map(city_to_area))
                                .groupby(["area", "year"])['value'].sum()
                                .unstack("area")
                                .reindex(columns=sel_areas)
                                .sort_index()
                            )

                            fig_area_hotel = create_line_chart(
                                df_area_hotel, sel_areas, 
                                f"エリア別{element}推移（ホテル・旅館のみ） ({year_range_area[0]}-{year_range_area[1]})",
                                element, show_legend=False, df_all=None, show_ranking=False
                            )
                            st.plotly_chart(fig_area_hotel, use_container_width=True)
                            st.dataframe(df_area_hotel.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== 規模別詳細 =====
                    elif view_mode_hotel == "規模別詳細":
                        st.subheader("🏢 ホテル・旅館 規模別詳細分析")
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            st.write(f"**📊 {element}の規模別推移（ホテル・旅館のみ）**")
                            
                            for scale_en, scale_jp in scale_class_mapping.items():
                                # 規模別データ集計
                                df_area_scale = (
                                    df_scale.query(
                                        f"metric == @metric_en & cat1 == @scale_en & "
                                        "city in @city_to_area.keys() & "
                                        f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                    )
                                    .assign(area=lambda d: d["city"].map(city_to_area))
                                    .groupby(["area", "year"])['value'].sum()
                                    .unstack("area")
                                    .reindex(columns=sel_areas)
                                    .sort_index()
                                )

                                if not df_area_scale.empty and df_area_scale.sum().sum() > 0:
                                    fig = create_line_chart(
                                        df_area_scale, sel_areas,
                                        f"{element} - {scale_jp}（ホテル・旅館）",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    with st.expander(f"📋 {scale_jp} データテーブル"):
                                        st.dataframe(df_area_scale.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== ホテル種別詳細 =====
                    elif view_mode_hotel == "ホテル種別詳細":
                        st.subheader("🏨 ホテル種別詳細分析")
                        
                        hotel_type_mapping = {
                            "resort_hotel": "リゾートホテル",
                            "business_hotel": "ビジネスホテル",
                            "city_hotel": "シティホテル", 
                            "ryokan": "旅館"
                        }
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            st.write(f"**📊 {element}のホテル種別推移**")
                            
                            for hotel_type_en, hotel_type_jp in hotel_type_mapping.items():
                                # ホテル種別データ集計（全規模を合計）
                                df_area_type = (
                                    df_hotel.query(
                                        f"metric == @metric_en & cat1.str.startswith('{hotel_type_en}_') & "
                                        "city in @city_to_area.keys() & "
                                        f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                    )
                                    .assign(area=lambda d: d["city"].map(city_to_area))
                                    .groupby(["area", "year"])['value'].sum()
                                    .unstack("area")
                                    .reindex(columns=sel_areas)
                                    .sort_index()
                                )

                                if not df_area_type.empty and df_area_type.sum().sum() > 0:
                                    fig = create_line_chart(
                                        df_area_type, sel_areas,
                                        f"{element} - {hotel_type_jp}",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    with st.expander(f"📋 {hotel_type_jp} データテーブル"):
                                        st.dataframe(df_area_type.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== マトリックス表示 =====
                    elif view_mode_hotel == "マトリックス表示":
                        st.subheader("📊 マトリックス表示（ホテル種別×規模）")
                        
                        # 指標と年度を選択
                        col1, col2 = st.columns(2)
                        with col1:
                            selected_metric = st.selectbox("指標選択", sel_elems_area, key="area_matrix_metric")
                        with col2:
                            available_years = sorted(df_hotel['year'].unique(), reverse=True)
                            selected_year = st.selectbox("年度選択", available_years, key="area_matrix_year")
                        
                        metric_en = elem_map[selected_metric]
                        
                        for area in sel_areas:
                            st.write(f"**🗺️ {area} - {selected_year}年 {selected_metric}**")
                            
                            # エリア内の市町村を取得
                            area_cities = REGION_MAP.get(area, [])
                            
                            # エリア内のデータを集計
                            area_data = df_hotel.query(
                                f"city in @area_cities & year == @selected_year & metric == @metric_en & cat1 != 'total'"
                            )
                            
                            if not area_data.empty:
                                # カテゴリの分析と分割
                                matrix_data = []
                                
                                for _, row in area_data.iterrows():
                                    cat1 = row['cat1']
                                    value = row['value']
                                    
                                    # アンダースコアで分割
                                    parts = cat1.split('_')
                                    
                                    if len(parts) >= 2:
                                        if len(parts) == 2:
                                            hotel_type, scale = parts
                                        elif len(parts) == 3:
                                            hotel_type = f"{parts[0]}_{parts[1]}"
                                            scale = parts[2]
                                        else:
                                            continue
                                        
                                        # 既存の同じ組み合わせがあれば合計
                                        existing = next((item for item in matrix_data if item['hotel_type'] == hotel_type and item['scale'] == scale), None)
                                        if existing:
                                            existing['value'] += value
                                        else:
                                            matrix_data.append({
                                                'hotel_type': hotel_type,
                                                'scale': scale,
                                                'value': value
                                            })
                                
                                if matrix_data:
                                    # DataFrameに変換してマトリックス作成
                                    matrix_df = pd.DataFrame(matrix_data)
                                    
                                    try:
                                        matrix = matrix_df.pivot_table(
                                            index='hotel_type', columns='scale', values='value', 
                                            aggfunc='sum', fill_value=0
                                        )
                                        
                                        # 日本語ラベルに変換
                                        hotel_type_jp_map = {
                                            'resort_hotel': 'リゾートホテル',
                                            'business_hotel': 'ビジネスホテル', 
                                            'city_hotel': 'シティホテル',
                                            'ryokan': '旅館'
                                        }
                                        
                                        scale_jp_map = {
                                            'large': '大規模',
                                            'medium': '中規模',
                                            'small': '小規模'
                                        }
                                        
                                        # インデックスと列名を日本語に変換
                                        new_index = [hotel_type_jp_map.get(idx, idx) for idx in matrix.index]
                                        matrix.index = new_index
                                        
                                        new_columns = [scale_jp_map.get(col, col) for col in matrix.columns]
                                        matrix.columns = new_columns
                                        
                                        # 規模の順序を調整
                                        desired_column_order = ['大規模', '中規模', '小規模']
                                        available_columns = [col for col in desired_column_order if col in matrix.columns]
                                        matrix = matrix[available_columns]
                                        
                                        # 合計行・列を追加
                                        matrix['合計'] = matrix.sum(axis=1)
                                        matrix.loc['合計'] = matrix.sum(axis=0)
                                        
                                        # ゼロ行を除外（合計行以外）
                                        matrix_display = matrix.copy()
                                        non_zero_rows = (matrix_display.iloc[:-1].sum(axis=1) > 0)
                                        if len(non_zero_rows) > 0:
                                            matrix_display = matrix_display.loc[non_zero_rows.index[non_zero_rows].tolist() + ['合計']]
                                        
                                        # 表示
                                        if len(matrix_display) > 1:
                                            try:
                                                styled_matrix = matrix_display.style.format(thousands=",").background_gradient(
                                                    cmap='Blues', subset=matrix_display.columns[:-1]
                                                )
                                                st.dataframe(styled_matrix, use_container_width=True)
                                            except:
                                                st.dataframe(matrix_display.style.format(thousands=","), use_container_width=True)
                                        else:
                                            st.info("データはありますが、すべて0のため表示をスキップしました。")
                                            
                                    except Exception as e:
                                        st.error(f"マトリックス作成エラー: {e}")
                                        
                                else:
                                    st.warning("有効なマトリックスデータがありません")
                            else:
                                st.write("データがありません")
        
        # ===== データ概要情報 =====
        with st.expander("📈 データ概要情報"):
            st.write("**🏨 データソースの違い:**")
            st.write("• **全宿泊施設**: ホテル・旅館、民宿、ペンション、ゲストハウス等すべてを含む")
            st.write("• **ホテル・旅館特化**: 全宿泊施設のうち「ホテル・旅館」のみに限定")
            st.write("• **規模別分析**: ホテル・旅館を収容人数で大中小に分類")
            st.write("• **ホテル種別分析**: ホテル・旅館をリゾート、ビジネス、シティ、旅館に分類")
            
            if analysis_type == "全宿泊施設":
                df_info = df_long.query("table == 'accommodation_type'")
            else:
                df_info = df_long.query("table == 'scale_class' or table == 'hotel_breakdown'")
            
            if not df_info.empty:
                years_list = sorted([int(year) for year in df_info['year'].unique()])
                st.write(f"**利用可能な年度:** {years_list}")
                st.write(f"**エリア数:** {len(REGION_MAP)}")
                
                if sel_areas:
                    latest_year = df_info['year'].max()
                    st.write(f"**{latest_year}年の選択エリアデータサマリー:**")
                    
                    # エリア別サマリー作成
                    city_to_area = {c: r for r, lst in REGION_MAP.items() for c in lst}
                    
                    if analysis_type == "全宿泊施設":
                        summary_data = (
                            df_info.query(f"year == @latest_year & cat1 == 'total' & city in @city_to_area.keys()")
                            .assign(area=lambda d: d["city"].map(city_to_area))
                            .query("area in @sel_areas")
                            .groupby(['area', 'metric'])['value'].sum()
                            .unstack('metric')
                        )
                    else:
                        # ホテル・旅館のみの場合
                        accommodation_df = df_long.query("table == 'accommodation_type'")
                        summary_data = (
                            accommodation_df.query(f"year == @latest_year & cat1 == 'hotel_ryokan' & city in @city_to_area.keys()")
                            .assign(area=lambda d: d["city"].map(city_to_area))
                            .query("area in @sel_areas")
                            .groupby(['area', 'metric'])['value'].sum()
                            .unstack('metric')
                        )
                    
                    if not summary_data.empty:
                        # 列名を日本語に変換
                        column_mapping = {'capacity': '収容人数', 'facilities': '軒数', 'rooms': '客室数'}
                        summary_data.columns = [column_mapping.get(col, col) for col in summary_data.columns]
                        
                        # 列の順序を調整
                        desired_order = ['軒数', '客室数', '収容人数']
                        available_cols = [col for col in desired_order if col in summary_data.columns]
                        summary_data = summary_data[available_cols]
                        
                        st.dataframe(summary_data.style.format(thousands=","), use_container_width=True)



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