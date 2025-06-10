# app/excel_importer.py
from pathlib import Path
import pandas as pd
from app.type_map import TYPE_MASTER

ROOT    = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"              # Excel も CSV もここに置く

def extract_type(name: str) -> str:
    """行見出し(例: 'リゾートホテル(大規模)')から種別を返す"""
    for key in TYPE_MASTER:
        if key in name:
            return TYPE_MASTER[key]
    return "その他"

def tidy_sheet(df_raw: pd.DataFrame, year: int) -> pd.DataFrame:
    df = df_raw.copy()
    df.iloc[:, :3] = df.iloc[:, :3].ffill()   # 地域・市町村前方埋め
    df = df.rename(columns={df.columns[0]: "地域", df.columns[2]: "市町村"})

    # ── 種別・規模列を抽出 ─────────────────────────
    df["宿泊種別"] = df.iloc[:, 3].map(extract_type)
    df["規模"]   = df.iloc[:, 3].str.extract(r"（(.+?)）")[0].fillna("総計")

    # ── 必要列だけ残す ───────────────────────────
    col_map = {"軒数": "軒数", "客 室 数": "客室数", "収容\n人数": "収容人数"}
    df = df[list(col_map.keys()) + ["地域", "市町村", "宿泊種別", "規模"]]

    # ── ワイド→ロング ───────────────────────────
    tidy = (df.rename(columns=col_map)
              .melt(id_vars=["地域", "市町村", "宿泊種別", "規模"],
                    var_name="指標", value_name="値"))
    tidy["年"]  = year
    tidy["値"] = (tidy["値"].astype(str)
                            .str.replace(",", "")
                            .replace("", 0)
                            .astype("Int64"))
    return tidy[["地域", "市町村", "年", "宿泊種別", "規模", "指標", "値"]]

def convert_excel(xlsx: Path):
    year = int(xlsx.stem.split("r")[1][:2]) + 2018  # R5 → 2023
    sheet = (pd.ExcelFile(xlsx)
               .parse("(1)市町村別・種別・規模別", header=3))
    tidy = tidy_sheet(sheet, year)
    out = RAW_DIR / f"survey_{year}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(out, index=False)
    print(f"✅ 生成: {out}")

if __name__ == "__main__":
    # Excel ファイル名を適宜書き換えてください
    convert_excel(RAW_DIR / "沖縄県宿泊施設実態調査推移.xlsx")

