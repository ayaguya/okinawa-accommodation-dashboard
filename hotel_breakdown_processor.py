# -*- coding: utf-8 -*-
# hotel_breakdown_processor.py
# =============================================================
# H26年以降のExcelファイルからhotel_breakdownデータを実際に抽出・処理
# 発見されたデータ構造に基づいて正確なデータを生成
# =============================================================

import pandas as pd
from pathlib import Path
import numpy as np

def process_hotel_breakdown_data():
    """hotel_breakdownシートから実データを抽出"""
    
    RAW_DIR = Path("data/raw")
    BY_YEAR_DIR = Path("data/processed/by_year")
    BY_YEAR_DIR.mkdir(parents=True, exist_ok=True)
    
    # H26年以降のファイルリスト
    hotel_breakdown_files = {
        2014: "h26.xlsx",
        2015: "h27.xlsx", 
        2016: "h28.xlsx",
        2017: "h29.xlsx",
        2018: "h30.xlsx",
        2019: "r1.xlsx",
        2020: "r2.xlsx",
        2021: "r3.xlsx",
        2022: "r4.xlsx",
        2023: "r5.xlsx",
        2024: "r6.xlsx"
    }
    
    # 市町村リスト（行番号3以降の順序）
    municipalities = [
        "那覇市", "糸満市", "豊見城市", "八重瀬町", "南城市", "与那原町", "南風原町",  # 南部
        "沖縄市", "宜野湾市", "浦添市", "うるま市", "読谷村", "嘉手納町", "北谷町", "北中城村", "中城村", "西原町",  # 中部
        "名護市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町", "恩納村", "宜野座村", "金武町",  # 北部
        "宮古島市", "多良間村",  # 宮古
        "石垣市", "竹富町", "与那国町",  # 八重山
        "久米島町", "渡嘉敷村", "座間味村", "粟国村", "渡名喜村", "南大東村", "北大東村", "伊江村", "伊平屋村", "伊是名村"  # 離島
    ]
    
    # データ構造マッピング
    hotel_type_columns = {
        "resort_hotel": {"large": [1, 2, 3], "medium": [4, 5, 6], "small": [7, 8, 9]},
        "business_hotel": {"large": [10, 11, 12], "medium": [13, 14, 15], "small": [16, 17, 18]},
        "city_hotel": {"large": [19, 20, 21], "medium": [22, 23, 24], "small": [25, 26, 27]},
        "ryokan": {"large": [28, 29, 30], "medium": [31, 32, 33], "small": [34, 35, 36]},
        "total": {"total": [37, 38, 39]}
    }
    
    metric_names = {0: "facilities", 1: "rooms", 2: "capacity"}
    
    all_data = []
    
    for year, filename in hotel_breakdown_files.items():
        file_path = RAW_DIR / filename
        if not file_path.exists():
            print(f"⚠️ ファイルが見つかりません: {file_path}")
            continue
            
        try:
            print(f"📊 処理中: {year}年 ({filename})")
            
            # hotel_breakdownシートを読み込み
            df = pd.read_excel(file_path, sheet_name="hotel_breakdown", header=None)
            
            # データ行（3行目以降）を処理
            for city_idx, city in enumerate(municipalities):
                data_row_idx = 3 + city_idx
                
                if data_row_idx >= len(df):
                    print(f"  ⚠️ {city}: データ行が見つかりません (行{data_row_idx})")
                    continue
                
                # 各ホテル種別×規模×メトリックの組み合わせを処理
                for hotel_type, scale_cols in hotel_type_columns.items():
                    for scale, col_indices in scale_cols.items():
                        for metric_idx, col_idx in enumerate(col_indices):
                            if col_idx < len(df.columns):
                                value = df.iloc[data_row_idx, col_idx]
                                
                                # 数値に変換（NaNや文字列は0に）
                                if pd.isna(value) or not isinstance(value, (int, float)):
                                    value = 0
                                else:
                                    value = int(value)
                                
                                # データレコードを作成
                                record = {
                                    "year": year,
                                    "city": city,
                                    "metric": metric_names[metric_idx],
                                    "cat1": f"{hotel_type}_{scale}" if hotel_type != "total" else "total",
                                    "cat2": "",
                                    "table": "hotel_breakdown",
                                    "value": value
                                }
                                all_data.append(record)
            
            print(f"  ✅ {year}年: {len(municipalities)} 市町村処理完了")
            
        except Exception as e:
            print(f"  ❌ {year}年の処理エラー: {e}")
    
    # DataFrameに変換
    df_hotel_breakdown = pd.DataFrame(all_data)
    
    if len(df_hotel_breakdown) > 0:
        # 年度別にファイルを保存
        for year in df_hotel_breakdown['year'].unique():
            year_data = df_hotel_breakdown[df_hotel_breakdown['year'] == year]
            output_file = BY_YEAR_DIR / f"long_{year}_hotel_breakdown.csv"
            year_data.to_csv(output_file, index=False, encoding='utf-8')
            print(f"📄 保存: {output_file} ({len(year_data):,}行)")
        
        # 全年度統合ファイルも保存
        output_file_all = BY_YEAR_DIR / "hotel_breakdown_all_years.csv"
        df_hotel_breakdown.to_csv(output_file_all, index=False, encoding='utf-8')
        print(f"📄 統合ファイル保存: {output_file_all} ({len(df_hotel_breakdown):,}行)")
        
        # データサマリー表示
        print(f"\n📊 データサマリー:")
        print(f"  総レコード数: {len(df_hotel_breakdown):,}")
        print(f"  年度: {df_hotel_breakdown['year'].min()}〜{df_hotel_breakdown['year'].max()}")
        print(f"  市町村数: {df_hotel_breakdown['city'].nunique()}")
        print(f"  テーブル: {list(df_hotel_breakdown['table'].unique())}")
        print(f"  メトリック: {list(df_hotel_breakdown['metric'].unique())}")
        print(f"  カテゴリ数: {df_hotel_breakdown['cat1'].nunique()}")
        
        print(f"\n📋 cat1の種類:")
        for cat1 in sorted(df_hotel_breakdown['cat1'].unique()):
            count = len(df_hotel_breakdown[df_hotel_breakdown['cat1'] == cat1])
            print(f"    {cat1}: {count:,}行")
        
        # サンプルデータ表示
        print(f"\n📄 サンプルデータ (最新年度: {df_hotel_breakdown['year'].max()}年、那覇市):")
        sample = df_hotel_breakdown[
            (df_hotel_breakdown['year'] == df_hotel_breakdown['year'].max()) & 
            (df_hotel_breakdown['city'] == '那覇市')
        ].head(10)
        print(sample.to_string(index=False))
        
    else:
        print("❌ データが抽出されませんでした")
    
    return df_hotel_breakdown

def update_load_all_data_function():
    """load_all_data関数のアップデート指示を表示"""
    print(f"\n🔧 次のステップ: okinawa_accommodation_dashboard.py の修正")
    print(f"load_all_data() 関数に以下を追加してください:")
    print(f"""
    # hotel_breakdownデータの読み込み
    hotel_breakdown_file = BY_YEAR_DIR / "hotel_breakdown_all_years.csv"
    if hotel_breakdown_file.exists():
        df_hotel = pd.read_csv(hotel_breakdown_file, dtype={{"year": int}})
        dfs.append(df_hotel)
        print(f"hotel_breakdown データ読み込み: {{len(df_hotel):,}}行")
    """)

if __name__ == "__main__":
    print("=== hotel_breakdown 実データ抽出開始 ===")
    
    # 実データを抽出・処理
    df_result = process_hotel_breakdown_data()
    
    # 次のステップの案内
    update_load_all_data_function()
    
    print(f"\n🎉 処理完了！")
    print(f"Streamlitアプリを再起動して TAB 3 が動作することを確認してください:")
    print(f"streamlit run okinawa_accommodation_dashboard.py")