import pandas as pd
import numpy as np
from pathlib import Path
import os
import re

def get_year_from_filename(filename):
    """
    ファイル名から年度を推定
    """
    filename_lower = filename.lower()
    
    # 和暦パターン
    if 'h26' in filename_lower or '平成26' in filename_lower:
        return 2014
    elif 'h27' in filename_lower or '平成27' in filename_lower:
        return 2015
    elif 'h28' in filename_lower or '平成28' in filename_lower:
        return 2016
    elif 'h29' in filename_lower or '平成29' in filename_lower:
        return 2017
    elif 'h30' in filename_lower or '平成30' in filename_lower:
        return 2018
    elif 'r1' in filename_lower or 'r01' in filename_lower or '令和1' in filename_lower or '令和01' in filename_lower:
        return 2019
    elif 'r2' in filename_lower or 'r02' in filename_lower or '令和2' in filename_lower or '令和02' in filename_lower:
        return 2020
    elif 'r3' in filename_lower or 'r03' in filename_lower or '令和3' in filename_lower or '令和03' in filename_lower:
        return 2021
    elif 'r4' in filename_lower or 'r04' in filename_lower or '令和4' in filename_lower or '令和04' in filename_lower:
        return 2022
    elif 'r5' in filename_lower or 'r05' in filename_lower or '令和5' in filename_lower or '令和05' in filename_lower:
        return 2023
    elif 'r6' in filename_lower or 'r06' in filename_lower or '令和6' in filename_lower or '令和06' in filename_lower:
        return 2024
    
    # 西暦パターン
    year_match = re.search(r'20(14|15|16|17|18|19|20|21|22|23|24)', filename_lower)
    if year_match:
        return int('20' + year_match.group(1))
    
    return None

def find_excel_files(data_dir="data/raw"):
    """
    data/rawディレクトリからExcelファイルを検索
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ ディレクトリが存在しません: {data_path}")
        return []
    
    excel_files = []
    excel_extensions = ['.xlsx', '.xls']
    
    print(f"📁 {data_path} でExcelファイルを検索中...")
    
    for file_path in data_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in excel_extensions:
            year = get_year_from_filename(file_path.name)
            excel_files.append({
                'path': file_path,
                'filename': file_path.name,
                'year': year
            })
            print(f"  📄 {file_path.name} → 年度: {year}")
    
    # 年度でソート
    excel_files.sort(key=lambda x: x['year'] if x['year'] else 0)
    
    return excel_files

def check_sheet_exists(excel_path, sheet_name):
    """
    指定されたシートが存在するかチェック
    """
    try:
        excel_file = pd.ExcelFile(excel_path)
        return sheet_name in excel_file.sheet_names
    except Exception:
        return False

def convert_hotel_breakdown_excel_to_csv(excel_path, output_path, year):
    """
    hotel_breakdownシートのExcelファイルを正しいCSV形式に変換
    """
    
    print(f"\n📖 処理中: {excel_path.name} (年度: {year})")
    
    # シートの存在確認
    if not check_sheet_exists(excel_path, 'hotel_breakdown'):
        print(f"⚠️ 'hotel_breakdown'シートが見つかりません。利用可能なシート:")
        try:
            excel_file = pd.ExcelFile(excel_path)
            for sheet in excel_file.sheet_names:
                print(f"     - {sheet}")
        except Exception as e:
            print(f"     エラー: {e}")
        return None
    
    # Excelファイルを読み込み
    try:
        df = pd.read_excel(excel_path, sheet_name='hotel_breakdown', header=None)
    except Exception as e:
        print(f"❌ Excel読み込みエラー: {e}")
        return None
    
    print(f"   データサイズ: {df.shape}")
    
    # 列のマッピングを作成
    hotel_types = ['resort_hotel', 'business_hotel', 'city_hotel', 'ryokan']
    scales = ['large', 'medium', 'small']
    metrics = ['facilities', 'rooms', 'capacity']
    
    col_mapping = []
    col_idx = 1  # 0列目は市町村名
    
    for hotel_type in hotel_types:
        for scale in scales:
            for metric in metrics:
                col_mapping.append({
                    'col_idx': col_idx,
                    'hotel_type': hotel_type,
                    'scale': scale,
                    'metric': metric,
                    'cat1': f"{hotel_type}_{scale}"
                })
                col_idx += 1
    
    # データ変換
    result_data = []
    
    # 4行目以降がデータ（0-indexで3以降）
    processed_cities = 0
    for row_idx in range(3, min(len(df), 100)):  # 安全のため最大100行まで
        city_name = df.iloc[row_idx, 0]
        
        if pd.isna(city_name) or str(city_name).strip() == '':
            continue
        
        city_name = str(city_name).strip()
        processed_cities += 1
        
        # 各列のデータを処理
        for mapping in col_mapping:
            if mapping['col_idx'] < len(df.columns):
                value = df.iloc[row_idx, mapping['col_idx']]
                
                # 数値変換
                if pd.isna(value):
                    value = 0
                else:
                    try:
                        value = int(float(value))
                    except:
                        value = 0
                
                result_data.append({
                    'year': year,
                    'city': city_name,
                    'metric': mapping['metric'],
                    'cat1': mapping['cat1'],
                    'cat2': '',
                    'table': 'hotel_breakdown',
                    'value': value
                })
    
    print(f"   処理された市町村数: {processed_cities}")
    print(f"   データ変換完了: {len(result_data)}レコード")
    
    # totalを計算して追加
    df_temp = pd.DataFrame(result_data)
    
    # 市町村×メトリック別にtotalを計算
    for city in df_temp['city'].unique():
        for metric in metrics:
            city_metric_data = df_temp[
                (df_temp['city'] == city) & (df_temp['metric'] == metric)
            ]
            total_value = city_metric_data['value'].sum()
            
            result_data.append({
                'year': year,
                'city': city,
                'metric': metric,
                'cat1': 'total',
                'cat2': '',
                'table': 'hotel_breakdown',
                'value': total_value
            })
    
    # DataFrame作成
    result_df = pd.DataFrame(result_data)
    
    # 並び替え
    result_df = result_df.sort_values(['city', 'metric', 'cat1']).reset_index(drop=True)
    
    # CSVとして保存
    result_df.to_csv(output_path, index=False, encoding='utf-8')
    
    print(f"   ✅ CSV保存完了: {output_path.name}")
    print(f"   📊 総レコード数: {len(result_df)}")
    
    return result_df

def main():
    print("🏨 複数年度 Excel→CSV変換プロセスを開始します")
    print("対象期間: H26～R6 (2014～2024年)")
    
    # 1. Excelファイルを検索
    excel_files = find_excel_files("data/raw")
    
    if not excel_files:
        print("\n❌ Excelファイルが見つかりません")
        return
    
    # 年度が推定できたファイルのみを処理
    valid_files = [f for f in excel_files if f['year'] is not None]
    
    if not valid_files:
        print("\n❌ 年度が推定できるExcelファイルが見つかりません")
        return
    
    print(f"\n📋 処理対象ファイル: {len(valid_files)}件")
    for file_info in valid_files:
        print(f"   {file_info['year']}年: {file_info['filename']}")
    
    # 2. 出力ディレクトリを作成
    output_dir = Path("data/processed/by_year")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 各ファイルを変換
    successful_conversions = 0
    failed_conversions = 0
    
    for file_info in valid_files:
        year = file_info['year']
        excel_path = file_info['path']
        output_file = output_dir / f"long_{year}_hotel_breakdown.csv"
        
        try:
            result_df = convert_hotel_breakdown_excel_to_csv(excel_path, output_file, year)
            if result_df is not None:
                successful_conversions += 1
                
                # 宮古島市のデータを簡単にチェック（最新年のみ）
                if year == 2024:
                    miyako_data = result_df[result_df['city'] == '宮古島市']
                    if not miyako_data.empty:
                        facilities_total = miyako_data[
                            (miyako_data['metric'] == 'facilities') & 
                            (miyako_data['cat1'] == 'total')
                        ]['value'].iloc[0]
                        print(f"   🔍 宮古島市軒数(Total): {facilities_total}")
            else:
                failed_conversions += 1
                
        except Exception as e:
            print(f"❌ {excel_path.name} の変換でエラー: {e}")
            failed_conversions += 1
    
    # 4. 結果サマリー
    print("\n" + "="*50)
    print("📊 変換結果サマリー")
    print("="*50)
    print(f"✅ 成功: {successful_conversions}件")
    print(f"❌ 失敗: {failed_conversions}件")
    print(f"📁 出力ディレクトリ: {output_dir}")
    
    if successful_conversions > 0:
        print("\n📝 次のステップ:")
        print("1. 生成されたCSVファイルを確認")
        print("2. Streamlitダッシュボードを再実行")
        print("3. Tab3（ホテル・旅館特化）で宮古島市データを確認")
        
        # 生成されたファイル一覧
        print(f"\n📄 生成されたファイル:")
        for csv_file in sorted(output_dir.glob("long_*_hotel_breakdown.csv")):
            print(f"   {csv_file.name}")

if __name__ == "__main__":
    main()