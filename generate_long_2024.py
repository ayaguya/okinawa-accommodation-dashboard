import pandas as pd
from pathlib import Path

# データディレクトリの設定
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed/by_year")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# r6.xlsx の読み込み
xlsx_path = RAW_DIR / "r6.xlsx"
df = pd.read_excel(xlsx_path, sheet_name="accommodation_type")

# データの正規化
# 1. 列名の正規化
df.columns = df.columns.str.strip().str.lower()

# 2. 市町村名の正規化
df["city"] = df["city"].astype(str).str.strip()

# 3. 数値の正規化
for col in ["facilities", "rooms", "capacity"]:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(r"[,　\s]", "", regex=True)
            .str.replace("－", "0")
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0)
            .astype(int)
        )

# 4. 年度の正規化（2024年固定）
df["year"] = 2024

# 5. 必要な列のみを残す
df = df[["city", "year", "facilities", "rooms", "capacity"]]

# 6. ロングフォーマットに変換
long_df = df.melt(
    id_vars=["city", "year"],
    value_vars=["facilities", "rooms", "capacity"],
    var_name="metric",
    value_name="value"
)

# 7. カテゴリ情報の追加
long_df["table"] = "pref_transition"
long_df["cat1"] = "total"
long_df["cat2"] = ""

# 8. 列の順序を調整
long_df = long_df[["city", "year", "table", "cat1", "cat2", "metric", "value"]]

# CSV 保存
output_path = PROCESSED_DIR / "long_2024.csv"
long_df.to_csv(output_path, index=False, encoding="utf-8")

print(f"Successfully saved to {output_path}")
