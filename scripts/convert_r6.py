# scripts/convert_r6.py
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/r6.xlsx")
OUT = Path("data/processed/by_year/long_2024.csv")
ALIASES = {"facilities": "軒数", "rooms": "客室数", "capacity": "収容人数"}

dfs = []
print(f"\n=== 開始: 2024年データ変換 ===")
print(f"入力ファイル: {RAW}")
print(f"出力ファイル: {OUT}")

for sheet in ["accommodation_type", "scale_class", "hotel_breakdown"]:
    print(f"\n=== シート処理: {sheet} ===")
    
    # シートの読み込み
    df = pd.read_excel(RAW, sheet_name=sheet, header=None)
    print(f"読み込み完了: 形状={df.shape}")
    
    # ヘッダ行を取得
    cat1 = df.iloc[0].fillna("")
    metric = df.iloc[1].fillna("")
    df.columns = [f"{a}/{b}" if b else a for a, b in zip(cat1, metric)]
    print(f"ヘッダ設定完了: 列数={len(df.columns)}")
    
    # データ部分を取得
    df = df.iloc[2:].reset_index(drop=True)
    print(f"データ部分取得: 形状={df.shape}")
    
    # 市町村列を取得
    city_col = [col for col in df.columns if 'city' in col.lower()][0]
    print(f"市町村列見つかり: {city_col}")
    df = df.rename(columns={city_col: "city"})
    
    # ロングフォーマットに変換
    df = df.melt(id_vars="city", var_name="col", value_name="value")
    df[["cat1", "metric", "cat2"]] = df["col"].str.split("/", expand=True).fillna("")
    print(f"ロングフォーマット変換: 形状={df.shape}")
    
    # メトリクスのマッピング
    df["metric"] = df["metric"].map(lambda x: next(k for k,v in ALIASES.items() if v==x) if x in ALIASES.values() else x)
    
    # 必要な列を追加
    df["table"] = sheet
    df["year"] = 2024
    
    # 必要な列のみを保持
    df_final = df[["year","city","table","cat1","cat2","metric","value"]]
    print(f"最終データ: 形状={df_final.shape}")
    dfs.append(df_final)

# データの結合と保存
result = pd.concat(dfs, ignore_index=True)
print(f"\n=== 結合結果 ===")
print(f"最終データ形状: {result.shape}")
print(f"ユニークな市町村数: {result['city'].nunique()}")
print(f"ユニークなメトリクス数: {result['metric'].nunique()}")

# CSV 保存
result.to_csv(OUT, index=False)
print(f"\n=== 完了 ===")
print(f"✅ 2024 CSV saved → {OUT}")
print(f"最終データ形状: {result.shape}")
