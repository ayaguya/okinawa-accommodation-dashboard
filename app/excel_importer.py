# app/excel_importer.py
import sys
from pathlib import Path
import pandas as pd
from app.type_map import TYPE_MASTER, normalize_accommodation_type
from datetime import datetime

ROOT    = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

def extract_type(name: str) -> str:
    """
    宿泊種別の抽出と正規化
    
    Args:
        name (str): 入力された宿泊種別名
        
    Returns:
        str: 正規化された宿泊種別
    """
    return normalize_accommodation_type(name)

def tidy_sheet(df_raw: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Excelシートを整理し、必要なカラムのみを抽出
    
    Args:
        df_raw (pd.DataFrame): 元のデータフレーム
        year (int): 対象年
        
    Returns:
        pd.DataFrame: 整理されたデータフレーム
    """
    # カラム名の正規化
    df = df_raw.copy()
    df.columns = df.columns.str.strip()
    
    # 必要なカラムの抽出
    required_cols = ['年月', '宿泊種別', '宿泊者数', '宿泊施設数']
    df = df[required_cols]
    
    # 宿泊種別の正規化
    df['宿泊種別'] = df['宿泊種別'].apply(extract_type)
    
    # 数値カラムの型変換
    numeric_cols = ['宿泊者数', '宿泊施設数']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].fillna(0)
    
    # 日付カラムの型変換
    df['年月'] = pd.to_datetime(df['年月'], format='%Y-%m')
    
    # 不要な行の削除
    df = df.dropna(subset=['宿泊種別'])
    
    return df

def convert_excel(xlsx: Path, year: int) -> None:
    """
    Excelファイルを処理してCSVに変換
    
    Args:
        xlsx (Path): Excelファイルのパス
        year (int): 対象年
    """
    print(f"Processing: {xlsx}")
    df_raw = pd.read_excel(xlsx)
    df = tidy_sheet(df_raw, year)
    
    # CSVファイル名の生成
    csv_file = RAW_DIR / f"accommodation_{year}.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8')
    print(f"Saved to: {csv_file}")

def load_all_data() -> pd.DataFrame:
    """
    全てのCSVファイルからデータを読み込み、結合
    
    Returns:
        pd.DataFrame: 結合されたデータフレーム
    """
    all_data = []
    
    # 全てのCSVファイルを読み込む
    for csv_file in RAW_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            all_data.append(df)
        except Exception as e:
            print(f"Error reading {csv_file}: {str(e)}")
    
    if all_data:
        # 全てのデータを結合
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    else:
        raise ValueError("No data files found")

def get_latest_data() -> pd.DataFrame:
    """
    最新のデータを取得
    
    Returns:
        pd.DataFrame: 最新のデータ
    """
    df = load_all_data()
    latest_date = df['年月'].max()
    return df[df['年月'] == latest_date]

def get_trend_data() -> pd.DataFrame:
    """
    トレンドデータを取得（過去12ヶ月分）
    
    Returns:
        pd.DataFrame: トレンドデータ
    """
    df = load_all_data()
    latest_date = df['年月'].max()
    start_date = latest_date - pd.DateOffset(months=12)
    return df[(df['年月'] >= start_date) & (df['年月'] <= latest_date)]
    sheet = pd.ExcelFile(xlsx).parse("(1)市町村別・種別・規模別", header=3)
    tidy = tidy_sheet(sheet, year)
    out = RAW_DIR / f"survey_{year}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(out, index=False)
    print(f"✅ 生成: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m app.excel_importer <path/to/file.xlsx> <year>")
        sys.exit(1)

    xlsx_path = Path(sys.argv[1])
    try:
        year = int(sys.argv[2])
    except ValueError:
        print("Error: <year> must be an integer, e.g. 2023")
        sys.exit(1)

    convert_excel(xlsx_path, year)
