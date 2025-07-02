def handle_ranking(df, metric_en, metric_jp, location_type, locations, ranking_count, ranking_year):
    """ランキング表示の処理"""
    # エリア名と県名を除外するフィルタ
    exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
    
    # データの対象範囲を決定
    if location_type == "市町村" and locations and locations != ["全体"]:
        data = df.query(f"city in @locations & metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
        scope_text = f"選択市町村（{'・'.join(locations[:3])}{'など' if len(locations) > 3 else ''}）"
    elif location_type == "エリア" and locations and locations != ["全体"]:
        area_cities = []
        for area in locations:
            area_cities.extend(REGION_MAP.get(area, []))
        data = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
        scope_text = f"{'・'.join(locations)}エリア"
    else:  # 全体またはフィルタなし
        data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
        scope_text = "全市町村"
    
    ranking = data.sort_values('value', ascending=False).head(ranking_count)
    
    result = f"## {ranking_year}年 {scope_text} {metric_jp}ランキング トップ{ranking_count}\n\n"
    
    for i, (_, row) in enumerate(ranking.iterrows(), 1):
        result += f"**{i}位: {row['city']}** - {row['value']:,}{get_unit(metric_jp)}\n"
    
    return result# -*- coding: utf-8 -*-
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
    "今帰仁村": 47322, "本部町": 47327, "恩納村": 47323, "宜野座村": 47324, "金武町": 47325,
    "読谷村": 47326, "嘉手納町": 47328, "北谷町": 47329,
    "北中城村": 47330, "中城村": 47331, "西原町": 47332,
    # 島尻郡
    "与那原町": 47351, "南風原町": 47352, "渡嘉敷村": 47353,
    "座間味村": 47354, "粟国村": 47355, "渡名喜村": 47356,
    "南大東村": 47357, "北大東村": 47358, "伊江村": 47359,
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

    try:
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
    except Exception as e:
        st.error(f"Transition.xlsx読み込みエラー: {e}")
        return pd.DataFrame()

# ---------------- ヘルプコンテンツ表示関数 ----------------
def display_help_content():
    """ヘルプコンテンツの表示"""
    
    help_sections = {
        "🎯 アプリ概要": {
            "title": "このアプリでできること",
            "content": """
            ### 🎯 このアプリでできること
            **沖縄県全41市町村**の宿泊施設データを多角的に分析できるダッシュボードです。
            
            #### 📊 分析対象データ
            - **期間**: 昭和47年〜令和6年（約50年間の長期トレンド）
            - **対象**: 全41市町村の宿泊施設（ホテル・旅館・民宿・ペンション等）
            - **指標**: 施設数（軒数）・客室数・収容人数
            
            #### 🔍 5つの分析アプローチ
            1. **🤖 ランキング分析**: 自然言語形式でデータを質問・分析
            2. **🏘️ 市町村別分析**: 特定の市町村を選んで詳細分析
            3. **🏨 ホテル・旅館規模別**: 施設の規模（大・中・小）による分析
            4. **🏛️ ホテル・旅館種別**: リゾート・ビジネス・シティホテル等の分析
            5. **🗺️ エリア別分析**: 南部・中部・北部・宮古・八重山・離島の分析
            """
        }
    }
    
    # セクション選択
    selected_section = st.selectbox(
        "📖 表示したいヘルプ項目を選択してください",
        list(help_sections.keys()),
        key="help_section_selector"
    )
    
    # 選択されたセクションを表示
    if selected_section in help_sections:
        section = help_sections[selected_section]
        st.markdown(f"## {section['title']}")
        st.markdown(section['content'])

# ---------------- 構造化質問処理関数 ----------------
def generate_question_preview(question_type, metric, location_type, locations, params):
    """質問のプレビューテキストを生成"""
    # ランキング系での場所フィルタ処理
    if question_type in ["ランキング表示", "増減数ランキング", "増減率ランキング"]:
        if params.get('enable_location_filter', False) and locations and locations != ["全体"]:
            if location_type == "市町村":
                if len(locations) == len(CITY_CODE.keys()):  # 全市町村選択
                    scope_text = "（全市町村）"
                elif len(locations) <= 3:
                    location_text = "・".join(locations)
                    scope_text = f"（{location_text}内）"
                else:
                    scope_text = f"（{locations[0]}など{len(locations)}市町村内）"
            elif location_type == "エリア":
                if len(locations) == len(REGION_MAP.keys()):  # 全エリア選択
                    scope_text = "（全エリア）"
                elif len(locations) <= 3:
                    location_text = "・".join(locations) + "エリア"
                    scope_text = f"（{location_text}内）"
                else:
                    scope_text = f"（{locations[0]}など{len(locations)}エリア内）"
            else:
                scope_text = ""
        else:
            scope_text = "（全市町村）"
    else:
        # 通常の場所選択
        if not locations and location_type != "全体":
            return "場所を選択してください"
        
        if location_type == "市町村":
            if len(locations) == len(CITY_CODE.keys()):  # 全市町村選択
                location_text = "沖縄県全市町村"
            elif len(locations) <= 3:
                location_text = "・".join(locations)
            else:
                location_text = f"{locations[0]}など{len(locations)}市町村"
        elif location_type == "エリア":
            if len(locations) == len(REGION_MAP.keys()):  # 全エリア選択
                location_text = "沖縄県全エリア"
            elif len(locations) <= 3:
                location_text = "・".join(locations) + "エリア"
            else:
                location_text = f"{locations[0]}など{len(locations)}エリア"
        else:
            location_text = "沖縄県全体"
    
    if question_type == "基本情報取得":
        year = params.get('target_year', '最新年')
        return f"{location_text}の{year}年の{metric}は？"
    
    elif question_type == "ランキング表示":
        count = params.get('ranking_count', 5)
        year = params.get('ranking_year', '最新年')
        return f"{year}年の{metric}トップ{count}{scope_text}は？"
    
    elif question_type == "増減数ランキング":
        count = params.get('ranking_count_change', 5)
        analysis = params.get('change_analysis_type', '対前年比較')
        if analysis == "対前年比較":
            year = params.get('target_year_ranking', '最新年')
            return f"{year}年の対前年{metric}増減数トップ{count}{scope_text}は？"
        else:
            period = params.get('period_years_ranking', '過去3年間')
            return f"{period}の{metric}増減数トップ{count}{scope_text}は？"
    
    elif question_type == "増減率ランキング":
        count = params.get('ranking_count_change', 5)
        analysis = params.get('change_analysis_type', '対前年比較')
        if analysis == "対前年比較":
            year = params.get('target_year_ranking', '最新年')
            return f"{year}年の対前年{metric}増減率トップ{count}{scope_text}は？"
        else:
            period = params.get('period_years_ranking', '過去3年間')
            return f"{period}の{metric}増減率トップ{count}{scope_text}は？"
    
    elif question_type == "増減・伸び率分析":
        analysis = params.get('analysis_type', '対前年比較')
        result = params.get('result_type', '増減数')
        if analysis == "対前年比較":
            return f"{location_text}の対前年{metric}{result}は？"
        else:
            period = params.get('period_years', '過去3年間')
            return f"{location_text}の{period}の{metric}{result}は？"
    
    elif question_type == "期間推移分析":
        period = params.get('period_type', '過去5年間')
        return f"{location_text}の{period}の{metric}推移は？"
    
    elif question_type == "比較分析":
        year = params.get('comparison_year', '最新年')
        return f"{year}年の{location_text}の{metric}比較は？"
    
    return "質問を設定してください"

def process_structured_question(**params):
    """構造化された質問パラメータを処理して回答を生成"""
    try:
        question_type = params['question_type']
        location_type = params['location_type']
        locations = params['locations']
        df = params['df']
        debug_mode = params.get('debug_mode', False)
        
        if debug_mode:
            import streamlit as st
            st.write("**🔍 process_structured_question デバッグ**")
            st.write(f"- question_type: {question_type}")
            st.write(f"- location_type: {location_type}")
            st.write(f"- locations: {locations}")
        
        # 基本情報取得の場合は複数指標に対応
        if question_type == "基本情報取得":
            metrics = params.get('metrics', [params.get('metric', '軒数')])  # 複数指標または単一指標
            if isinstance(metrics, str):
                metrics = [metrics]  # 文字列の場合はリストに変換
            
            target_year = params['target_year']
            
            if debug_mode:
                st.write(f"- 処理する指標数: {len(metrics)}")
                st.write(f"- 指標: {metrics}")
            
            # データフィルタリング
            df_analysis = get_analysis_dataframe(df, debug_mode)
            if df_analysis is None:
                return "申し訳ございませんが、分析に使用できるデータが見つかりません。"
            
            # 全指標のデータ存在確認
            valid_metrics = []
            for metric_jp in metrics:
                metric_en = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}[metric_jp]
                if validate_metric_data(df_analysis, metric_en, metric_jp, debug_mode):
                    valid_metrics.append(metric_jp)
            
            if not valid_metrics:
                return "申し訳ございませんが、指定された指標のデータが見つかりません。"
            
            # 市町村ごとにまとめた基本情報を取得
            result = handle_basic_info_multi_metrics(df_analysis, valid_metrics, location_type, locations, target_year)
            return result
        
        else:
            # 従来の単一指標処理
            metric_jp = params['metric']
            metric_en = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}[metric_jp]
            
            if debug_mode:
                st.write(f"- metric: {metric_jp} ({metric_en})")
            
            # データフィルタリング
            df_analysis = get_analysis_dataframe(df, debug_mode)
            if df_analysis is None:
                return "申し訳ございませんが、分析に使用できるデータが見つかりません。"
            
            # 指標データの存在確認
            if not validate_metric_data(df_analysis, metric_en, metric_jp, debug_mode):
                return f"申し訳ございませんが、指標「{metric_jp}」のデータが見つかりません。"
            
            # パラメータにdebug_modeを追加
            params['debug_mode'] = debug_mode
            
            if question_type == "ランキング表示":
                result = handle_ranking(df_analysis, metric_en, metric_jp, location_type, locations, params['ranking_count'], params['ranking_year'])
                
            elif question_type in ["増減数ランキング", "増減率ランキング"]:
                result = handle_change_ranking(df_analysis, metric_en, metric_jp, location_type, locations, params)
                
            elif question_type == "増減・伸び率分析":
                result = handle_change_analysis(df_analysis, metric_en, metric_jp, location_type, locations, params)
                
            elif question_type == "期間推移分析":
                result = handle_trend_analysis(df_analysis, metric_en, metric_jp, location_type, locations, params['start_year'], params['end_year'])
                
            elif question_type == "比較分析":
                result = handle_comparison(df_analysis, metric_en, metric_jp, location_type, locations, params['comparison_year'])
                
            else:
                result = f"未対応の質問タイプです: {question_type}"
        
        # 結果が空の場合の対処 - Figure オブジェクトもチェック
        if result is None:
            result = "結果を生成できませんでした。データを確認してください。"
        elif isinstance(result, str) and result.strip() == "":
            result = "結果を生成できませんでした。データを確認してください。"
        
        return result
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f"""**処理中にエラーが発生しました**

**エラー:** {str(e)}

**詳細:**
```
{error_detail}
```

**パラメータ:**
- 質問タイプ: {params.get('question_type', 'N/A')}
- 指標: {params.get('metric', 'N/A')}
- 場所: {params.get('location_type', 'N/A')}
"""

def get_analysis_dataframe(df, debug_mode=False):
    """分析用データフレームを取得（優先順位付き）"""
    # 1. accommodation_typeテーブルを最優先
    df_accom = df.query("table == 'accommodation_type'")
    if not df_accom.empty:
        df_analysis = df_accom
        table_used = "accommodation_type"
    else:
        # 2. scale_classテーブルを次優先
        df_scale = df.query("table == 'scale_class'")
        if not df_scale.empty:
            df_analysis = df_scale  
            table_used = "scale_class"
        else:
            # 3. hotel_breakdownテーブルを使用
            df_hotel = df.query("table == 'hotel_breakdown'")
            if not df_hotel.empty:
                df_analysis = df_hotel
                table_used = "hotel_breakdown"
            else:
                # 4. 全データから使用
                df_analysis = df
                table_used = "全テーブル"
    
    if debug_mode:
        import streamlit as st
        st.write(f"- 使用テーブル: {table_used}")
        st.write(f"- データ件数: {len(df_analysis):,}行")
    
    return df_analysis if not df_analysis.empty else None

def validate_metric_data(df_analysis, metric_en, metric_jp, debug_mode=False):
    """指標データの存在を確認"""
    # 指定された指標のデータが存在するかチェック
    metric_data = df_analysis.query(f"metric == '{metric_en}'")
    if metric_data.empty:
        if debug_mode:
            import streamlit as st
            available_metrics = sorted(df_analysis['metric'].unique())
            st.warning(f"指標「{metric_jp}」({metric_en})のデータがありません。利用可能: {available_metrics}")
        return False
    
    # totalカテゴリのデータが存在するかチェック
    total_data = metric_data.query("cat1 == 'total'")
    if total_data.empty:
        if debug_mode:
            import streamlit as st
            available_cats = sorted(metric_data['cat1'].unique())
            st.warning(f"指標「{metric_jp}」のtotalカテゴリデータがありません。利用可能: {available_cats}")
        return False
    
    if debug_mode:
        import streamlit as st
        st.write(f"- {metric_jp}データ件数: {len(metric_data):,}行")
        st.write(f"- {metric_jp}(total)データ件数: {len(total_data):,}行")
        st.write(f"- 年度範囲: {total_data['year'].min()}〜{total_data['year'].max()}年")
    
    return True

def generate_question_preview(question_type, metric, location_type, locations, params):
    """質問のプレビューテキストを生成（複数指標対応）"""
    # 基本情報取得の場合は複数指標に対応
    if question_type == "基本情報取得":
        # metricsパラメータがある場合は複数指標、そうでなければ単一指標
        metrics = params.get('selected_metrics', [metric] if metric else [])
        if not metrics:
            return "指標を選択してください"
        
        # 場所テキストの生成
        if not locations or location_type == "全体":
            location_text = "沖縄県全体"
        elif location_type == "市町村":
            if len(locations) <= 3:
                location_text = "・".join(locations)
            else:
                location_text = f"{locations[0]}など{len(locations)}市町村"
        elif location_type == "エリア":
            if len(locations) <= 3:
                location_text = "・".join(locations) + "エリア"
            else:
                location_text = f"{locations[0]}など{len(locations)}エリア"
        else:
            location_text = "選択された場所"
        
        # 指標テキストの生成
        if len(metrics) == 1:
            metric_text = metrics[0]
        elif len(metrics) == 2:
            metric_text = "・".join(metrics)
        else:
            metric_text = f"{metrics[0]}など{len(metrics)}項目"
        
        year = params.get('target_year', '最新年')
        return f"{location_text}の{year}年の{metric_text}は？"
    
    # その他の質問タイプは従来通り
    # ランキング系での場所フィルタ処理
    if question_type in ["ランキング表示", "増減数ランキング", "増減率ランキング"]:
        if params.get('enable_location_filter', False) and locations and locations != ["全体"]:
            if location_type == "市町村":
                if len(locations) == len(CITY_CODE.keys()):  # 全市町村選択
                    scope_text = "（全市町村）"
                elif len(locations) <= 3:
                    location_text = "・".join(locations)
                    scope_text = f"（{location_text}内）"
                else:
                    scope_text = f"（{locations[0]}など{len(locations)}市町村内）"
            elif location_type == "エリア":
                if len(locations) == len(REGION_MAP.keys()):  # 全エリア選択
                    scope_text = "（全エリア）"
                elif len(locations) <= 3:
                    location_text = "・".join(locations) + "エリア"
                    scope_text = f"（{location_text}内）"
                else:
                    scope_text = f"（{locations[0]}など{len(locations)}エリア内）"
            else:
                scope_text = ""
        else:
            scope_text = "（全市町村）"
    else:
        # 通常の場所選択
        if not locations and location_type != "全体":
            return "場所を選択してください"
        
        if location_type == "市町村":
            if len(locations) == len(CITY_CODE.keys()):  # 全市町村選択
                location_text = "沖縄県全市町村"
            elif len(locations) <= 3:
                location_text = "・".join(locations)
            else:
                location_text = f"{locations[0]}など{len(locations)}市町村"
        elif location_type == "エリア":
            if len(locations) == len(REGION_MAP.keys()):  # 全エリア選択
                location_text = "沖縄県全エリア"
            elif len(locations) <= 3:
                location_text = "・".join(locations) + "エリア"
            else:
                location_text = f"{locations[0]}など{len(locations)}エリア"
        else:
            location_text = "沖縄県全体"
    
    if question_type == "ランキング表示":
        count = params.get('ranking_count', 5)
        year = params.get('ranking_year', '最新年')
        return f"{year}年の{metric}トップ{count}{scope_text}は？"
    
    elif question_type == "増減数ランキング":
        count = params.get('ranking_count_change', 5)
        analysis = params.get('change_analysis_type', '対前年比較')
        if analysis == "対前年比較":
            year = params.get('target_year_ranking', '最新年')
            return f"{year}年の対前年{metric}増減数トップ{count}{scope_text}は？"
        else:
            period = params.get('period_years_ranking', '過去3年間')
            return f"{period}の{metric}増減数トップ{count}{scope_text}は？"
    
    elif question_type == "増減率ランキング":
        count = params.get('ranking_count_change', 5)
        analysis = params.get('change_analysis_type', '対前年比較')
        if analysis == "対前年比較":
            year = params.get('target_year_ranking', '最新年')
            return f"{year}年の対前年{metric}増減率トップ{count}{scope_text}は？"
        else:
            period = params.get('period_years_ranking', '過去3年間')
            return f"{period}の{metric}増減率トップ{count}{scope_text}は？"
    
    elif question_type == "増減・伸び率分析":
        analysis = params.get('analysis_type', '対前年比較')
        result = params.get('result_type', '増減数')
        if analysis == "対前年比較":
            return f"{location_text}の対前年{metric}{result}は？"
        else:
            period = params.get('period_years', '過去3年間')
            return f"{location_text}の{period}の{metric}{result}は？"
    
    elif question_type == "期間推移分析":
        period = params.get('period_type', '過去5年間')
        return f"{location_text}の{period}の{metric}推移は？"
    
    elif question_type == "比較分析":
        year = params.get('comparison_year', '最新年')
        return f"{year}年の{location_text}の{metric}比較は？"
    
    return "質問を設定してください"

def handle_change_ranking(df, metric_en, metric_jp, location_type, locations, params):
    """増減数・増減率ランキングの処理"""
    try:
        analysis_type = params['analysis_type']
        result_type = params['result_type']
        ranking_count = params['ranking_count']
        debug_mode = params.get('debug_mode', False)
        
        # Streamlit デバッグ情報
        if debug_mode:
            import streamlit as st
            st.write(f"**🔍 handle_change_ranking デバッグ**")
            st.write(f"- analysis_type: {analysis_type}")
            st.write(f"- result_type: {result_type}")
            st.write(f"- location_type: {location_type}")
            st.write(f"- locations: {locations}")
        
        # データの対象範囲を決定
        if location_type == "市町村" and locations and locations != ["全体"]:
            target_cities = locations
            scope_text = f"選択市町村（{'・'.join(locations[:3])}{'など' if len(locations) > 3 else ''}）"
        elif location_type == "エリア" and locations and locations != ["全体"]:
            # エリア別ランキングの場合は、エリア単位で処理
            if len(locations) == len(REGION_MAP.keys()):  # 全エリア選択
                scope_text = "全エリア"
                return handle_area_change_ranking(df, metric_en, metric_jp, list(REGION_MAP.keys()), scope_text,
                                               analysis_type, result_type, ranking_count, params, debug_mode)
            else:
                scope_text = f"{'・'.join(locations)}エリア"
                return handle_area_change_ranking(df, metric_en, metric_jp, locations, scope_text,
                                               analysis_type, result_type, ranking_count, params, debug_mode)
        else:  # 全体またはフィルタなし
            target_cities = list(CITY_CODE.keys())  # 全市町村
            scope_text = "全市町村"
        
        if debug_mode:
            st.write(f"- target_cities数: {len(target_cities)}")
            st.write(f"- scope_text: {scope_text}")
            st.write(f"- target_cities例: {target_cities[:5]}")
        
        if analysis_type == "対前年比較":
            target_year = params['target_year']
            result = handle_change_ranking_year_over_year(df, metric_en, metric_jp, target_cities, scope_text, 
                                                      target_year, result_type, ranking_count)
        else:  # 期間比較
            start_year = params['start_year']
            end_year = params['end_year']
            if debug_mode:
                st.write(f"- 期間比較実行: {start_year}-{end_year}")
            result = handle_change_ranking_period(df, metric_en, metric_jp, target_cities, scope_text,
                                              start_year, end_year, result_type, ranking_count, debug_mode)
        
        if debug_mode:
            st.write(f"- 処理結果の長さ: {len(result) if result else 0}文字")
            if result:
                st.write(f"- 結果の最初の100文字: {result[:100]}...")
        
        if not result or result.strip() == "":
            error_msg = f"""増減ランキングの処理結果が空でした。

**詳細情報:**
- 分析タイプ: {analysis_type}
- 対象: {scope_text}
- 開始年: {params.get('start_year')}
- 終了年: {params.get('end_year')}
- 対象市町村数: {len(target_cities)}
"""
            if debug_mode:
                st.error("処理結果が空です！")
            return error_msg
        
        return result
        
    except Exception as e:
        error_msg = f"増減ランキング処理中にエラーが発生しました: {str(e)}\n\nパラメータ: {params}"
        if params.get('debug_mode', False):
            import streamlit as st
            st.error(f"handle_change_ranking エラー: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
        return error_msg

def handle_area_change_ranking(df, metric_en, metric_jp, areas, scope_text, analysis_type, result_type, ranking_count, params, debug_mode=False):
    """エリア別の増減ランキング処理"""
    try:
        if debug_mode:
            import streamlit as st
            st.write(f"**🔍 handle_area_change_ranking デバッグ**")
            st.write(f"- エリア数: {len(areas)}")
            st.write(f"- エリア: {areas}")
        
        # city → area の逆引き辞書
        city_to_area = {c: r for r, lst in REGION_MAP.items() for c in lst}
        
        if analysis_type == "対前年比較":
            target_year = params['target_year']
            previous_year = target_year - 1
            
            # 各エリアの合計データを計算
            area_current = {}
            area_previous = {}
            
            for area in areas:
                area_cities = REGION_MAP.get(area, [])
                
                # 現在年のエリア合計
                current_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @target_year & city in @area_cities")
                area_current[area] = current_data['value'].sum()
                
                # 前年のエリア合計
                previous_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @previous_year & city in @area_cities")
                area_previous[area] = previous_data['value'].sum()
            
            # 増減数と増減率を計算
            area_increases = {}
            area_rates = {}
            
            for area in areas:
                if area in area_current and area in area_previous:
                    increase = area_current[area] - area_previous[area]
                    area_increases[area] = increase
                    
                    if area_previous[area] != 0:
                        rate = (increase / area_previous[area]) * 100
                        area_rates[area] = rate
                    else:
                        area_rates[area] = 0 if increase == 0 else float('inf')
            
            # ランキング作成
            if result_type == "増減数":
                ranked_areas = sorted(area_increases.items(), key=lambda x: x[1], reverse=True)[:ranking_count]
                result = f"## {target_year}年 対前年エリア別{metric_jp}増減数ランキング トップ{ranking_count}（{scope_text}）\n\n"
                
                for i, (area, increase) in enumerate(ranked_areas, 1):
                    current_val = area_current.get(area, 0)
                    previous_val = area_previous.get(area, 0)
                    rate = area_rates.get(area, 0)
                    
                    result += f"**{i}位: {area}エリア**\n"
                    result += f"- 増減数: {increase:+,}{get_unit(metric_jp)}\n"
                    result += f"- 増減率: {rate:+.1f}%\n"
                    result += f"- {target_year}年: {current_val:,}{get_unit(metric_jp)}\n"
                    result += f"- {previous_year}年: {previous_val:,}{get_unit(metric_jp)}\n\n"
            else:  # 増減率
                finite_rates = {area: rate for area, rate in area_rates.items() if rate != float('inf')}
                ranked_areas = sorted(finite_rates.items(), key=lambda x: x[1], reverse=True)[:ranking_count]
                result = f"## {target_year}年 対前年エリア別{metric_jp}増減率ランキング トップ{ranking_count}（{scope_text}）\n\n"
                
                for i, (area, rate) in enumerate(ranked_areas, 1):
                    current_val = area_current.get(area, 0)
                    previous_val = area_previous.get(area, 0)
                    increase = area_increases.get(area, 0)
                    
                    result += f"**{i}位: {area}エリア**\n"
                    result += f"- 増減率: {rate:+.1f}%\n"
                    result += f"- 増減数: {increase:+,}{get_unit(metric_jp)}\n"
                    result += f"- {target_year}年: {current_val:,}{get_unit(metric_jp)}\n"
                    result += f"- {previous_year}年: {previous_val:,}{get_unit(metric_jp)}\n\n"
        
        else:  # 期間比較
            start_year = params['start_year']
            end_year = params['end_year']
            
            # 各エリアの合計データを計算
            area_start = {}
            area_end = {}
            
            for area in areas:
                area_cities = REGION_MAP.get(area, [])
                
                # 開始年のエリア合計
                start_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @start_year & city in @area_cities")
                area_start[area] = start_data['value'].sum()
                
                # 終了年のエリア合計
                end_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @end_year & city in @area_cities")
                area_end[area] = end_data['value'].sum()
            
            # 増減数と増減率を計算
            area_increases = {}
            area_rates = {}
            
            for area in areas:
                if area in area_start and area in area_end:
                    increase = area_end[area] - area_start[area]
                    area_increases[area] = increase
                    
                    if area_start[area] != 0:
                        rate = (increase / area_start[area]) * 100
                        area_rates[area] = rate
                    else:
                        area_rates[area] = 0 if increase == 0 else float('inf')
            
            period_text = f"{start_year}年〜{end_year}年（{end_year - start_year + 1}年間）"
            
            # ランキング作成
            if result_type == "増減数":
                ranked_areas = sorted(area_increases.items(), key=lambda x: x[1], reverse=True)[:ranking_count]
                result = f"## {period_text} 期間エリア別{metric_jp}増減数ランキング トップ{ranking_count}（{scope_text}）\n\n"
                
                for i, (area, increase) in enumerate(ranked_areas, 1):
                    start_val = area_start.get(area, 0)
                    end_val = area_end.get(area, 0)
                    rate = area_rates.get(area, 0)
                    
                    result += f"**{i}位: {area}エリア**\n"
                    result += f"- 期間増減数: {increase:+,}{get_unit(metric_jp)}\n"
                    if rate != float('inf'):
                        result += f"- 期間増減率: {rate:+.1f}%\n"
                    else:
                        result += f"- 期間増減率: 新規開設\n"
                    result += f"- {end_year}年: {end_val:,}{get_unit(metric_jp)}\n"
                    result += f"- {start_year}年: {start_val:,}{get_unit(metric_jp)}\n\n"
            else:  # 増減率
                finite_rates = {area: rate for area, rate in area_rates.items() if rate != float('inf')}
                ranked_areas = sorted(finite_rates.items(), key=lambda x: x[1], reverse=True)[:ranking_count]
                result = f"## {period_text} 期間エリア別{metric_jp}増減率ランキング トップ{ranking_count}（{scope_text}）\n\n"
                
                for i, (area, rate) in enumerate(ranked_areas, 1):
                    start_val = area_start.get(area, 0)
                    end_val = area_end.get(area, 0)
                    increase = area_increases.get(area, 0)
                    
                    result += f"**{i}位: {area}エリア**\n"
                    result += f"- 期間増減率: {rate:+.1f}%\n"
                    result += f"- 期間増減数: {increase:+,}{get_unit(metric_jp)}\n"
                    result += f"- {end_year}年: {end_val:,}{get_unit(metric_jp)}\n"
                    result += f"- {start_year}年: {start_val:,}{get_unit(metric_jp)}\n\n"
        
        return result
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        if debug_mode:
            import streamlit as st
            st.error(f"エリア別増減ランキング処理中にエラー: {str(e)}")
            st.code(error_detail)
        return f"""**エリア別増減ランキング処理中にエラー**

**エラー:** {str(e)}

**パラメータ:** 
- エリア: {areas}
- 分析タイプ: {analysis_type}
- 結果タイプ: {result_type}
"""

def handle_change_ranking_period(df, metric_en, metric_jp, target_cities, scope_text, start_year, end_year, result_type, ranking_count, debug_mode=False):
    """期間比較の増減ランキング"""
    try:
        # データ取得前の確認
        if debug_mode:
            import streamlit as st
            st.write(f"**🔍 handle_change_ranking_period デバッグ**")
            st.write(f"- 開始年: {start_year}, 終了年: {end_year}, 指標: {metric_en}")
            st.write(f"- データフレーム行数: {len(df):,}行")
            st.write(f"- 利用可能な年度: {sorted(df['year'].unique())}")
            st.write(f"- 利用可能な指標: {sorted(df['metric'].unique())}")
            st.write(f"- 対象市町村数: {len(target_cities)}")
        
        # エリア名と県名を除外するフィルタ
        exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
        
        # データ取得 - より安全なフィルタリング（エリア・県名を除外）
        start_data_all = df[
            (df['metric'] == metric_en) & 
            (df['cat1'] == 'total') & 
            (df['year'] == start_year) &
            (~df['city'].isin(exclude_list))  # エリア・県名を除外
        ]
        end_data_all = df[
            (df['metric'] == metric_en) & 
            (df['cat1'] == 'total') & 
            (df['year'] == end_year) &
            (~df['city'].isin(exclude_list))  # エリア・県名を除外
        ]
        
        if debug_mode:
            st.write(f"- {start_year}年データ行数（除外後）: {len(start_data_all)}行")
            st.write(f"- {end_year}年データ行数（除外後）: {len(end_data_all)}行")
        
        if start_data_all.empty:
            available_years = sorted(df[df['metric'] == metric_en]['year'].unique())
            return f"""## {start_year}年〜{end_year}年 期間{metric_jp}{result_type}ランキング

❌ **{start_year}年のデータが見つかりません。**

**指標「{metric_jp}」({metric_en})の利用可能な年度:** {available_years}

**データ状況:**
- 総データ件数: {len(df):,}行
- {metric_jp}データ件数: {len(df[df['metric'] == metric_en]):,}行
- totalカテゴリデータ件数: {len(df[(df['metric'] == metric_en) & (df['cat1'] == 'total')]):,}行
"""
        
        if end_data_all.empty:
            available_years = sorted(df[df['metric'] == metric_en]['year'].unique())
            return f"""## {start_year}年〜{end_year}年 期間{metric_jp}{result_type}ランキング

❌ **{end_year}年のデータが見つかりません。**

**指標「{metric_jp}」({metric_en})の利用可能な年度:** {available_years}
"""
        
        # 対象市町村でフィルタ
        start_data = start_data_all[start_data_all['city'].isin(target_cities)].set_index('city')['value']
        end_data = end_data_all[end_data_all['city'].isin(target_cities)].set_index('city')['value']
        
        if debug_mode:
            st.write(f"- フィルタ後 {start_year}年データ: {len(start_data)}市町村")
            st.write(f"- フィルタ後 {end_year}年データ: {len(end_data)}市町村")
        
        # 両方の年にデータがある市町村のみ対象
        common_cities = start_data.index.intersection(end_data.index)
        
        if debug_mode:
            st.write(f"- 共通市町村数: {len(common_cities)}市町村")
            if len(common_cities) > 0:
                st.write(f"- 共通市町村例: {list(common_cities)[:5]}")
        
        if len(common_cities) == 0:
            available_start = set(start_data_all['city'].unique())
            available_end = set(end_data_all['city'].unique())
            target_set = set(target_cities)
            
            return f"""## {start_year}年〜{end_year}年 期間{metric_jp}{result_type}ランキング
            
❌ **比較可能なデータが見つかりません。**

**データ状況:**
- {start_year}年のデータがある市町村数: {len(available_start)}
- {end_year}年のデータがある市町村数: {len(available_end)}  
- 対象市町村数: {len(target_set)}
- 両方の年にデータがある対象市町村: {len(common_cities)}

**{start_year}年にデータがある市町村:** {sorted(available_start)[:10]}...
**{end_year}年にデータがある市町村:** {sorted(available_end)[:10]}...
**対象市町村:** {sorted(target_cities)[:10]}...
"""
        
        # 増減数と増減率を計算
        increases = end_data[common_cities] - start_data[common_cities]
        
        if debug_mode:
            st.write(f"- 増減数計算完了, データ数: {len(increases)}件")
            # サンプルデータを表示
            sample_increases = increases.sort_values(ascending=False).head(3)
            st.write(f"**増減数サンプル（上位3件）:**")
            for city, increase in sample_increases.items():
                st.write(f"  - {city}: {increase:+.1f}{get_unit(metric_jp)}")
        
        # ゼロ除算を避けるため、分母が0の場合は0を設定
        rates = increases.copy()
        for city in common_cities:
            if start_data[city] != 0:
                rates[city] = (increases[city] / start_data[city]) * 100
            else:
                rates[city] = 0 if increases[city] == 0 else float('inf')
        
        period_text = f"{start_year}年〜{end_year}年（{end_year - start_year + 1}年間）"
        
        if result_type == "増減数":
            ranked_data = increases.sort_values(ascending=False).head(ranking_count)
            
            if debug_mode:
                st.write(f"- ランキングデータ: {len(ranked_data)}件")
            
            result = f"## {period_text} 期間{metric_jp}増減数ランキング トップ{ranking_count}（{scope_text}）\n\n"
            
            for i, (city, increase) in enumerate(ranked_data.items(), 1):
                start_val = start_data.get(city, 0)
                end_val = end_data.get(city, 0)
                rate = rates.get(city, 0)
                
                result += f"**{i}位: {city}**\n"
                result += f"- 期間増減数: {increase:+,}{get_unit(metric_jp)}\n"
                if rate != float('inf'):
                    result += f"- 期間増減率: {rate:+.1f}%\n"
                else:
                    result += f"- 期間増減率: 新規開設\n"
                result += f"- {end_year}年: {end_val:,}{get_unit(metric_jp)}\n"
                result += f"- {start_year}年: {start_val:,}{get_unit(metric_jp)}\n\n"
        else:  # 増減率
            # 無限大を除外してソート
            finite_rates = rates[rates != float('inf')]
            ranked_data = finite_rates.sort_values(ascending=False).head(ranking_count)
            result = f"## {period_text} 期間{metric_jp}増減率ランキング トップ{ranking_count}（{scope_text}）\n\n"
            
            for i, (city, rate) in enumerate(ranked_data.items(), 1):
                start_val = start_data.get(city, 0)
                end_val = end_data.get(city, 0)
                increase = increases.get(city, 0)
                
                result += f"**{i}位: {city}**\n"
                result += f"- 期間増減率: {rate:+.1f}%\n"
                result += f"- 期間増減数: {increase:+,}{get_unit(metric_jp)}\n"
                result += f"- {end_year}年: {end_val:,}{get_unit(metric_jp)}\n"
                result += f"- {start_year}年: {start_val:,}{get_unit(metric_jp)}\n\n"
        
        if debug_mode:
            st.write(f"- 結果生成完了, 文字数: {len(result)}文字")
        
        return result
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        if debug_mode:
            import streamlit as st
            st.error(f"期間比較ランキング処理中にエラー: {str(e)}")
            st.code(error_detail)
        return f"""**期間比較ランキング処理中にエラー**

**エラー:** {str(e)}

**パラメータ:** 
- 開始年: {start_year}
- 終了年: {end_year} 
- 対象市町村数: {len(target_cities)}
- 指標: {metric_en}
"""

def handle_change_ranking_year_over_year(df, metric_en, metric_jp, target_cities, scope_text, target_year, result_type, ranking_count):
    """対前年比較の増減ランキング"""
    try:
        # エリア名と県名を除外するフィルタ
        exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
        
        # 対象年と前年のデータ取得
        previous_year = target_year - 1
        
        current_data_all = df[
            (df['metric'] == metric_en) & 
            (df['cat1'] == 'total') & 
            (df['year'] == target_year) &
            (~df['city'].isin(exclude_list))
        ]
        previous_data_all = df[
            (df['metric'] == metric_en) & 
            (df['cat1'] == 'total') & 
            (df['year'] == previous_year) &
            (~df['city'].isin(exclude_list))
        ]
        
        if current_data_all.empty or previous_data_all.empty:
            return f"指定年度のデータが不足しています。{target_year}年または{previous_year}年のデータがありません。"
        
        # 対象市町村でフィルタ
        current_data = current_data_all[current_data_all['city'].isin(target_cities)].set_index('city')['value']
        previous_data = previous_data_all[previous_data_all['city'].isin(target_cities)].set_index('city')['value']
        
        # 両方の年にデータがある市町村のみ対象
        common_cities = current_data.index.intersection(previous_data.index)
        
        if len(common_cities) == 0:
            return f"比較可能なデータがありません。"
        
        # 増減数と増減率を計算
        increases = current_data[common_cities] - previous_data[common_cities]
        
        # ゼロ除算を避けるため、分母が0の場合は特別扱い
        rates = increases.copy()
        for city in common_cities:
            if previous_data[city] != 0:
                rates[city] = (increases[city] / previous_data[city]) * 100
            else:
                rates[city] = 0 if increases[city] == 0 else float('inf')
        
        if result_type == "増減数":
            ranked_data = increases.sort_values(ascending=False).head(ranking_count)
            result = f"## {target_year}年 対前年{metric_jp}増減数ランキング トップ{ranking_count}（{scope_text}）\n\n"
            
            for i, (city, increase) in enumerate(ranked_data.items(), 1):
                current_val = current_data.get(city, 0)
                previous_val = previous_data.get(city, 0)
                rate = rates.get(city, 0)
                
                result += f"**{i}位: {city}**\n"
                result += f"- 対前年増減数: {increase:+,}{get_unit(metric_jp)}\n"
                if rate != float('inf'):
                    result += f"- 対前年増減率: {rate:+.1f}%\n"
                else:
                    result += f"- 対前年増減率: 新規開設\n"
                result += f"- {target_year}年: {current_val:,}{get_unit(metric_jp)}\n"
                result += f"- {previous_year}年: {previous_val:,}{get_unit(metric_jp)}\n\n"
        else:  # 増減率
            # 無限大を除外してソート
            finite_rates = rates[rates != float('inf')]
            ranked_data = finite_rates.sort_values(ascending=False).head(ranking_count)
            result = f"## {target_year}年 対前年{metric_jp}増減率ランキング トップ{ranking_count}（{scope_text}）\n\n"
            
            for i, (city, rate) in enumerate(ranked_data.items(), 1):
                current_val = current_data.get(city, 0)
                previous_val = previous_data.get(city, 0)
                increase = increases.get(city, 0)
                
                result += f"**{i}位: {city}**\n"
                result += f"- 対前年増減率: {rate:+.1f}%\n"
                result += f"- 対前年増減数: {increase:+,}{get_unit(metric_jp)}\n"
                result += f"- {target_year}年: {current_val:,}{get_unit(metric_jp)}\n"
                result += f"- {previous_year}年: {previous_val:,}{get_unit(metric_jp)}\n\n"
        
        return result
        
    except Exception as e:
        return f"対前年比較ランキング処理中にエラー: {str(e)}"

def handle_basic_info_multi_metrics(df, metrics, location_type, locations, target_year):
    """複数指標対応の基本情報取得処理（市町村ごとにまとめて表示）"""
    # エリア名と県名を除外する共通フィルタ
    exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
    
    if location_type == "市町村":
        result = f"## {target_year}年 基本情報\n\n"
        
        # 各指標のランキング情報を事前に計算
        all_rankings = {}
        all_data = {}
        
        for metric_jp in metrics:
            metric_en = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}[metric_jp]
            
            # 全市町村データを取得してランキング作成
            all_municipal_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @target_year & ~city.isin(@exclude_list)")
            
            if not all_municipal_data.empty:
                ranking = all_municipal_data.sort_values('value', ascending=False).reset_index(drop=True)
                all_rankings[metric_jp] = ranking
                
                # 市町村ごとのデータを辞書化
                city_data = {}
                for _, row in all_municipal_data.iterrows():
                    city_data[row['city']] = row['value']
                all_data[metric_jp] = city_data
        
        # 市町村ごとに情報をまとめて表示
        for city in locations:
            result += f"### {city}\n\n"
            
            for metric_jp in metrics:
                if metric_jp in all_data and city in all_data[metric_jp]:
                    value = all_data[metric_jp][city]
                    result += f"**{metric_jp}:** {value:,}{get_unit(metric_jp)}"
                    
                    # ランキング情報を追加
                    if metric_jp in all_rankings:
                        ranking = all_rankings[metric_jp]
                        city_rank_info = ranking[ranking['city'] == city]
                        if not city_rank_info.empty:
                            rank = city_rank_info.index[0] + 1
                            result += f" （全市町村中 {rank}位／{len(ranking)}市町村）"
                    result += "  \n"  # 改行を追加（マークダウンの改行）
                else:
                    result += f"**{metric_jp}:** {target_year}年のデータがありません。  \n"
            
            result += "\n"
        
        return result
    
    elif location_type == "エリア":
        result = f"## {target_year}年 エリア別基本情報\n\n"
        
        for area in locations:
            result += f"### {area}エリア\n\n"
            area_cities = REGION_MAP.get(area, [])
            
            for metric_jp in metrics:
                metric_en = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}[metric_jp]
                
                # エリアデータ集計
                area_data = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @target_year & ~city.isin(@exclude_list)")
                total_value = area_data['value'].sum()
                
                result += f"**{metric_jp}:** {total_value:,}{get_unit(metric_jp)}  \n"
                
                # エリア内トップ3
                top3 = area_data.sort_values('value', ascending=False).head(3)
                if not top3.empty:
                    result += f"　主要市町村: "
                    details = [f"{row['city']}({row['value']:,})" for _, row in top3.iterrows()]
                    result += "、".join(details) + "  \n"
            
            result += "\n"
            
        return result
    
    else:  # 全体
        result = f"## {target_year}年 沖縄県全体基本情報\n\n"
        
        for metric_jp in metrics:
            metric_en = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}[metric_jp]
            
            # 市町村データのみをフィルタしてランキングと統計を計算
            data_for_ranking = df.query(f"metric == @metric_en & cat1 == 'total' & year == @target_year & ~city.isin(@exclude_list)")
            total_value = data_for_ranking['value'].sum()
            
            result += f"**{metric_jp}合計:** {total_value:,}{get_unit(metric_jp)}  \n"
            result += f"**集計市町村数:** {len(data_for_ranking)}市町村  \n"
            
            # トップ5
            top5 = data_for_ranking.sort_values('value', ascending=False).head(5)
            result += f"**{metric_jp}トップ5市町村:**  \n"
            for i, (_, row) in enumerate(top5.iterrows(), 1):
                result += f"　{i}位: {row['city']} ({row['value']:,}{get_unit(metric_jp)})  \n"
            result += "  \n"
            
        return result

def handle_ranking(df, metric_en, metric_jp, location_type, locations, ranking_count, ranking_year):
    """ランキング表示の処理（棒グラフを生成・エリア対応版）"""
    import plotly.graph_objects as go
    
    # エリア名と県名を除外するフィルタ
    exclude_list = ['沖縄県', '南部', '中部', '北部', '宮古', '八重山', '離島']
    
    # データの対象範囲を決定
    if location_type == "市町村" and locations and locations != ["全体"]:
        data = df.query(f"city in @locations & metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
        scope_text = f"選択市町村（{'・'.join(locations[:3])}{'など' if len(locations) > 3 else ''}）"
        
        # 該当データがない場合はメッセージを返す
        if data.empty:
            return f"## {ranking_year}年 {scope_text} {metric_jp}ランキング\n\n該当するデータがありません。"
        
        ranking = data.sort_values('value', ascending=False).head(ranking_count)
        
        # グラフ用データ
        ranking_for_plot = ranking.sort_values('value', ascending=True)
        x_values = ranking_for_plot['value']
        y_labels = ranking_for_plot['city']
        
    elif location_type == "エリア" and locations and locations != ["全体"]:
        # エリア別集計処理
        area_data = {}
        
        for area in locations:
            area_cities = REGION_MAP.get(area, [])
            
            # エリア内の市町村データを取得
            area_city_data = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
            
            # エリア合計を計算
            area_total = area_city_data['value'].sum()
            area_data[area] = area_total
        
        if not area_data:
            return f"## {ranking_year}年 エリア別 {metric_jp}ランキング\n\n該当するデータがありません。"
        
        # エリアをランキング順にソート（降順）
        sorted_areas = sorted(area_data.items(), key=lambda x: x[1], reverse=True)
        
        # グラフ用に昇順でソート（Plotlyの水平棒グラフ用）
        sorted_areas_for_plot = sorted(area_data.items(), key=lambda x: x[1], reverse=False)
        
        scope_text = f"{'・'.join(locations)}エリア"
        x_values = [value for area, value in sorted_areas_for_plot]
        y_labels = [f"{area}エリア" for area, value in sorted_areas_for_plot]
        
    else:  # 全体またはフィルタなし
        data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @ranking_year & ~city.isin(@exclude_list)")
        scope_text = "全市町村"
        
        # 該当データがない場合はメッセージを返す
        if data.empty:
            return f"## {ranking_year}年 {scope_text} {metric_jp}ランキング\n\n該当するデータがありません。"
        
        ranking = data.sort_values('value', ascending=False).head(ranking_count)
        
        # グラフ用データ
        ranking_for_plot = ranking.sort_values('value', ascending=True)
        x_values = ranking_for_plot['value']
        y_labels = ranking_for_plot['city']
    
    # 棒グラフ作成
    unit = get_unit(metric_jp)
    title_text = f"{ranking_year}年 {scope_text} {metric_jp}ランキング"
    if location_type != "エリア":
        title_text += f" トップ{ranking_count}"
    
    fig = go.Figure(go.Bar(
        x=x_values,
        y=y_labels,
        orientation='h',
        text=[f'{x:,}' for x in x_values],  # バーの横に数値を表示
        textposition='outside',
        hovertemplate=f"%{{y}}: %{{x:,}}{unit}<extra></extra>",
        marker_color='cornflowerblue'
    ))
    
    fig.update_layout(
        title=title_text,
        xaxis_title=f"{metric_jp} ({unit})",
        yaxis_title="エリア" if location_type == "エリア" else "市町村",
        yaxis=dict(tickmode='linear'),  # すべてのラベルを表示
        height=max(400, len(y_labels) * 40),  # 件数に応じて高さを調整
        margin=dict(l=120, r=40, t=80, b=40)  # 左マージンを広げて名前を見やすくする
    )
    
    return fig

def display_help_content():
    """ヘルプコンテンツの表示（ブラッシュアップ版）"""
    
    help_sections = {
        "🎯 アプリ概要": {
            "title": "このアプリでできること",
            "content": """
            ### 🎯 このアプリでできること
            **沖縄県全41市町村**の宿泊施設データを多角的に分析できる総合ダッシュボードです。
            
            #### 📊 分析対象データ
            - **期間**: 昭和47年〜令和6年（**52年間**の超長期トレンド）
            - **対象**: 全41市町村の宿泊施設（ホテル・旅館・民宿・ペンション等）
            - **指標**: 施設数（軒数）・客室数・収容人数
            - **データソース**: 沖縄県「宿泊施設実態調査」（年1回実施）
            
            #### 🔍 5つの分析アプローチ
            1. **🤖 ランキング分析**: 自然言語形式でデータを質問・分析
            2. **🏘️ 市町村別分析**: 特定の市町村を選んで詳細分析
            3. **🏨 ホテル・旅館規模別**: 施設の規模（大・中・小）による分析
            4. **🏛️ ホテル・旅館種別**: リゾート・ビジネス・シティホテル等の分析
            5. **🗺️ エリア別分析**: 南部・中部・北部・宮古・八重山・離島の分析
            
            #### ✨ 主な特徴
            - **操作が簡単**: クリックとドラッグで直感的に操作
            - **リアルタイム更新**: 設定変更で即座にグラフが更新
            - **比較分析**: 複数の市町村・エリアを同時に比較
            - **順位表示**: 全41市町村中の順位を自動表示
            - **長期トレンド**: 最大52年間の推移分析が可能
            
            #### 👥 想定利用者
            - **行政職員**: 政策立案・予算編成の基礎資料作成
            - **観光事業者**: 市場分析・競合調査・投資判断
            - **研究者・学生**: 学術研究・卒業論文の資料収集
            - **メディア関係者**: 記事作成・番組制作の背景データ
            - **一般県民**: 地域理解・観光情報の把握
            """
        },
        
        "🤖 ランキング分析の使い方": {
            "title": "自然言語形式で簡単データ分析",
            "content": """
            ### 🤖 ランキング分析タブの使い方
            
            #### 🎯 このタブの特徴
            **質問を構築するだけ**で、複雑なデータ分析を自動実行します。プログラミング知識は一切不要！
            
            #### 📝 6つの質問タイプ詳細
            
            **1. 基本情報取得** 🔍
            - **用途**: 複数指標を一度に確認
            - **例**: 「那覇市の2024年の軒数・客室数・収容人数は？」
            - **特徴**: 最大3指標を同時表示、全市町村中の順位も表示
            - **活用場面**: 基礎データの把握、プレゼン資料作成
            
            **2. ランキング表示** 🏆
            - **用途**: トップランキングを自動生成
            - **例**: 「2024年の客室数トップ10は？」
            - **特徴**: 3〜20件まで表示件数選択可能
            - **活用場面**: 競合分析、市場ポジション把握
            
            **3. 増減数ランキング** 📈
            - **用途**: 成長量（絶対数）で市町村をランキング
            - **例**: 「2024年の対前年軒数増減数トップ5は？」
            - **特徴**: 対前年比較・期間比較の2モード
            - **活用場面**: 成長市場の発見、投資機会の特定
            
            **4. 増減率ランキング** 📊
            - **用途**: 成長率（％）で市町村をランキング
            - **例**: 「過去3年間の収容人数増減率トップ5は？」
            - **特徴**: 小規模市町村でも上位ランクイン可能
            - **活用場面**: 高成長地域の発見、トレンド分析
            
            **5. 増減・伸び率分析** 🔬
            - **用途**: 特定市町村の成長率を詳細分析
            - **例**: 「石垣市の対前年客室数増減率は？」
            - **特徴**: 全市町村中の順位付きで相対評価
            - **活用場面**: 個別地域の詳細分析、競合比較
            
            **6. 期間推移分析** 📉
            - **用途**: 長期トレンドを可視化
            - **例**: 「宮古島市の過去10年間の軒数推移は？」
            - **特徴**: 年別推移と期間全体の変化率を表示
            - **活用場面**: 長期計画策定、歴史的変化の把握
            
            #### 🛠️ 操作手順（5ステップ）
            1. **質問タイプを選択** → 6つから用途に応じて選択
            2. **指標を選択** → 軒数・客室数・収容人数から選択
            3. **場所を選択** → 市町村・エリア・全体から選択
            4. **詳細設定** → 年度・表示件数・期間等を設定
            5. **実行ボタンをクリック** → 結果が自動生成
            
            #### 💡 効果的な活用のコツ
            
            **初心者向け**:
            - **プレビュー機能**で質問内容を事前確認
            - **基本情報取得**から始めて全体像を把握
            - **複数指標同時取得**で効率的な情報収集
            
            **中級者向け**:
            - **増減率ランキング**で高成長地域を発見
            - **期間比較**で短期・長期のトレンド把握
            - **場所フィルタ**で特定エリア内の競合分析
            
            **上級者向け**:
            - **複数の質問タイプを組み合わせ**て多角的分析
            - **異なる期間設定**で景気サイクルの影響分析
            - **指標別ランキング**で市場特性の違いを把握
            """
        },
        
        "🏘️ 市町村別分析の使い方": {
            "title": "市町村を深掘り分析",
            "content": """
            ### 🏘️ 市町村別分析タブの使い方
            
            #### 🎯 このタブの特徴
            選択した市町村の**宿泊形態別**データを詳細分析。**最大41市町村を同時比較**可能です。
            
            #### 📊 分析内容詳細
            
            **対象データ**: 全宿泊施設（ホテル・旅館・民宿・ペンション等）
            **期間**: 2007年〜2024年（18年間）
            
            **7つの宿泊形態分類**:
            - **ホテル・旅館**: 最も一般的な宿泊施設
            - **民宿**: 地域密着型の小規模宿泊施設
            - **ペンション・貸別荘**: レジャー・長期滞在向け
            - **ドミトリー・ゲストハウス**: バックパッカー・若年層向け
            - **ウィークリーマンション**: 長期滞在・ビジネス向け
            - **団体経営施設**: 企業・団体運営の宿泊施設
            - **ユースホステル**: 青少年向け低価格宿泊施設
            
            #### 🛠️ 操作方法詳細
            
            **1. 基本設定**
            - **市町村選択**: 比較したい市町村を複数選択
              - 💡 類似規模の市町村を選んで比較分析
              - 💡 隣接市町村を選んで連携効果を分析
            - **指標選択**: 軒数・客室数・収容人数から選択
            - **期間設定**: スライダーで分析期間を調整（最短1年〜最長18年）
            
            **2. 表示モード切り替え**
            - **詳細項目OFF**: Total（全宿泊形態合計）のみ表示
              - メリット: シンプルで見やすい
              - 用途: 全体トレンドの把握
            - **詳細項目ON**: 宿泊形態ごとの詳細データも表示
              - メリット: 市場構成の詳細分析
              - 用途: 競合分析、市場機会の発見
            
            #### 📈 グラフの見方・活用法
            
            **ライングラフの特徴**:
            - **縦軸**: 指標の値（軒数・客室数・収容人数）
            - **横軸**: 年度（選択した期間）
            - **線の色**: 市町村ごとに異なる色で表示
            - **順位表示**: マウスオーバーで全市町村中の順位を確認
            
            **効果的な読み方**:
            - **線の傾き**: 急上昇は高成長、急下降は市場縮小
            - **線の位置**: 上位は大規模市場、下位は小規模市場
            - **線の形状**: 直線は安定成長、波形は変動大
            - **順位変動**: 順位上昇は相対的成長力の向上
            
            #### 📋 データテーブルの活用法
            
            **テーブル構成**:
            - **行**: 市町村名（市町村コード順で統一表示）
            - **列**: 年度（選択期間の各年）
            - **数値**: 千の位区切りで見やすく表示
            
            **活用のコツ**:
            - **横方向の読み取り**: 特定市町村の時系列変化
            - **縦方向の読み取り**: 特定年の市町村間比較
            - **数値のコピー**: データをExcel等に貼り付けて追加分析
            
            #### 💡 分析パターン例
            
            **競合分析パターン**:
            1. 同規模の市町村を3〜5個選択
            2. 詳細項目ONで宿泊形態別に比較
            3. 成長している形態と停滞している形態を特定
            4. 自地域の戦略立案に活用
            
            **地域連携分析パターン**:
            1. 隣接する市町村を複数選択
            2. 期間を長めに設定（10年以上）
            3. 地域全体のトレンドと個別トレンドを比較
            4. 連携効果や競合関係を分析
            
            **市場機会発見パターン**:
            1. 全41市町村を一度に選択
            2. 特定の宿泊形態（例：ゲストハウス）に注目
            3. 急成長している市町村を特定
            4. 成功要因を別途調査して横展開検討
            """
        },
        
        "🏨 規模別分析の使い方": {
            "title": "ホテル・旅館の規模による分析",
            "content": """
            ### 🏨 ホテル・旅館特化 規模別分析の使い方
            
            #### 🎯 このタブの特徴
            **ホテル・旅館のみ**を対象に、施設の**規模別**で詳細分析。民宿・ペンション等は除外した純粋なホテル市場の分析が可能です。
            
            #### 📏 規模分類の詳細
            
            **3段階の規模分類**（収容人数ベース）:
            
            **🏢 大規模施設（300人以上）**
            - **特徴**: リゾートホテル、シティホテルが中心
            - **対象客層**: 団体旅行、国際観光客、高級志向客
            - **立地**: 主要観光地、都市部中心地
            - **投資規模**: 数十億円〜数百億円
            
            **🏨 中規模施設（100人以上300人未満）**
            - **特徴**: ビジネスホテル、中規模リゾートが中心
            - **対象客層**: 個人旅行、ビジネス客、ファミリー
            - **立地**: 市街地、観光地周辺
            - **投資規模**: 数億円〜数十億円
            
            **🏠 小規模施設（100人未満）**
            - **特徴**: 小規模ホテル、旅館が中心
            - **対象客層**: 個人旅行、地域密着型利用
            - **立地**: 住宅地、郊外、離島
            - **投資規模**: 数千万円〜数億円
            
            #### 📊 分析対象・期間
            - **期間**: 2007年〜2024年（**18年間**の長期データ）
            - **対象**: ホテル・旅館のみ（民宿・ペンション等は除外）
            - **データ特徴**: より詳細で専門的な市場分析が可能
            
            #### 🛠️ 操作方法の詳細
            
            **1. 基本設定のコツ**
            - **市町村選択**: 
              - 💡 観光地型（石垣市、宮古島市等）
              - 💡 都市型（那覇市、浦添市等）
              - 💡 混合型（名護市、沖縄市等）
            - **規模分類選択**: 分析目的に応じて選択
              - 💡 全選択: 市場全体の構造把握
              - 💡 大規模のみ: 高級市場の分析
              - 💡 小規模のみ: 地域密着市場の分析
            
            **2. 表示構成の理解**
            - **Total表示**: まず全規模合計で全体トレンドを把握
            - **規模別詳細**: 各規模での成長パターンを個別分析
            
            #### 📈 分析パターンと活用例
            
            **🎯 観光地の特性分析**
            
            **リゾート地（石垣市、宮古島市等）**:
            - 大規模施設の比率が高い
            - 観光ブーム時に大規模施設が急増
            - 季節変動や外的要因（コロナ等）の影響大
            
            **都市部（那覇市、浦添市等）**:
            - 中規模施設（ビジネスホテル）が中心
            - 安定的な需要で変動が少ない
            - 再開発による新規参入が多い
            
            **地方部（名護市、今帰仁村等）**:
            - 小規模施設が多い
            - 地域イベントや観光開発の影響を受けやすい
            - 家族経営的な施設が中心
            
            #### 💼 投資・開発の参考活用
            
            **市場参入の判断材料**:
            1. **成長規模の特定**: どの規模帯が成長しているか
            2. **競合密度の把握**: 既存施設の集中度
            3. **市場空白の発見**: 不足している規模帯の特定
            4. **適正規模の判断**: 地域需要に合った施設規模
            
            **リスク分析**:
            1. **市場飽和度**: 施設数の過度な集中
            2. **競合激化**: 同規模施設の急増
            3. **需要変動**: 外的要因による影響度
            4. **参入障壁**: 大規模開発の可能性
            
            #### 📊 データの深い読み方
            
            **成長パターンの分類**:
            - **安定成長型**: 継続的な右肩上がり
            - **急成長型**: 短期間での大幅増加
            - **循環型**: 一定期間での増減の繰り返し
            - **停滞・減少型**: 横ばいまたは減少傾向
            
            **規模間の関係性**:
            - **代替関係**: 大規模減少→中規模増加
            - **補完関係**: 全規模で同時成長
            - **独立関係**: 規模別に異なる動き
            
            #### 💡 高度な分析テクニック
            
            **時系列分析**:
            - リーマンショック（2008年）の影響
            - 東日本大震災（2011年）の影響
            - コロナ禍（2020-2022年）の影響
            - 回復期（2023年以降）の特徴
            
            **比較分析**:
            - 同規模施設間での地域差比較
            - 異なる規模での成長率比較
            - 全国平均や他県との比較（外部データ併用）
            """
        },
        
        "🏛️ ホテル種別分析の使い方": {
            "title": "ホテル・旅館の種別による詳細分析",
            "content": """
            ### 🏛️ ホテル・旅館特化 宿泊形態別分析の使い方
            
            #### 🎯 このタブの特徴
            ホテル・旅館を**機能・サービス別**に細分化して分析する**最も詳細**なタブです。観光形態や利用目的に応じた専門的な市場分析が可能です。
            
            #### 🏨 4つのホテル種別詳細
            
            **🏖️ リゾートホテル**
            - **主要機能**: 観光・レジャー特化、滞在型サービス
            - **対象客層**: 観光客、ファミリー、カップル
            - **立地特性**: 海沿い、景勝地、テーマパーク周辺
            - **サービス**: プール、スパ、マリンアクティビティ
            - **客室特徴**: オーシャンビュー、広めの客室、リゾート感
            - **沖縄での特徴**: 最も重要なカテゴリ、外資系チェーンも多数
            
            **💼 ビジネスホテル**
            - **主要機能**: 出張・商用客特化、効率重視
            - **対象客層**: ビジネス客、短期滞在者
            - **立地特性**: 駅近、市街地中心、ビジネス街
            - **サービス**: 会議室、ビジネスセンター、Wi-Fi
            - **客室特徴**: コンパクト、機能性重視、デスクワーク対応
            - **沖縄での特徴**: 那覇市中心に集中、本土チェーンが多数参入
            
            **🏙️ シティホテル**
            - **主要機能**: 都市部総合サービス、多目的対応
            - **対象客層**: 観光客、ビジネス客、宴会利用者
            - **立地特性**: 都市中心部、交通便利地
            - **サービス**: レストラン、宴会場、コンシェルジュ
            - **客室特徴**: 多様なタイプ、高級感、総合的サービス
            - **沖縄での特徴**: 那覇市中心、老舗ホテルと新興ホテルが混在
            
            **🏯 旅館**
            - **主要機能**: 日本伝統スタイル、文化体験
            - **対象客層**: 日本文化体験希望者、中高年層
            - **立地特性**: 温泉地、歴史的地域、自然豊かな場所
            - **サービス**: 和食、温泉、伝統的おもてなし
            - **客室特徴**: 和室、畳、伝統的内装
            - **沖縄での特徴**: 数は少ないが独特の「沖縄スタイル旅館」が存在
            
            #### 📊 分析データの特徴
            - **期間**: 2014年〜2024年（**11年間**のより詳細な分析期間）
            - **開始年の意義**: 2014年から詳細分類開始、より正確な市場把握
            - **データ精度**: 従来より細分化された高精度データ
            - **分析深度**: 観光形態や利用目的に応じた専門分析が可能
            
            #### 🛠️ 4つの表示モード完全ガイド
            
            **1. 概要表示** 📊
            - **用途**: Total（全種別合計）の推移を表示
            - **メリット**: 全体トレンドの把握、大局的視点
            - **活用場面**: 
              - 市場全体の成長性評価
              - 政策効果の全体的影響把握
              - 他地域との比較基準作成
            
            **2. 規模別詳細** 🏢
            - **用途**: 大規模・中規模・小規模ごとの分析
            - **メリット**: 投資規模別の市場動向把握
            - **活用場面**:
              - 投資計画の規模決定
              - 競合の投資動向分析
              - 市場参入の適正規模判断
            
            **3. ホテル種別詳細** 🏨
            - **用途**: リゾート・ビジネス・シティ・旅館ごとの分析
            - **メリット**: 機能特化型の成長トレンド把握
            - **活用場面**:
              - コンセプト決定（どの種別で参入するか）
              - ターゲット客層の需要分析
              - サービス差別化戦略の立案
            
            **4. マトリックス表示** 📋
            - **用途**: ホテル種別×規模のクロス集計表示
            - **メリット**: 市場の詳細な構造分析
            - **活用場面**:
              - ポジショニング分析
              - 競合マッピング
              - 市場空白の発見
            
            #### 📈 マトリックス表示の詳細解説
            
            **マトリックスの見方**:
            - **行（縦軸）**: ホテル種別（リゾート・ビジネス・シティ・旅館）
            - **列（横軸）**: 規模分類（大規模・中規模・小規模）
            - **セルの値**: 選択した指標（軒数・客室数・収容人数）
            - **色の濃淡**: 数値の大小を視覚的に表現
            
            **読み取りのコツ**:
            - **濃い色のセル**: その組み合わせが市場の主力
            - **薄い色のセル**: 市場空白または少数派
            - **行の比較**: 種別別の規模構成
            - **列の比較**: 規模別の種別構成
            
            #### 🎯 活用シーン別詳細ガイド
            
            **🏖️ 観光戦略の立案**
            
            **リゾートホテル分析の活用**:
            1. **成長トレンド**: 過去11年の推移から今後の予測
            2. **規模別動向**: 大型リゾートvs小規模リゾートの成長差
            3. **地域特性**: エリア別のリゾート集積度
            4. **季節性対応**: 通年営業可能な施設の重要性
            
            **政策立案への活用**:
            - 観光振興計画での重点エリア設定
            - インフラ整備の優先順位決定
            - 規制緩和・優遇措置の対象選定
            
            **💼 ビジネス需要の分析**
            
            **ビジネスホテル市場の把握**:
            1. **立地分析**: 那覇市中心部の供給状況
            2. **競合状況**: 既存チェーンの市場シェア
            3. **成長可能性**: ビジネス需要の今後の見通し
            4. **差別化要因**: 求められるサービスレベル
            
            **投資判断への活用**:
            - 市場参入時期の決定
            - 適正料金設定の基準
            - サービス内容の差別化ポイント
            
            #### 🔍 競合分析の高度なテクニック
            
            **ポジショニングマップの作成**:
            1. **X軸**: 施設規模（小規模→大規模）
            2. **Y軸**: サービス特化度（汎用→特化）
            3. **プロット**: 各ホテル種別×規模の組み合わせ
            4. **空白発見**: 競合の少ないポジション特定
            
            **時系列競合分析**:
            1. **参入時期**: 各カテゴリの新規参入パターン
            2. **成長速度**: カテゴリ別の拡大ペース
            3. **市場成熟度**: 飽和に近いカテゴリの特定
            4. **次期トレンド**: 今後成長が期待されるカテゴリ予測
            
            #### 💡 データ分析の上級テクニック
            
            **複合分析の手法**:
            1. **他タブとの連携**: エリア別分析と組み合わせて地域特性把握
            2. **外部データ連携**: 観光客数、経済指標との相関分析
            3. **季節性分析**: 年間を通じた需要変動の把握
            4. **将来予測**: トレンドラインから今後の市場予測
            
            **注意点とデータ解釈**:
            - **サンプル数**: 小規模カテゴリは変動が大きい
            - **分類変更**: 2014年以前のデータとの連続性に注意
            - **外的要因**: コロナ禍等の特殊事情を考慮
            - **地域性**: 沖縄特有の観光形態を理解した上での分析が重要
            """
        },
        
        "🗺️ エリア別分析の使い方": {
            "title": "6つのエリアで沖縄全体を俯瞰",
            "content": """
            ### 🗺️ エリア別分析タブの使い方
            
            #### 🎯 このタブの特徴
            沖縄県を**6つのエリア**に分けて、地域特性を分析。市町村単位では見えない**広域的なトレンド**と**地域間の特性差**を把握できます。
            
            #### 🗾 6つのエリア詳細構成
            
            **🏙️ 南部エリア（7市町村）**
            那覇市、糸満市、豊見城市、八重瀬町、南城市、与那原町、南風原町
            - **特徴**: 県庁所在地・政治経済の中心地域
            - **宿泊特性**: ビジネスホテル、シティホテルが中心
            - **主要機能**: 行政、商業、金融、交通ハブ
            - **観光特性**: 都市型観光、歴史・文化観光、空港アクセス
            - **発展傾向**: 安定成長、再開発による新規参入
            
            **🏢 中部エリア（10市町村）**
            沖縄市、宜野湾市、浦添市、うるま市、読谷村、嘉手納町、北谷町、北中城村、中城村、西原町
            - **特徴**: 米軍基地・商業施設が集中する複合地域
            - **宿泊特性**: ビジネスホテル、中規模ホテルが多様
            - **主要機能**: 米軍関連、商業、住宅、工業
            - **観光特性**: 都市型観光、アメリカ文化体験、ショッピング
            - **発展傾向**: 変動的、基地返還による開発機会
            
            **🌿 北部エリア（9市町村）**
            名護市、国頭村、大宜味村、東村、今帰仁村、本部町、恩納村、宜野座村、金武町
            - **特徴**: 自然豊かな観光地域、やんばるの森
            - **宿泊特性**: リゾートホテル、大規模施設が中心
            - **主要機能**: 観光、自然保護、農業、林業
            - **観光特性**: 自然観光、エコツーリズム、リゾート滞在
            - **発展傾向**: 観光ブームに連動、環境配慮型開発
            
            **🏝️ 宮古エリア（2市町村）**
            宮古島市、多良間村
            - **特徴**: 美しい海と独特の文化を持つ離島
            - **宿泊特性**: リゾートホテル、中規模ホテルが中心
            - **主要機能**: 観光、農業（サトウキビ）、漁業
            - **観光特性**: 海洋リゾート、マリンスポーツ、離島文化
            - **発展傾向**: 急速な観光開発、インフラ整備進展
            
            **🌺 八重山エリア（3市町村）**
            石垣市、竹富町、与那国町
            - **特徴**: 最南端の離島リゾート、国際的観光地
            - **宿泊特性**: 高級リゾートホテル、多様な規模
            - **主要機能**: 観光、国際交流、農業、漁業
            - **観光特性**: 高級リゾート、国際観光、自然・文化体験
            - **発展傾向**: 国際化進展、高級化・差別化の方向
            
            **⛵ 離島エリア（10市町村）**
            久米島町、渡嘉敷村、座間味村、粟国村、渡名喜村、南大東村、北大東村、伊江村、伊平屋村、伊是名村
            - **特徴**: 多様な小規模離島群、それぞれ独特の特色
            - **宿泊特性**: 小規模施設、民宿、ペンション中心
            - **主要機能**: 観光、農業、漁業、伝統文化保存
            - **観光特性**: 個性的な離島体験、静寂・癒し系観光
            - **発展傾向**: 持続可能な観光、地域資源活用型
            
            #### 📊 2つの分析タイプ詳細
            
            **1. 全宿泊施設分析** 🏨
            - **対象**: ホテル・旅館・民宿・ペンション・ゲストハウス等すべて
            - **特徴**: 地域の宿泊市場全体を包括的に把握
            - **活用場面**: 
              - 総合的な観光政策立案
              - 地域経済への宿泊業の貢献度測定
              - 全体的な需給バランス分析
            
            **表示モード**:
            - **概要表示**: エリア別Total推移の基本分析
            - **宿泊形態別詳細**: ホテル・民宿・ペンション等の内訳分析
            
            **2. ホテル・旅館特化分析** 🏖️
            - **対象**: ホテル・旅館のみ（より専門的な宿泊施設）
            - **特徴**: 商業的な宿泊市場の動向を精密分析
            - **活用場面**:
              - 投資・開発計画の策定
              - 競合他社の戦略分析
              - 高級宿泊市場の動向把握
            
            **表示モード**:
            - **概要表示**: エリア別ホテル・旅館推移
            - **規模別/種別詳細**: 大中小規模or機能別の詳細分析
            
            #### 🛠️ 操作方法とコツ
            
            **1. エリア選択の戦略**
            - **全エリア選択**: 沖縄県全体の地域バランス把握
            - **類似エリア比較**: 宮古vs八重山（離島リゾート比較）
            - **対比エリア比較**: 南部vs北部（都市型vs自然型比較）
            - **連続エリア比較**: 南部+中部（都市圏分析）
            
            **2. 指標選択の考え方**
            - **軒数**: 施設の集積度、競合密度
            - **客室数**: 市場規模、受入キャパシティ
            - **収容人数**: 実際の宿泊可能人数、需給バランス
            
            **3. 期間設定の戦略**
            - **短期（1-3年）**: 最近のトレンド、政策効果の把握
            - **中期（5-7年）**: 景気サイクル、開発サイクルの把握
            - **長期（10年以上）**: 構造的変化、長期トレンドの把握
            
            #### 📈 エリア比較分析の高度なテクニック
            
            **🔍 地域特性の把握パターン**
            
            **成長パターン分析**:
            - **安定成長型**: 南部（継続的な都市型成長）
            - **急成長型**: 宮古・八重山（観光ブーム型）
            - **回復成長型**: 北部（リゾート開発復活）
            - **変動型**: 中部（基地問題等の影響）
            - **微成長型**: 離島（小規模・持続型）
            
            **季節性・外的要因分析**:
            - **観光季節性**: 夏季集中vs通年型の地域差
            - **経済変動**: リーマンショック、コロナ禍の影響度差
            - **政策効果**: 各種振興策の地域別効果測定
            - **インフラ効果**: 空港・道路整備の影響度
            
            #### 🎯 活用シーン別ガイド
            
            **🏛️ 行政・政策立案での活用**
            
            **広域観光計画の策定**:
            1. **エリア間の役割分担**: 都市型・自然型・リゾート型の配置最適化
            2. **インフラ整備の優先順位**: 成長エリアへの重点投資
            3. **広域連携の可能性**: 隣接エリアとの連携効果
            4. **格差是正策**: 成長格差の要因分析と対策立案
            
            **予算配分・事業評価**:
            - エリア別の投資効果測定
            - 過去の政策効果の定量評価
            - 将来投資の優先順位設定
            
            **🏢 民間事業者での活用**
            
            **立地選定・市場参入**:
            1. **成長エリアの特定**: 今後有望な投資エリア
            2. **競合状況の把握**: エリア別の競合密度
            3. **市場規模の測定**: エリア別の市場ポテンシャル
            4. **差別化戦略**: エリア特性に応じたコンセプト決定
            
            **事業拡大・多店舗展開**:
            - 既存店舗のエリア内ポジション把握
            - 新規出店候補エリアの選定
            - エリア別の事業戦略の差別化
            
            **📊 学術研究・メディアでの活用**
            
            **地域経済研究**:
            1. **観光産業の地域経済効果**: エリア別の経済貢献度
            2. **地域格差の要因分析**: 成長格差の構造的要因
            3. **政策効果の実証分析**: 各種政策の定量的効果測定
            4. **将来予測モデル**: エリア別の成長予測
            
            **報道・記事作成**:
            - 沖縄観光の地域別トレンド
            - 離島振興の効果検証
            - 基地返還による経済効果
            - 観光公害・オーバーツーリズム問題
            
            #### 💡 エリア分析の上級テクニック
            
            **複合指標による総合分析**:
            1. **成長力指数**: (軒数成長率+客室数成長率+収容人数成長率)÷3
            2. **集積度指数**: エリア内市町村の標準偏差（バラツキ）
            3. **効率性指数**: 軒数あたり客室数、客室あたり収容人数
            4. **特化係数**: 全県比でのエリア特化度
            
            **時系列クラスター分析**:
            - 似た成長パターンのエリアをグループ化
            - 成功エリアの要因を他エリアに適用
            - 異常値（急変動）の要因分析
            
            **相関分析**:
            - エリア間の相関関係（競合・補完）
            - 外部要因（観光客数、経済指標）との相関
            - 先行指標・遅行指標の特定
            """
        },
        
        "📊 データ出典・注意事項": {
            "title": "データの詳細情報と利用上の注意",
            "content": """
            ### 📊 データ出典・注意事項
            
            #### 📋 データソース詳細
            
            **正式名称**: 沖縄県宿泊施設実態調査
            **実施機関**: 沖縄県文化観光スポーツ部観光政策課
            **調査目的**: 県内宿泊施設の実態把握、観光政策立案の基礎資料作成
            **法的根拠**: 統計法に基づく一般統計調査
            **公開URL**: [沖縄県宿泊施設実態調査](https://www.pref.okinawa.jp/shigoto/kankotokusan/1011671/1011816/1003416/1026290.html)
            
            #### 📅 調査実施体制・スケジュール
            
            **調査頻度**: 年1回（毎年実施）
            **調査基準日**: 各年12月31日現在
            **調査方法**: 郵送調査、一部聞き取り調査
            **調査対象**: 県内全宿泊施設（許可・届出施設）
            **公表時期**: 翌年6月頃（例：2024年調査→2025年6月公表）
            **調査歴史**: 昭和47年（1972年）開始、52年間継続
            
            #### 🏨 調査対象施設の詳細定義
            
            **含まれる施設**:
            - **ホテル**: 旅館業法のホテル営業許可施設
            - **旅館**: 旅館業法の旅館営業許可施設  
            - **民宿**: 旅館業法の簡易宿所営業許可施設（民宿形態）
            - **ペンション**: 旅館業法の簡易宿所営業許可施設（ペンション形態）
            - **貸別荘**: 旅館業法の簡易宿所営業許可施設（貸別荘形態）
            - **ゲストハウス・ドミトリー**: 旅館業法の簡易宿所営業許可施設
            - **ウィークリーマンション**: 宿泊営業を行う施設
            - **団体経営施設**: 企業・団体が運営する宿泊施設
            - **ユースホステル**: 青少年向け宿泊施設
            
            **除外される施設**:
            - **モーテル**: 旅館業法対象外
            - **ラブホテル**: 調査対象外
            - **民泊**: 住宅宿泊事業法施設（2018年法制化以降、一部含む年あり）
            - **無許可営業施設**: 法的許可のない施設
            - **社員寮・学生寮**: 一般宿泊営業を行わない施設
            - **病院・福祉施設**: 宿泊目的が治療・福祉の施設
            
            #### 📐 調査項目・指標の定義
            
            **基本指標**:
            - **軒数**: 営業許可を受けた施設の数（単位：軒）
            - **客室数**: 宿泊可能な部屋の総数（単位：室）
            - **収容人数**: 最大宿泊可能人数（単位：人）
            
            **分類基準**:
            - **宿泊形態**: 施設の営業形態・サービス内容による分類
            - **規模分類**: 収容人数による3段階分類（大規模300人以上、中規模100-299人、小規模99人以下）
            - **地域分類**: 市町村単位、6エリア単位での集計
            
            #### ⚠️ データ利用上の重要な注意事項
            
            **🔄 調査方法の変更履歴**
            
            **昭和47年〜平成25年（1972-2013年）**:
            - 基本的な宿泊形態分類のみ
            - 詳細なホテル種別分類なし
            - 規模分類は簡易版
            
            **平成26年〜現在（2014年〜）**:
            - ホテル詳細分類開始（リゾート・ビジネス・シティ・旅館）
            - 規模分類の精緻化
            - 調査項目の拡充
            
            **令和2年〜（2020年〜）**:
            - コロナ禍対応での調査方法一部変更
            - 休業・廃業施設の扱い明確化
            
            **📊 データの制約・限界**
            
            **調査回答率**:
            - 回答率: 概ね85-95%（年により変動）
            - 未回答施設: 推計値で補完（一部）
            - 新規開業: 調査時期により漏れの可能性
            
            **施設分類の課題**:
            - **複合施設**: ホテル+コンドミニアム等の分類困難
            - **形態変更**: 営業中の業態変更の反映タイムラグ
            - **季節営業**: 通年営業・季節営業の区別
            
            **数値の変動要因**:
            - **開業・廃業**: 年度中の開廃業は次年度反映
            - **改修・増築**: 客室数・収容人数の変更
            - **災害影響**: 台風・地震等による一時的影響
            - **経済変動**: 景気変動による休廃業
            
            #### 🎯 適切なデータ解釈のガイドライン
            
            **時系列分析での注意点**:
            1. **長期トレンド重視**: 単年度変動より3-5年移動平均で判断
            2. **外的要因考慮**: リーマンショック、震災、コロナ等の影響を考慮
            3. **政策効果評価**: 政策実施時期と効果発現時期のタイムラグ
            4. **季節性考慮**: 年末基準日のため季節要因に注意
            
            **比較分析での注意点**:
            1. **規模考慮**: 市町村間の人口・面積・経済規模の違い
            2. **立地条件**: 地理的条件、交通アクセスの違い
            3. **観光資源**: 自然・文化資源の有無・質の違い
            4. **政策環境**: 自治体の観光政策・規制の違い
            
            **数値の精度について**:
            - **軒数**: 最も正確（許可制のため）
            - **客室数**: 比較的正確（物理的カウント）
            - **収容人数**: やや推計性あり（定員設定の解釈差）
            
            #### 📈 補完データ・関連統計
            
            **併用推奨データ**:
            - **沖縄県入域観光客統計**: 宿泊需要の把握
            - **国勢調査**: 人口基盤との関係
            - **経済センサス**: 宿泊業の経済規模
            - **建築確認統計**: 新規開発動向
            
            **全国比較データ**:
            - **観光庁宿泊旅行統計**: 全国・都道府県別データ
            - **厚生労働省衛生行政報告**: 許可施設数
            
            #### 🔍 データ品質向上への取り組み
            
            **県の改善努力**:
            - 調査項目の継続的見直し
            - 調査方法の改善・効率化
            - 未回答施設への追跡調査強化
            - デジタル化による精度向上
            
            **利用者側の配慮**:
            - データの特性・限界の理解
            - 複数年データでの検証
            - 他統計との整合性確認
            - 結論の慎重な導出
            
            #### 📞 データに関する問い合わせ
            
            **調査内容・方法について**:
            沖縄県文化観光スポーツ部観光政策課
            - 統計調査の詳細
            - 過去データの入手方法
            - 調査項目の定義確認
            
            **このアプリについて**:
            - データ集計・加工方法
            - 表示内容の解釈
            - 機能追加・改善要望
            
            #### 📚 引用・出典表記
            
            **学術論文での引用例**:
            ```
            沖縄県文化観光スポーツ部観光政策課「沖縄県宿泊施設実態調査」
            各年版，https://www.pref.okinawa.jp/
            ```
            
            **報告書での出典例**:
            ```
            出典：沖縄県「宿泊施設実態調査」（令和6年）を基に作成
            ```
            
            **このアプリ利用時の注記例**:
            ```
            データ：沖縄県「宿泊施設実態調査」
            分析：沖縄県宿泊施設データ可視化アプリ
            ```
            """
        },
        
        "💡 効果的な活用方法": {
            "title": "このアプリを最大限活用するコツ",
            "content": """
            ### 💡 効果的な活用方法
            
            #### 🎯 目的別・立場別の使い分けガイド
            
            **🏛️ 行政職員の方向け**
            
            **政策立案・計画策定**:
            1. **🗺️ エリア別分析** → 広域的な地域バランス把握
            2. **🤖 ランキング分析** → 成長地域・課題地域の特定
            3. **🏘️ 市町村別分析** → 個別自治体の詳細状況確認
            4. **複数年データ比較** → 政策効果の定量評価
            
            **予算編成・事業評価**:
            - 過去の投資効果を数値で検証
            - 今後の重点投資エリア選定
            - 類似自治体との比較による妥当性判断
            - 議会説明用の客観的データ作成
            
            **🏢 観光事業者の方向け**
            
            **市場参入・立地選定**:
            1. **🤖 ランキング分析（増減率）** → 成長市場の発見
            2. **🏨 規模別分析** → 適正な施設規模の判断
            3. **🏛️ ホテル種別分析** → 最適なコンセプト決定
            4. **🗺️ エリア別分析** → 競合状況の把握
            
            **競合分析・戦略立案**:
            - 既存競合の規模・成長率分析
            - 市場空白・ニッチの発見
            - 差別化ポイントの特定
            - 投資タイミングの判断
            
            **📚 研究者・学生の方向け**
            
            **学術研究・論文作成**:
            1. **長期データ活用** → 52年間の超長期分析
            2. **複数指標分析** → 多角的な検証
            3. **地域比較分析** → 地域間格差の要因分析
            4. **外部データ連携** → 他統計との相関分析
            
            **卒業論文・レポート**:
            - 沖縄観光業の発展史
            - 地域格差・離島振興の効果
            - 観光政策の定量評価
            - 持続可能観光の実現可能性
            
            **📰 メディア関係者の方向け**
            
            **記事・番組制作**:
            1. **最新トレンド** → 直近データでの現状把握
            2. **ランキング情報** → インパクトあるデータ抽出
            3. **地域比較** → 地域間の違いを明確化
            4. **歴史的変化** → 長期データでの変遷紹介
            
            **データジャーナリズム**:
            - 客観的データに基づく報道
            - 政策効果の検証記事
            - 地域経済の実態分析
            - 将来予測・課題提起
            
            #### 🔍 分析の進め方（推奨フロー）
            
            **👀 Step 1: 全体把握（15分）**
            1. **県全体グラフ確認** → 沖縄県全体のトレンド把握
            2. **🗺️ エリア別分析** → 6エリアの概要比較
            3. **最新年データ確認** → 現在の市場状況把握
            
            **🔎 Step 2: 関心領域の深掘り（30分）**
            1. **🤖 ランキング分析** → 注目市町村・エリアの特定
            2. **🏘️ 市町村別分析** → 詳細トレンド確認
            3. **期間調整** → 短期・中期・長期の変化確認
            
            **🎯 Step 3: 専門分析（60分）**
            1. **🏨 規模別分析** → 市場構造の理解
            2. **🏛️ ホテル種別分析** → 競合状況の詳細把握
            3. **複数タブ組み合わせ** → 多角的検証
            
            **📊 Step 4: 結論・活用（30分）**
            1. **データまとめ** → 重要な発見事項の整理
            2. **他データとの照合** → 外部情報での検証
            3. **アクションプラン** → 具体的活用方法の決定
            
            #### 🛠️ 高度な分析テクニック
            
            **📈 複数タブの組み合わせパターン**
            
            **パターン1: 投資検討フロー**
            1. **🗺️ エリア別** → 成長エリアを特定
            2. **🤖 ランキング** → そのエリア内の有望市町村を発見
            3. **🏨 規模別** → 適切な施設規模を判断
            4. **🏛️ ホテル種別** → 最適なホテルタイプを決定
            
            **パターン2: 競合調査フロー**
            1. **🏘️ 市町村別** → 競合の多い市町村を特定
            2. **🏛️ ホテル種別** → 競合のホテルタイプを分析
            3. **🤖 ランキング** → 競合の成長率を確認
            4. **差別化戦略** → 空白ポジションを発見
            
            **パターン3: 政策効果検証フロー**
            1. **🤖 ランキング** → 全体市場の動向把握
            2. **🗺️ エリア別** → 地域差・政策対象地域の効果確認
            3. **🏘️ 市町村別** → 個別自治体の政策前後比較
            4. **期間設定調整** → 政策実施時期との照合
            
            **パターン4: 市場トレンド分析フロー**
            1. **🤖 ランキング** → 最新の成長ランキング確認
            2. **🏨 規模別** → 成長している規模帯の特定
            3. **🏛️ ホテル種別** → 成長しているホテル種別の特定
            4. **🗺️ エリア別** → 成長の地域的分布確認
            
            #### 📊 データ活用の実践テクニック
            
            **🔢 数値の効果的な読み取り方**
            
            **成長率の判断基準**:
            - **高成長**: 年率10%以上の継続的増加
            - **安定成長**: 年率3-10%の継続的増加
            - **微成長**: 年率0-3%の増加
            - **停滞**: ±3%以内の変動
            - **減少**: 継続的な負の成長
            
            **規模感の把握**:
            - **大規模市場**: 軒数100軒以上、客室数3,000室以上
            - **中規模市場**: 軒数30-100軒、客室数1,000-3,000室
            - **小規模市場**: 軒数30軒未満、客室数1,000室未満
            
            **季節性・変動の考慮**:
            - **観光地**: 夏季ピーク、冬季オフの考慮
            - **ビジネス地**: 平日集中、週末減少の考慮
            - **離島**: 天候・交通の影響大
            
            **📈 グラフ・チャートの読み方のコツ**
            
            **ライングラフ（時系列）**:
            - **傾き**: 急 = 大きな変化、緩 = 安定的変化
            - **振幅**: 大 = 変動性高、小 = 安定性高
            - **転換点**: トレンド変化のタイミング特定
            - **季節性**: 一定周期での上下変動
            
            **ランキング（棒グラフ）**:
            - **1位との差**: 市場集中度の把握
            - **上位集中度**: トップ5の合計シェア
            - **下位との差**: 市場格差の程度
            - **順位変動**: 成長力の相対比較
            
            **データテーブル**:
            - **行間比較**: 地域間・時期間の比較
            - **列間比較**: 指標間の関係性
            - **異常値**: 突出した数値の要因分析
            - **欠損値**: データなし部分の解釈
            
            #### 🎯 目的達成のための戦略的活用
            
            **💼 ビジネス判断での活用戦略**
            
            **市場参入判断**:
            1. **市場規模**: 十分な需要があるか
            2. **成長性**: 今後も成長が期待できるか
            3. **競合状況**: 過度な競争状態でないか
            4. **参入タイミング**: 成長初期段階か成熟期か
            
            **投資規模決定**:
            1. **地域特性**: そのエリアに適した規模は何か
            2. **競合規模**: 既存競合との差別化可能規模
            3. **市場キャパ**: 市場が吸収可能な追加供給量
            4. **投資回収**: 期待収益率に見合う投資規模
            
            **差別化戦略**:
            1. **空白ポジション**: 競合の少ない分野
            2. **成長分野**: 拡大している市場セグメント
            3. **地域ニーズ**: その地域特有の需要
            4. **時代トレンド**: 社会変化に対応した戦略
            
            **📋 政策立案での活用戦略**
            
            **課題地域の特定**:
            1. **成長格差**: 他地域と比べて停滞している地域
            2. **構造的問題**: 長期的に解決すべき課題
            3. **緊急性**: 早急な対応が必要な課題
            4. **波及効果**: 解決により他地域への好影響
            
            **政策効果の測定**:
            1. **ベースライン**: 政策実施前の状況
            2. **目標設定**: 達成すべき具体的数値
            3. **モニタリング**: 定期的な進捗確認
            4. **事後評価**: 政策終了後の効果測定
            
            **予算配分の最適化**:
            1. **効果的地域**: 投資効果の高い地域への重点配分
            2. **公平性**: 地域間格差の是正
            3. **緊急性**: 緊急課題への優先対応
            4. **継続性**: 長期的視点での投資計画
            
            #### 🚀 上級者向け高度活用法
            
            **📊 複合指標の作成**
            
            **成長力指数の算出**:
            ```
            成長力指数 = (軒数成長率 × 0.3) + (客室数成長率 × 0.4) + (収容人数成長率 × 0.3)
            ```
            
            **競合密度指数の算出**:
            ```
            競合密度 = 軒数 ÷ 人口(万人) × 観光客数補正係数
            ```
            
            **効率性指数の算出**:
            ```
            効率性 = 収容人数 ÷ 軒数 （1軒あたり平均収容人数）
            ```
            
            **📈 予測モデルの構築**
            
            **トレンド分析による予測**:
            1. **線形トレンド**: 安定成長地域の将来予測
            2. **指数トレンド**: 急成長地域の将来予測
            3. **周期性考慮**: 景気サイクルを考慮した予測
            4. **外的要因調整**: 政策・開発計画等の影響考慮
            
            **比較分析による予測**:
            1. **先行地域**: 先行事例からの類推
            2. **類似地域**: 似た条件の地域からの予測
            3. **全国平均**: 全国トレンドとの比較
            4. **国際比較**: 海外類似地域との比較
            
            #### 💡 効率的な操作・時短テクニック
            
            **⚡ ショートカット活用法**
            
            **設定の効率化**:
            - **ブックマーク機能**: よく使う設定の保存
            - **デフォルト設定**: 最もよく使う条件を初期値に
            - **一括選択**: 「全選択」「全解除」ボタンの活用
            - **期間テンプレート**: 「過去3年」「過去5年」等のプリセット活用
            
            **データ取得の効率化**:
            - **複数指標同時**: 一度の実行で複数指標を取得
            - **プレビュー活用**: 実行前に質問内容を確認
            - **表示順序**: 重要度の高い地域から選択
            
            **分析結果の活用**:
            - **グラフ保存**: スクリーンショットでの保存
            - **データコピー**: テーブルデータのコピー&ペースト
            - **URL共有**: 分析結果の他者共有
            
            #### 🔧 トラブルシューティング・よくある質問
            
            **❓ データが表示されない場合**
            
            **チェックポイント**:
            1. **選択確認**: 市町村・エリアが選択されているか
            2. **指標確認**: 分析したい指標が選択されているか
            3. **期間確認**: データが存在する期間が設定されているか
            4. **ブラウザ**: 最新版ブラウザの使用、キャッシュクリア
            
            **解決方法**:
            - ページの再読み込み（F5キー）
            - 異なる市町村・期間での試行
            - ブラウザの変更（Chrome、Firefox等）
            - デバイスの変更（PC、タブレット等）
            
            **❓ データの解釈に迷う場合**
            
            **基本的な考え方**:
            1. **複数年での確認**: 単年度ではなく複数年で判断
            2. **他地域との比較**: 絶対値ではなく相対的な位置
            3. **外的要因の考慮**: 災害・政策等の特殊事情
            4. **専門家相談**: 不明な点は関係機関に問い合わせ
            
            **参考情報源**:
            - 沖縄県観光政策課の調査報告書
            - 観光庁の全国統計との比較
            - 学術論文・研究報告書
            - 業界団体の市場レポート
            
            #### 📚 継続的な学習・スキルアップ
            
            **📖 推奨学習リソース**
            
            **データ分析スキル向上**:
            - 統計学の基礎知識
            - データ可視化の技術
            - 時系列分析の手法
            - 比較分析の方法論
            
            **観光業界知識**:
            - 観光政策の動向
            - 宿泊業界のトレンド
            - マーケティング理論
            - 地域経済学
            
            **沖縄観光の特殊性**:
            - 沖縄観光の歴史
            - 離島観光の特性
            - 基地問題と観光
            - 持続可能観光
            
            **🎓 実践的なスキルアップ方法**
            
            **定期的な分析習慣**:
            - 月1回の定期分析
            - 四半期での成果確認
            - 年次でのトレンド総括
            - 他地域との比較分析
            
            **ネットワーキング**:
            - 同業者との情報交換
            - 専門家との意見交換
            - 学会・研究会への参加
            - オンラインコミュニティ参加
            
            **アウトプット習慣**:
            - 分析結果のレポート作成
            - プレゼンテーション実施
            - ブログ・SNSでの発信
            - 学会・研究会での発表
            
            #### 🌟 このアプリを使った成功事例
            
            **🏛️ 行政での活用成功例**
            - 観光振興計画の策定時の基礎データ活用
            - 予算要求時の根拠データとして活用
            - 議会答弁での客観的データ提供
            - 他自治体との比較による政策改善
            
            **🏢 民間での活用成功例**
            - 新規出店地域の選定に活用
            - 投資家への説明資料として活用
            - 競合分析による戦略立案
            - マーケティング戦略の根拠データ
            
            **📚 研究・教育での活用成功例**
            - 卒業論文・修士論文のデータ分析
            - 学術論文の実証分析部分
            - 授業での実データ活用事例
            - 政策提言の根拠データ
            
            **📰 メディアでの活用成功例**
            - 観光動向の特集記事作成
            - 地域経済の現状分析記事
            - 政策効果の検証報道
            - 将来予測・課題提起記事
            
            #### 🔮 将来の機能拡張予定
            
            **予定されている機能追加**:
            - リアルタイムデータ更新
            - より詳細な地図表示機能
            - 外部データとの連携分析
            - AI による自動分析・予測機能
            - カスタムレポート自動生成
            - データエクスポート機能の拡充
            
            **ユーザーフィードバック反映**:
            - 操作性の継続的改善
            - 新しい分析手法の追加
            - 表示オプションの拡充
            - パフォーマンスの向上
            
            このアプリを通じて、データドリブンな意思決定を支援し、沖縄県の観光業発展に貢献することを目指しています。ぜひ積極的にご活用ください！
            """
        }
    }
    
    # セクション選択
    selected_section = st.selectbox(
        "📖 表示したいヘルプ項目を選択してください",
        list(help_sections.keys()),
        key="help_section_selector"
    )
    
    # 選択されたセクションを表示
    if selected_section in help_sections:
        section = help_sections[selected_section]
        st.markdown(f"## {section['title']}")
        st.markdown(section['content'])
        
        # セクション別の追加アクション
        if selected_section == "🎯 アプリ概要":
            st.markdown("---")
            st.markdown("### 🚀 今すぐ始めてみましょう！")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🤖 ランキング分析を試す", key="goto_ranking", help="自然言語形式でデータを質問"):
                    st.info("👆 上部の「🤖 ランキング分析」タブをクリックしてください")
            with col2:
                if st.button("🏘️ 市町村別分析を試す", key="goto_municipal", help="特定の市町村を詳細分析"):
                    st.info("👆 上部の「🏘️ 市町村別分析」タブをクリックしてください")
            with col3:
                if st.button("🗺️ エリア別分析を試す", key="goto_area", help="6つのエリアで広域分析"):
                    st.info("👆 上部の「🗺️ エリア別分析」タブをクリックしてください")
        
        elif selected_section == "💡 効果的な活用方法":
            st.markdown("---")
            st.markdown("### 📊 クイックスタートガイド")
            with st.expander("🔰 初心者向け：5分で基本をマスター", expanded=True):
                st.markdown("""
                #### 📋 まず最初にやってみよう
                
                **Step 1**: 🤖 ランキング分析タブ → 「基本情報取得」
                - 指標: 全選択（軒数・客室数・収容人数）
                - 場所: 「那覇市」を選択
                - 年度: 2024年
                - → 実行ボタンをクリック
                
                **Step 2**: 🤖 ランキング分析タブ → 「ランキング表示」  
                - 指標: 客室数
                - 表示件数: 10件
                - 年度: 2024年
                - → 実行ボタンをクリック
                
                **Step 3**: 🗺️ エリア別分析タブ
                - エリア: 全選択
                - 指標: 軒数
                - 期間: 2020-2024
                - → グラフを確認
                
                この3つで沖縄県の宿泊施設の基本が分かります！
                """)
            
            with st.expander("⚡ 時短テクニック集", expanded=False):
                st.markdown("""
                #### ⚡ 効率的な操作方法
                
                **設定の時短**:
                - 「全選択」「全解除」ボタンを活用
                - よく使う期間（過去3年、過去5年）をプリセット活用
                - 複数指標を一度に選択
                
                **データ取得の時短**:
                - プレビュー機能で事前確認
                - 複数タブを同時に開いて比較分析
                - データテーブルを直接コピー
                
                **分析の時短**:
                - 目的に応じたタブの使い分け
                - 大→小の順番で絞り込み分析
                - 異常値は他タブで詳細確認
                """)
    
    # 共通のフッター情報
    st.markdown("---")
    st.markdown("### 📞 サポート・フィードバック")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **🐛 バグ報告・機能要望**
        
        より良いアプリにするため、皆様のご意見をお聞かせください：
        
        - 操作で困った点
        - 追加してほしい分析機能
        - データの見方が分からない部分
        - 表示速度・パフォーマンスの問題
        """)
    
    with col2:
        st.success("""
        **💡 活用事例・成功事例**
        
        このアプリの活用事例をぜひ教えてください：
        
        - 政策立案・予算編成での活用
        - ビジネス判断・投資決定での利用
        - 研究・論文・レポートでの使用
        - 記事・番組制作での活用
        """)
    
    # アプリ情報
    st.markdown("---")
    st.markdown("### 📊 このアプリについて")
    st.markdown("""
    **沖縄県宿泊施設データ可視化アプリ** は、沖縄県の宿泊施設実態調査データを
    誰でも簡単に分析できるよう開発されたWebアプリケーションです。
    
    **開発目的**: オープンデータの活用促進、データドリブンな意思決定支援、沖縄観光業界の発展寄与
    
    **対象利用者**: 行政職員、観光事業者、研究者、学生、メディア関係者、一般県民
    
    **データ期間**: 昭和47年（1972年）〜令和6年（2024年）の52年間
    """)

def handle_change_analysis(df, metric_en, metric_jp, location_type, locations, params):
    """増減・伸び率分析の処理"""
    analysis_type = params['analysis_type']
    result_type = params['result_type']
    show_ranking = params.get('show_ranking', True)
    ranking_count = params.get('ranking_count', 5)
    
    if analysis_type == "対前年比較":
        target_year = params['target_year']
        return handle_year_over_year_analysis(df, metric_en, metric_jp, location_type, locations, 
                                            target_year, result_type, show_ranking, ranking_count)
    else:
        start_year = params['start_year']
        end_year = params['end_year']
        return handle_period_change_analysis(df, metric_en, metric_jp, location_type, locations,
                                           start_year, end_year, result_type, show_ranking, ranking_count)

def handle_year_over_year_analysis(df, metric_en, metric_jp, location_type, locations, target_year, result_type, show_ranking, ranking_count):
    """
    対前年比較分析（全体順位の母数を41市町村に限定して修正）
    """
    # 1. 全41市町村のリストを定義
    all_municipalities_list = list(CITY_CODE.keys())
    
    # 2. 全41市町村のデータを取得
    current_data_all = df.query(f"metric == @metric_en & cat1 == 'total' & year == @target_year & city in @all_municipalities_list").set_index('city')['value']
    previous_data_all = df.query(f"metric == @metric_en & cat1 == 'total' & year == {target_year - 1} & city in @all_municipalities_list").set_index('city')['value']

    # 3. 全41市町村での増減数・増減率を計算
    common_cities_all = current_data_all.index.intersection(previous_data_all.index)
    increases_all = current_data_all.reindex(common_cities_all) - previous_data_all.reindex(common_cities_all)
    rates_all = (increases_all / previous_data_all.reindex(common_cities_all).replace(0, pd.NA) * 100).fillna(0)

    # 4. 全41市町村での順位を計算
    increase_ranks = increases_all.rank(method='min', ascending=False).astype(int)
    rate_ranks = rates_all.rank(method='min', ascending=False).astype(int)
    total_municipalities_in_rank = len(increases_all)

    # 5. 表示対象の市町村リストを決定
    if location_type == "市町村":
        cities_to_display = locations
        scope_text = "選択市町村"
    elif location_type == "エリア":
        cities_to_display = [city for area in locations for city in REGION_MAP.get(area, [])]
        scope_text = f"{'・'.join(locations)}エリア"
    else: # 全体
        cities_to_display = increases_all.sort_values(ascending=False).head(ranking_count).index.tolist() if show_ranking else common_cities_all.tolist()
        scope_text = "全市町村"

    # 6. 結果を生成
    result = f"## {target_year}年 対前年{metric_jp}分析（{scope_text}）\n\n"
    
    if show_ranking and location_type == "全体":
        result += f"### 📈 対前年増減数 上位{len(cities_to_display)}市町村\n"
        
    for city in sorted(cities_to_display, key=lambda c: increases_all.get(c, -float('inf')), reverse=True):
        if city in common_cities_all:
            increase = increases_all.get(city, 0)
            rate = rates_all.get(city, 0)
            current_val = current_data_all.get(city, 0)
            previous_val = previous_data_all.get(city, 0)
            inc_rank = increase_ranks.get(city, '-')
            rate_rank = rate_ranks.get(city, '-')

            result += f"**{city}**\n"
            result += f"- **対前年増減数**: {increase:+,}{get_unit(metric_jp)} （全体 {inc_rank}位 / {total_municipalities_in_rank}市町村）\n"
            result += f"- **対前年増減率**: {rate:+.1f}% （全体 {rate_rank}位 / {total_municipalities_in_rank}市町村）\n"
            result += f"- {target_year}年: {current_val:,}{get_unit(metric_jp)}\n"
            result += f"- {target_year-1}年: {previous_val:,}{get_unit(metric_jp)}\n\n"
        elif city in locations:
             result += f"**{city}**: {target_year}年または{target_year-1}年のデータがなく、計算できませんでした。\n\n"

    return result

def handle_period_change_analysis(df, metric_en, metric_jp, location_type, locations, start_year, end_year, result_type, show_ranking, ranking_count):
    """
    期間比較分析（全体順位の母数を41市町村に限定して修正）
    """
    # 1. 全41市町村のリストを定義
    all_municipalities_list = list(CITY_CODE.keys())

    # 2. 全41市町村のデータを取得
    start_data_all = df.query(f"metric == @metric_en & cat1 == 'total' & year == @start_year & city in @all_municipalities_list").set_index('city')['value']
    end_data_all = df.query(f"metric == @metric_en & cat1 == 'total' & year == @end_year & city in @all_municipalities_list").set_index('city')['value']

    # 3. 全41市町村での増減数・増減率を計算
    common_cities_all = start_data_all.index.intersection(end_data_all.index)
    increases_all = end_data_all.reindex(common_cities_all) - start_data_all.reindex(common_cities_all)
    rates_all = (increases_all / start_data_all.reindex(common_cities_all).replace(0, pd.NA) * 100).fillna(0)

    # 4. 全41市町村での順位を計算
    increase_ranks = increases_all.rank(method='min', ascending=False).astype(int)
    rate_ranks = rates_all.rank(method='min', ascending=False).astype(int)
    total_municipalities_in_rank = len(increases_all) # データが存在する市町村の総数

    # 5. 表示対象の市町村リストを決定
    if location_type == "市町村":
        cities_to_display = locations
        scope_text = "選択市町村"
    elif location_type == "エリア":
        cities_to_display = [city for area in locations for city in REGION_MAP.get(area, [])]
        scope_text = f"{'・'.join(locations)}エリア"
    else: # 全体
        cities_to_display = increases_all.sort_values(ascending=False).head(ranking_count).index.tolist() if show_ranking else common_cities_all.tolist()
        scope_text = "全市町村"

    # 6. 結果を生成
    period_text = f"{start_year}年〜{end_year}年"
    result = f"## {period_text} {metric_jp}変化分析（{scope_text}）\n\n"
    
    if show_ranking and location_type == "全体":
        result += f"### 📈 期間増減数 上位{len(cities_to_display)}市町村\n"

    for city in sorted(cities_to_display, key=lambda c: increases_all.get(c, -float('inf')), reverse=True):
        if city in common_cities_all:
            increase = increases_all.get(city, 0)
            rate = rates_all.get(city, 0)
            start_val = start_data_all.get(city, 0)
            end_val = end_data_all.get(city, 0)
            inc_rank = increase_ranks.get(city, '-')
            rate_rank = rate_ranks.get(city, '-')
            
            result += f"**{city}**\n"
            result += f"- **期間増減数**: {increase:+,}{get_unit(metric_jp)} （全体 {inc_rank}位 / {total_municipalities_in_rank}市町村）\n"
            result += f"- **期間増減率**: {rate:+.1f}% （全体 {rate_rank}位 / {total_municipalities_in_rank}市町村）\n"
            result += f"- {end_year}年: {end_val:,}{get_unit(metric_jp)}\n"
            result += f"- {start_year}年: {start_val:,}{get_unit(metric_jp)}\n\n"
        elif city in locations: # 選択されているがデータがない場合のみメッセージを表示
            result += f"**{city}**: {start_year}年または{end_year}年のデータがなく、計算できませんでした。\n\n"

    return result

def handle_trend_analysis(df, metric_en, metric_jp, location_type, locations, start_year, end_year):
    """期間推移分析の処理"""
    if location_type == "市町村":
        result = f"## {start_year}年〜{end_year}年 {metric_jp}推移\n\n"
        
        for city in locations:
            data = df.query(f"city == @city & metric == @metric_en & cat1 == 'total' & year >= @start_year & year <= @end_year")
            data = data.sort_values('year')
            
            if not data.empty:
                result += f"### {city}\n\n"
                
                # 年別データ表示
                for _, row in data.iterrows():
                    result += f"- {row['year']}年: {row['value']:,}{get_unit(metric_jp)}\n"
                
                # 期間全体の変化
                if len(data) >= 2:
                    first_value = data.iloc[0]['value']
                    last_value = data.iloc[-1]['value']
                    total_change = last_value - first_value
                    if first_value > 0:
                        total_growth = (total_change / first_value) * 100
                        result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)} ({total_growth:+.1f}%)\n\n"
                    else:
                        result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)}\n\n"
            else:
                result += f"### {city}\n\nデータが見つかりません。\n\n"
        
        return result
    
    elif location_type == "エリア":
        result = f"## {start_year}年〜{end_year}年 エリア別{metric_jp}推移\n\n"
        
        for area in locations:
            area_cities = REGION_MAP.get(area, [])
            
            result += f"### {area}エリア\n\n"
            
            # 年別エリア合計を計算
            years = range(start_year, end_year + 1)
            area_totals = []
            
            for year in years:
                year_data = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @year")
                total_value = year_data['value'].sum()
                area_totals.append((year, total_value))
                result += f"- {year}年: {total_value:,}{get_unit(metric_jp)}\n"
            
            # 期間全体の変化
            if len(area_totals) >= 2:
                first_value = area_totals[0][1]
                last_value = area_totals[-1][1]
                total_change = last_value - first_value
                if first_value > 0:
                    total_growth = (total_change / first_value) * 100
                    result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)} ({total_growth:+.1f}%)\n\n"
                else:
                    result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)}\n\n"
        
        return result
    
    else:  # 全体
        result = f"## {start_year}年〜{end_year}年 沖縄県全体{metric_jp}推移\n\n"
        
        years = range(start_year, end_year + 1)
        totals = []
        
        for year in years:
            year_data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @year")
            total_value = year_data['value'].sum()
            totals.append((year, total_value))
            result += f"- {year}年: {total_value:,}{get_unit(metric_jp)}\n"
        
        # 期間全体の変化
        if len(totals) >= 2:
            first_value = totals[0][1]
            last_value = totals[-1][1]
            total_change = last_value - first_value
            if first_value > 0:
                total_growth = (total_change / first_value) * 100
                result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)} ({total_growth:+.1f}%)\n"
            else:
                result += f"\n**期間全体の変化:** {total_change:+,}{get_unit(metric_jp)}\n"
        
        return result

def handle_comparison(df, metric_en, metric_jp, location_type, locations, comparison_year):
    """比較分析の処理"""
    if location_type == "市町村":
        data = df.query(f"city in @locations & metric == @metric_en & cat1 == 'total' & year == @comparison_year")
        data = data.sort_values('value', ascending=False)
        
        result = f"## {comparison_year}年 {metric_jp}比較\n\n"
        
        for i, (_, row) in enumerate(data.iterrows(), 1):
            result += f"**{i}位: {row['city']}** - {row['value']:,}{get_unit(metric_jp)}\n"
        
        # 差異分析
        if len(data) >= 2:
            max_value = data.iloc[0]['value']
            min_value = data.iloc[-1]['value']
            diff = max_value - min_value
            
            result += f"\n**最大差:** {diff:,}{get_unit(metric_jp)}\n"
            result += f"（{data.iloc[0]['city']} vs {data.iloc[-1]['city']}）\n"
        
        return result
    
    elif location_type == "エリア":
        result = f"## {comparison_year}年 エリア別{metric_jp}比較\n\n"
        
        area_data = []
        for area in locations:
            area_cities = REGION_MAP.get(area, [])
            area_total = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @comparison_year")['value'].sum()
            area_data.append((area, area_total))
        
        # エリアを値でソート
        area_data.sort(key=lambda x: x[1], reverse=True)
        
        for i, (area, total) in enumerate(area_data, 1):
            result += f"**{i}位: {area}エリア** - {total:,}{get_unit(metric_jp)}\n"
        
        # エリア構成詳細
        result += "\n### エリア構成詳細\n\n"
        for area, total in area_data:
            area_cities = REGION_MAP.get(area, [])
            city_data = df.query(f"city in @area_cities & metric == @metric_en & cat1 == 'total' & year == @comparison_year")
            city_ranking = city_data.sort_values('value', ascending=False).head(3)
            
            result += f"**{area}エリア** (合計: {total:,}{get_unit(metric_jp)})\n"
            for _, row in city_ranking.iterrows():
                result += f"　- {row['city']}: {row['value']:,}{get_unit(metric_jp)}\n"
            result += "\n"
        
        return result
    
    else:  # 全体の場合は意味がないので、トップ10を表示
        data = df.query(f"metric == @metric_en & cat1 == 'total' & year == @comparison_year")
        ranking = data.sort_values('value', ascending=False).head(10)
        
        result = f"## {comparison_year}年 沖縄県全体{metric_jp}トップ10\n\n"
        
        for i, (_, row) in enumerate(ranking.iterrows(), 1):
            result += f"**{i}位: {row['city']}** - {row['value']:,}{get_unit(metric_jp)}\n"
        
        # 全体統計
        total_value = data['value'].sum()
        avg_value = data['value'].mean()
        
        result += f"\n**県全体合計:** {total_value:,}{get_unit(metric_jp)}\n"
        result += f"**市町村平均:** {avg_value:,.1f}{get_unit(metric_jp)}\n"
        
        return result

def get_unit(metric_jp):
    """指標に応じた単位を返す"""
    units = {
        "軒数": "軒",
        "施設数": "軒", 
        "客室数": "室",
        "部屋数": "室",
        "収容人数": "人",
        "定員": "人"
    }
    return units.get(metric_jp, "")

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

    # 指標マッピング
    elem_map = {"軒数":"facilities","客室数":"rooms","収容人数":"capacity"}

    # ===== タブで分離 =====
    tab1, tab2, tab3, tab4, tab5, tab_help = st.tabs(["🤖 ランキング分析", "🏘️ 市町村別分析", "🏨 ホテル・旅館特化　規模別分析", "🏛️ ホテル・旅館特化　宿泊形態別分析", "🗺️ エリア別分析", "📖 ヘルプ"])

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

    # =================================================
    # TAB 1: ランキング分析（自然言語質問機能）
    # =================================================
    with tab1:
        # 新しいヘッダー部分 ↓
        col_header1, col_header2 = st.columns([5, 1])
        with col_header1:
            st.header("🤖 ランキング分析")
            st.write("以下の項目を選択して、データに関する質問を構築してください。")
        with col_header2:
            with st.popover("❓ このタブの使い方"):
                st.markdown("""
                **自然言語形式で簡単データ分析**
                
                ✅ **基本情報取得**: 複数指標の一覧表示  
                ✅ **ランキング表示**: トップランキング生成  
                ✅ **増減分析**: 成長率・変化量分析
                """)
        
        # 既存のメイン設定エリアはそのまま ↓
        # --- メイン設定エリア ---
        col1, col2 = st.columns(2)
        
        with col1:
            # 質問タイプの選択
            question_type = st.selectbox(
                "📊 質問タイプ",
                [
                    "基本情報取得", 
                    "ランキング表示", 
                    "増減数ランキング", 
                    "増減率ランキング", 
                    "増減・伸び率分析", 
                    "期間推移分析", 
                    "比較分析"
                ],
                key="question_type"
            )
            
            # 質問タイプに応じて指標の選択方法を変更
            if question_type == "基本情報取得":
                selected_metrics = st.multiselect(
                    "📈 指標（複数選択可）",
                    ["軒数", "客室数", "収容人数"],
                    default=["軒数", "客室数", "収容人数"], # デフォルトで全て選択
                    key="selected_metrics"
                )
            else:
                selected_metric = st.selectbox(
                    "📈 指標",
                    ["軒数", "客室数", "収容人数"],
                    key="selected_metric"
                )

        with col2:
            # 場所選択 - 増減ランキングの場合は任意フィルタ
            if question_type in ["ランキング表示", "増減数ランキング", "増減率ランキング"]:
                st.write("**📍 場所フィルタ（任意）**")
                enable_location_filter = st.checkbox("特定の場所に限定する", value=False, key="enable_location_filter")
                if enable_location_filter:
                    location_type = st.selectbox("場所タイプ", ["市町村", "エリア"], key="location_type")
                    if location_type == "市町村":
                        selected_locations = st.multiselect("市町村選択", all_municipalities, default=all_municipalities, key="selected_cities_nlq")
                    else: # エリア
                        selected_locations = st.multiselect("エリア選択", list(REGION_MAP.keys()), default=list(REGION_MAP.keys()), key="selected_areas_nlq")
                else:
                    location_type = "全体"
                    selected_locations = ["全体"]
            else:
                # その他の質問タイプは場所選択必須
                location_type = st.selectbox("📍 場所タイプ", ["市町村", "エリア", "全体"], key="location_type")
                if location_type == "市町村":
                    selected_locations = st.multiselect("市町村選択", all_municipalities, default=[], key="selected_cities_nlq")
                elif location_type == "エリア":
                    selected_locations = st.multiselect("エリア選択", list(REGION_MAP.keys()), default=list(REGION_MAP.keys()), key="selected_areas_nlq")
                else:
                    selected_locations = ["全体"]
        
        # 質問タイプ別の詳細設定
        if question_type == "基本情報取得":
            st.subheader("📋 基本情報設定")
            target_year = st.selectbox(
                "対象年度",
                sorted(df_long['year'].unique(), reverse=True),
                key="basic_year"
            )
            
        elif question_type == "ランキング表示":
            st.subheader("🏆 ランキング設定")
            col1, col2 = st.columns(2)
            with col1:
                ranking_count = st.selectbox(
                    "表示件数",
                    [3, 5, 10, 15, 20],
                    index=1,
                    key="ranking_count"
                )
            with col2:
                ranking_year = st.selectbox(
                    "対象年度",
                    sorted(df_long['year'].unique(), reverse=True),
                    key="ranking_year"
                )

        elif question_type in ["増減数ランキング", "増減率ランキング"]:
            st.subheader("📈 増減ランキング設定")
            col1, col2, col3 = st.columns(3)
            with col1:
                ranking_count_change = st.selectbox(
                    "表示件数",
                    [3, 5, 10, 15, 20],
                    index=1,
                    key="ranking_count_change"
                )
            with col2:
                change_analysis_type = st.selectbox(
                    "分析タイプ",
                    ["対前年比較", "期間比較"],
                    key="change_analysis_type"
                )
            with col3:
                if change_analysis_type == "対前年比較":
                    target_year_ranking = st.selectbox(
                        "対象年度",
                        sorted(df_long['year'].unique(), reverse=True),
                        key="target_year_ranking"
                    )
                else:
                    period_years_ranking = st.selectbox(
                        "期間",
                        ["過去3年間", "過去5年間", "過去10年間", "カスタム"],
                        key="period_years_ranking"
                    )
                    if period_years_ranking == "カスタム":
                        col_start, col_end = st.columns(2)
                        with col_start:
                            custom_start_ranking = st.selectbox(
                                "開始年",
                                sorted(df_long['year'].unique()),
                                key="custom_start_ranking"
                            )
                        with col_end:
                            custom_end_ranking = st.selectbox(
                                "終了年",
                                sorted(df_long['year'].unique(), reverse=True),
                                key="custom_end_ranking"
                            )
            
        elif question_type == "増減・伸び率分析":
            st.subheader("📈 増減分析設定")
            col1, col2, col3 = st.columns(3)
            with col1:
                analysis_type = st.selectbox(
                    "分析タイプ",
                    ["対前年比較", "期間比較（開始年〜最新年）"],
                    key="analysis_type"
                )
            with col2:
                result_type = st.selectbox(
                    "結果タイプ",
                    ["増減数", "増減率", "両方"],
                    key="result_type"
                )
            with col3:
                if analysis_type == "対前年比較":
                    target_year_change = st.selectbox(
                        "対象年度",
                        sorted(df_long['year'].unique(), reverse=True),
                        key="target_year_change"
                    )
                else:
                    period_years = st.selectbox(
                        "期間",
                        ["過去3年間", "過去5年間", "過去10年間", "カスタム"],
                        key="period_years"
                    )
                    if period_years == "カスタム":
                        col_start, col_end = st.columns(2)
                        with col_start:
                            custom_start = st.selectbox(
                                "開始年",
                                sorted(df_long['year'].unique()),
                                key="custom_start"
                            )
                        with col_end:
                            custom_end = st.selectbox(
                                "終了年",
                                sorted(df_long['year'].unique(), reverse=True),
                                key="custom_end"
                            )
            
            # ランキング形式かどうか
            show_ranking = st.checkbox(
                "ランキング形式で表示",
                value=True,
                key="show_ranking"
            )
            if show_ranking:
                ranking_count_change = st.selectbox(
                    "表示件数",
                    [3, 5, 10, 15, 20],
                    index=1,
                    key="ranking_count_change"
                )
            
        elif question_type == "期間推移分析":
            st.subheader("📊 期間推移設定")
            col1, col2 = st.columns(2)
            with col1:
                period_type = st.selectbox(
                    "期間タイプ",
                    ["過去3年間", "過去5年間", "過去10年間", "カスタム期間"],
                    key="period_type"
                )
            with col2:
                if period_type == "カスタム期間":
                    col_start, col_end = st.columns(2)
                    with col_start:
                        trend_start = st.selectbox(
                            "開始年",
                            sorted(df_long['year'].unique()),
                            key="trend_start"
                        )
                    with col_end:
                        trend_end = st.selectbox(
                            "終了年",
                            sorted(df_long['year'].unique(), reverse=True),
                            key="trend_end"
                        )
        
        elif question_type == "比較分析":
            st.subheader("🔍 比較設定")
            comparison_year = st.selectbox(
                "比較年度",
                sorted(df_long['year'].unique(), reverse=True),
                key="comparison_year"
            )
        
        # 質問実行ボタン
        if st.button("🔍 質問を実行", type="primary", key="run_structured_query_basic"):
            # 基本情報取得の場合は複数指標、その他は単一指標
            if question_type == "基本情報取得":
                metrics_to_pass = selected_metrics
                if not metrics_to_pass:
                    st.warning("指標を1つ以上選択してください。")
                    metrics_to_pass = None
            else:
                metrics_to_pass = selected_metric
                if not metrics_to_pass:
                    st.warning("指標を選択してください。")
                    metrics_to_pass = None
            
            # 場所選択のチェック - ランキング系は任意、その他は必須
            needs_location = question_type not in ["ランキング表示", "増減数ランキング", "増減率ランキング"]
            location_required = needs_location and location_type in ["市町村", "エリア"] and not selected_locations
            
            if location_required:
                st.warning("場所を選択してください。")
            elif not metrics_to_pass:
                pass  # 既に警告済み
            else:
                with st.spinner("データを分析中..."):
                    try:
                        # パラメータを構築
                        if question_type == "基本情報取得":
                            # 基本情報取得の場合は複数指標を渡す
                            params = {
                                'question_type': question_type,
                                'metrics': selected_metrics,  # 複数指標
                                'location_type': location_type,
                                'locations': selected_locations,
                                'df': df_long,
                                'all_municipalities': all_municipalities,
                                'debug_mode': st.session_state.get('debug_mode', False),
                                'target_year': target_year
                            }
                        else:
                            # その他の質問タイプは単一指標
                            params = {
                                'question_type': question_type,
                                'metric': selected_metric,
                                'location_type': location_type,
                                'locations': selected_locations,
                                'df': df_long,
                                'all_municipalities': all_municipalities,
                                'debug_mode': st.session_state.get('debug_mode', False)
                            }
                        
                        # --- 質問タイプ別のパラメータ追加（完全版） ---
                        if question_type == "ランキング表示":
                            params['ranking_count'] = ranking_count
                            params['ranking_year'] = ranking_year

                        elif question_type in ["増減数ランキング", "増減率ランキング"]:
                            params['ranking_count'] = ranking_count_change
                            params['analysis_type'] = change_analysis_type
                            params['result_type'] = "増減数" if question_type == "増減数ランキング" else "増減率"
                            
                            if change_analysis_type == "対前年比較":
                                params['target_year'] = target_year_ranking
                            else:  # 期間比較
                                if period_years_ranking == "カスタム":
                                    params['start_year'] = custom_start_ranking
                                    params['end_year'] = custom_end_ranking
                                else:
                                    current_year = int(df_long['year'].max())
                                    period_value = period_years_ranking
                                    period_map = {"過去3年間": 2, "過去5年間": 4, "過去10年間": 9}
                                    params['start_year'] = current_year - period_map.get(period_value, 2)
                                    params['end_year'] = current_year

                        elif question_type == "増減・伸び率分析":
                            params['analysis_type'] = analysis_type
                            params['result_type'] = result_type
                            if analysis_type == "対前年比較":
                                params['target_year'] = target_year_change
                            else:
                                if period_years == "カスタム":
                                    params['start_year'] = custom_start
                                    params['end_year'] = custom_end
                                else:
                                    current_year = int(df_long['year'].max())
                                    period_value = period_years
                                    period_map = {"過去3年間": 2, "過去5年間": 4, "過去10年間": 9}
                                    params['start_year'] = current_year - period_map.get(period_value, 2)
                                    params['end_year'] = current_year
                            params['show_ranking'] = show_ranking
                            if show_ranking:
                                params['ranking_count'] = ranking_count_change
                        
                        elif question_type == "期間推移分析":
                            if period_type == "カスタム期間":
                                params['start_year'] = trend_start
                                params['end_year'] = trend_end
                            else:
                                current_year = int(df_long['year'].max())
                                period_value = period_type
                                period_map = {"過去3年間": 2, "過去5年間": 4, "過去10年間": 9}
                                params['start_year'] = current_year - period_map.get(period_value, 4)
                                params['end_year'] = current_year
                        
                        elif question_type == "比較分析":
                            params['comparison_year'] = comparison_year

                        # 回答生成と表示
                        answer = process_structured_question(**params)
                        
                        st.markdown("### 📊 分析結果")
                        if isinstance(answer, go.Figure):
                            st.plotly_chart(answer, use_container_width=True)
                        elif isinstance(answer, str):
                            st.markdown(answer)
                        else:
                            st.write(answer)

                    except Exception as e:
                        st.error(f"分析処理中にエラーが発生しました: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        # プレビューエリア
        with st.expander("👁️ 質問プレビュー"):
            # 基本情報取得の場合は複数指標対応
            preview_params = locals().copy()
            if question_type == "基本情報取得":
                preview_params['selected_metrics'] = selected_metrics
                metric_for_preview = selected_metrics[0] if selected_metrics else "軒数"
            else:
                metric_for_preview = selected_metric if 'selected_metric' in locals() else "軒数"
            
            preview_text = generate_question_preview(
                question_type, metric_for_preview, location_type, selected_locations,
                preview_params
            )
            st.write(f"**生成される質問:** {preview_text}")

    # =================================================
    # TAB 2: 市町村別分析（accommodation_typeのみ）
    # =================================================
    with tab2:
        col_header1, col_header2 = st.columns([5, 1])
        with col_header1:
            st.header("🏘️ 市町村別の状況")
        with col_header2:
            with st.popover("❓ このタブの使い方"):
                st.markdown("""
                **市町村を深掘り分析**
                
                ✅ **宿泊形態別**: ホテル・民宿・ペンション等の詳細分析  
                ✅ **複数市町村比較**: 同時に比較可能  
                ✅ **順位表示**: 全市町村中の順位を確認
                """)
        
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
    # TAB 3: ホテル・旅館特化　規模別分析
    # =================================================
    with tab3:
        col_header1, col_header2 = st.columns([5, 1])
        with col_header1:
            st.header("🏨 ホテル・旅館特化　規模別分析の状況")
        with col_header2:
            with st.popover("❓ このタブの使い方"):
                st.markdown("""
                **ホテル・旅館の規模による分析**
                
                ✅ **規模分類**: 大規模・中規模・小規模別分析  
                ✅ **ホテル特化**: ホテル・旅館のみ対象  
                ✅ **長期トレンド**: 18年間の推移分析
                """)
        
        with st.expander("📋 このタブの分析について"):
            st.markdown("""
            **分析対象**: ホテル・旅館のみ（民宿・ペンション等は除く）  
            **分類基準**: 収容人数による規模区分
            - 大規模: 300人以上
            - 中規模: 100人以上300人未満  
            - 小規模: 100人未満
            
            **対象期間**: 2007年〜2024年（18年間の長期トレンド分析が可能）
            """)
        
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
    # TAB 4: ホテル・旅館特化　宿泊形態別分析（hotel_breakdown H26-R6）
    # =================================================
    with tab4:
        col_header1, col_header2 = st.columns([5, 1])
        with col_header1:
            st.header("🏛️ ホテル・旅館特化　宿泊形態別分析の状況")
        with col_header2:
            with st.popover("❓ このタブの使い方"):
                st.markdown("""
                **ホテル・旅館の種別による詳細分析**
                
                ✅ **ホテル種別**: リゾート・ビジネス・シティ・旅館  
                ✅ **マトリックス**: 種別×規模のクロス分析  
                ✅ **詳細期間**: 2014年〜2024年の詳細データ
                """)

        with st.expander("📋 このタブの分析について"):
            st.markdown("""
            **分析対象**: ホテル・旅館の詳細分類データ  
            **分類基準**: 施設の機能・サービス内容による区分
            - **リゾートホテル**: 観光・レジャー特化
            - **ビジネスホテル**: 出張・商用特化
            - **シティホテル**: 都市部総合サービス
            - **旅館**: 日本伝統スタイル
            
            **対象期間**: 2014年〜2024年（より詳細な分析が可能）  
            **特徴**: 観光形態や利用目的に応じた分析に適している
            """)

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
                            else:
                                st.info("選択した条件のデータがありません")

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
    # TAB 5: エリア別分析（全シート対応）
    # =================================================
    with tab5:
        col_header1, col_header2 = st.columns([5, 1])
        with col_header1:
            st.header("🗺️ エリア別の状況")
        with col_header2:
            with st.popover("❓ このタブの使い方"):
                st.markdown("""
                **6つのエリアで沖縄全体を俯瞰**
                
                ✅ **エリア構成**: 南部・中部・北部・宮古・八重山・離島  
                ✅ **比較分析**: エリア間の特性比較  
                ✅ **全施設対応**: 全宿泊施設 or ホテル特化選択可能
                """)
        
        # ===== 共通設定エリア =====
        st.subheader("🎛️ 分析設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # エリア選択
            area_names = list(REGION_MAP.keys())
            sel_areas = st.multiselect(
                "エリアを選択（デフォルト：全選択済み）",
                area_names,
                default=area_names,
                key="areas",
                help="必要に応じて特定のエリアに絞り込んでください"
            )
            
            # 便利ボタン
            col_area_select, col_area_clear = st.columns(2)
            with col_area_select:
                if st.button("全エリア選択", key="select_all_areas_tab5"):
                    st.rerun()
            with col_area_clear:
                if st.button("全エリア解除", key="clear_all_areas_tab5"):
                    st.rerun()
            
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
                        st.subheader("📊 宿泊形態別詳細 - 全宿泊施設")
                        
                        # 宿泊形態別カテゴリの取得
                        accommodation_categories = sorted([cat for cat in df_analysis['cat1'].unique() if cat and cat != 'total'])
                        
                        # 英語キーを日本語表示に変換
                        accommodation_categories_jp = []
                        for cat in accommodation_categories:
                            if cat in accommodation_type_mapping:
                                accommodation_categories_jp.append(accommodation_type_mapping[cat])
                            else:
                                accommodation_categories_jp.append(cat)
                        
                        # デフォルトでホテル・旅館、民宿、ペンション・貸別荘を選択
                        default_categories_jp = ["ホテル・旅館", "民宿", "ペンション・貸別荘"]
                        available_defaults = [cat for cat in default_categories_jp if cat in accommodation_categories_jp]
                        
                        sel_categories_area_jp = st.multiselect(
                            "宿泊形態詳細項目",
                            accommodation_categories_jp,
                            default=available_defaults if available_defaults else accommodation_categories_jp[:3],
                            key="area_categories"
                        )
                        
                        # 日本語表示から英語キーに逆変換
                        reverse_mapping_area = {v: k for k, v in accommodation_type_mapping.items()}
                        sel_categories_area = [reverse_mapping_area.get(cat_jp, cat_jp) for cat_jp in sel_categories_area_jp]
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            
                            st.subheader(f"📊 {element}の推移（宿泊形態別）")
                            
                            # 選択された宿泊形態ごとのグラフ
                            for category in sel_categories_area:
                                # 日本語表示名を取得
                                category_display = accommodation_type_mapping.get(category, category)
                                st.write(f"**{element} ({category_display})**")
                                
                                df_category_area = (
                                    df_analysis.query(
                                        f"metric == @metric_en & cat1 == @category & "
                                        "city in @city_to_area.keys() & "
                                        f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                    )
                                    .assign(area=lambda d: d["city"].map(city_to_area))
                                    .groupby(["area", "year"])['value'].sum()
                                    .unstack("area")
                                    .reindex(columns=sel_areas)
                                    .sort_index()
                                )

                                fig_category_area = create_line_chart(
                                    df_category_area, sel_areas,
                                    f"エリア別{element}推移（{category_display}） ({year_range_area[0]}-{year_range_area[1]})",
                                    element, show_legend=False, df_all=None, show_ranking=False
                                )
                                st.plotly_chart(fig_category_area, use_container_width=True)
                                st.dataframe(df_category_area.transpose().style.format(thousands=","), use_container_width=True)
                            
                            # 指標間の区切り
                            if element != sel_elems_area[-1]:
                                st.markdown("---")
            
            else:  # ホテル・旅館特化
                # scale_class または hotel_breakdown データを使用
                df_scale_area = df_long.query("table == 'scale_class'")
                df_hotel_area = df_long.query("table == 'hotel_breakdown'")
                
                if not df_scale_area.empty:
                    df_analysis = df_scale_area
                    table_name = "scale_class"
                    st.info("📊 **ホテル・旅館特化**: ホテル・旅館のみを対象とした規模別分析")
                elif not df_hotel_area.empty:
                    df_analysis = df_hotel_area
                    table_name = "hotel_breakdown"
                    st.info("📊 **ホテル・旅館特化**: ホテル・旅館の詳細分類別分析")
                else:
                    st.warning("⚠️ ホテル・旅館特化データが見つかりません。")
                    df_analysis = pd.DataFrame()
                
                if not df_analysis.empty:
                    # 表示方法選択
                    if table_name == "scale_class":
                        view_mode_hotel_area = st.selectbox(
                            "表示方法",
                            ["概要表示", "規模別詳細"],
                            key="area_view_mode_hotel"
                        )
                    else:  # hotel_breakdown
                        view_mode_hotel_area = st.selectbox(
                            "表示方法",
                            ["概要表示", "ホテル種別詳細"],
                            key="area_view_mode_hotel"
                        )
                    
                    # ===== 概要表示 =====
                    if view_mode_hotel_area == "概要表示":
                        st.subheader("📈 概要 - ホテル・旅館推移")
                        
                        for element in sel_elems_area:
                            metric_en = elem_map[element]
                            
                            # Total データ
                            df_hotel_total = (
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

                            fig_hotel_total = create_line_chart(
                                df_hotel_total, sel_areas, 
                                f"エリア別{element}推移（ホテル・旅館） ({year_range_area[0]}-{year_range_area[1]})",
                                element, show_legend=False, df_all=None, show_ranking=False
                            )
                            st.plotly_chart(fig_hotel_total, use_container_width=True)
                            st.dataframe(df_hotel_total.transpose().style.format(thousands=","), use_container_width=True)
                    
                    # ===== 詳細表示 =====
                    else:
                        if table_name == "scale_class":
                            st.subheader("📊 規模別詳細 - ホテル・旅館")
                            
                            # 規模別カテゴリの取得
                            scale_categories = sorted([cat for cat in df_analysis['cat1'].unique() if cat and cat != 'total'])
                            
                            # 英語キーを日本語表示に変換
                            scale_categories_jp = []
                            for cat in scale_categories:
                                if cat in scale_class_mapping:
                                    scale_categories_jp.append(scale_class_mapping[cat])
                                else:
                                    scale_categories_jp.append(cat)
                            
                            sel_scale_categories_area_jp = st.multiselect(
                                "規模分類（複数選択可）",
                                scale_categories_jp,
                                default=scale_categories_jp,
                                key="area_scale_categories"
                            )
                            
                            # 日本語表示から英語キーに逆変換
                            reverse_scale_mapping_area = {v: k for k, v in scale_class_mapping.items()}
                            sel_scale_categories_area = [reverse_scale_mapping_area.get(cat_jp, cat_jp) for cat_jp in sel_scale_categories_area_jp]
                            
                            for element in sel_elems_area:
                                metric_en = elem_map[element]
                                
                                st.subheader(f"📊 {element}の推移（規模別）")
                                
                                # 選択された規模分類ごとのグラフ
                                for category in sel_scale_categories_area:
                                    # 日本語表示名を取得
                                    category_display = scale_class_mapping.get(category, category)
                                    st.write(f"**{element} ({category_display})**")
                                    
                                    df_category_area = (
                                        df_analysis.query(
                                            f"metric == @metric_en & cat1 == @category & "
                                            "city in @city_to_area.keys() & "
                                            f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                        )
                                        .assign(area=lambda d: d["city"].map(city_to_area))
                                        .groupby(["area", "year"])['value'].sum()
                                        .unstack("area")
                                        .reindex(columns=sel_areas)
                                        .sort_index()
                                    )

                                    fig_category_area = create_line_chart(
                                        df_category_area, sel_areas,
                                        f"エリア別{element}推移（{category_display}） ({year_range_area[0]}-{year_range_area[1]})",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig_category_area, use_container_width=True)
                                    st.dataframe(df_category_area.transpose().style.format(thousands=","), use_container_width=True)
                                
                                # 指標間の区切り
                                if element != sel_elems_area[-1]:
                                    st.markdown("---")
                        
                        else:  # hotel_breakdown
                            st.subheader("📊 ホテル種別詳細")
                            
                            # hotel_breakdownの詳細カテゴリ取得
                            hotel_categories = sorted([cat for cat in df_analysis['cat1'].unique() if cat and cat != 'total'])
                            
                            sel_hotel_categories_area = st.multiselect(
                                "ホテル種別（複数選択可）",
                                hotel_categories,
                                default=hotel_categories[:5] if len(hotel_categories) > 5 else hotel_categories,
                                key="area_hotel_categories"
                            )
                            
                            for element in sel_elems_area:
                                metric_en = elem_map[element]
                                
                                st.subheader(f"📊 {element}の推移（ホテル種別）")
                                
                                # 選択されたホテル種別ごとのグラフ
                                for category in sel_hotel_categories_area:
                                    st.write(f"**{element} ({category})**")
                                    
                                    df_category_area = (
                                        df_analysis.query(
                                            f"metric == @metric_en & cat1 == @category & "
                                            "city in @city_to_area.keys() & "
                                            f"year >= {year_range_area[0]} & year <= {year_range_area[1]}"
                                        )
                                        .assign(area=lambda d: d["city"].map(city_to_area))
                                        .groupby(["area", "year"])['value'].sum()
                                        .unstack("area")
                                        .reindex(columns=sel_areas)
                                        .sort_index()
                                    )

                                    fig_category_area = create_line_chart(
                                        df_category_area, sel_areas,
                                        f"エリア別{element}推移（{category}） ({year_range_area[0]}-{year_range_area[1]})",
                                        element, show_legend=False, df_all=None, show_ranking=False
                                    )
                                    st.plotly_chart(fig_category_area, use_container_width=True)
                                    st.dataframe(df_category_area.transpose().style.format(thousands=","), use_container_width=True)
                                
                                # 指標間の区切り
                                if element != sel_elems_area[-1]:
                                    st.markdown("---")

    # =================================================
    # TAB 6: ヘルプ・使い方
    # =================================================
    with tab_help:
        st.header("📖 アプリ使用方法・完全ガイド")
        
        st.markdown("""
        ### 🎯 このヘルプについて
        このアプリの全機能を効果的に活用するための完全ガイドです。
        初めてご利用の方は「**🎯 アプリ概要**」から、特定の機能について知りたい方は該当するセクションをご覧ください。
        """)
        
        # ヘルプコンテンツ表示関数を呼び出し
        display_help_content()

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