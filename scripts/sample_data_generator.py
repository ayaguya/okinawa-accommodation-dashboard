"""
テスト用サンプルデータを生成するスクリプト
"""

import pandas as pd
import numpy as np
from pathlib import Path
from app.type_map import (
    TYPE_MASTER, METRICS, YEARS, normalize_accommodation_type,
    normalize_metric, normalize_year, normalize_municipality
)

# データ生成設定
SAMPLE_DATA_DIR = Path("../data/sample")
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 市町村リスト（主要な市町村のみ）
SAMPLE_MUNICIPALITIES = [
    "那覇市", "宜野湾市", "石垣市", "浦添市", "沖縄市",
    "うるま市", "名護市", "糸満市", "宮古島市"
]

# 宿泊種別リスト
SAMPLE_TYPES = list(TYPE_MASTER.keys())

# 年度範囲
SAMPLE_YEARS = list(YEARS.values())

# データ生成関数
def generate_sample_data():
    """
    テスト用サンプルデータを生成
    """
    # データフレームの初期化
    data = []
    
    # 各年度、市町村、宿泊種別に対してデータ生成
    for year in SAMPLE_YEARS:
        for municipality in SAMPLE_MUNICIPALITIES:
            for accommodation_type in SAMPLE_TYPES:
                # データ生成のパターン
                base_value = np.random.randint(1, 100)
                
                # 軒数
                facilities = base_value * np.random.randint(1, 5)
                
                # 客室数（軒数の2-5倍程度）
                rooms = facilities * np.random.randint(2, 5)
                
                # 収容人数（客室数の2-4倍程度）
                capacity = rooms * np.random.randint(2, 4)
                
                # 民泊届出数（宿泊種別による）
                minpaku = 0
                if accommodation_type == "民泊":
                    minpaku = facilities * np.random.randint(1, 3)
                
                # データ追加
                data.append({
                    "year": year,
                    "municipality": municipality,
                    "accommodation_type": accommodation_type,
                    "facilities": facilities,
                    "rooms": rooms,
                    "capacity": capacity,
                    "minpaku_registrations": minpaku
                })
    
    # データフレーム作成
    df = pd.DataFrame(data)
    
    # データ保存
    output_file = SAMPLE_DATA_DIR / "sample_accommodation_data.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"サンプルデータを生成しました: {output_file}")
    
    return df

def main():
    """メイン関数"""
    print("=== テスト用サンプルデータ生成スクリプト ===")
    
    # サンプルデータ生成
    df = generate_sample_data()
    
    # 基本統計量の表示
    print("\n=== サンプルデータの基本統計量 ===")
    print("\nデータ件数:", len(df))
    print("\n各年度のデータ件数:")
    print(df['year'].value_counts().sort_index())
    print("\n各市町村のデータ件数:")
    print(df['municipality'].value_counts())
    print("\n各宿泊種別のデータ件数:")
    print(df['accommodation_type'].value_counts())
    
    # 各指標の統計量
    print("\n=== 各指標の統計量 ===")
    metrics = ['facilities', 'rooms', 'capacity', 'minpaku_registrations']
    for metric in metrics:
        print(f"\n{metric}:")
        print(df[metric].describe())

if __name__ == "__main__":
    main()
