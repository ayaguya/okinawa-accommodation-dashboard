from pathlib import Path
import pandas as pd

# ファイルパスの設定
LONG_2024 = Path("data/processed/by_year/long_2024.csv")
ALL_YEARS = Path("data/processed/all/all_years_long.csv")

# 2024年のデータを読み込み
print("=== 2024年データの読み込み ===")
df_2024 = pd.read_csv(LONG_2024)
print(f"2024年データ形状: {df_2024.shape}")

# 全年度データを読み込み（存在する場合）
print("\n=== 全年度データの読み込み ===")
if ALL_YEARS.exists():
    df_all = pd.read_csv(ALL_YEARS)
    print(f"既存データ形状: {df_all.shape}")
else:
    df_all = pd.DataFrame()
    print("既存データが見つかりません")

# データの結合
print("\n=== データの結合 ===")
df_combined = pd.concat([df_all, df_2024], ignore_index=True)
print(f"結合後データ形状: {df_combined.shape}")

# 重複の削除（必要に応じて）
df_combined = df_combined.drop_duplicates()

# ソート
df_combined = df_combined.sort_values(by=["year", "municipality", "table", "metric"])

# 保存
print("\n=== 保存 ===")
df_combined.to_csv(ALL_YEARS, index=False)
print(f"✅ 全年度データを更新しました: {ALL_YEARS}")
print(f"最終データ形状: {df_combined.shape}")

# データの要約表示
print("\n=== データ要約 ===")
print(f"期間: {df_combined['year'].min()}〜{df_combined['year'].max()}")
print(f"市町村数: {df_combined['municipality'].nunique()}")
print(f"メトリクス数: {df_combined['metric'].nunique()}")
