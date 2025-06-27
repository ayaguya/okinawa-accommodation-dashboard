"""convert_excel_to_long.py
====================================
Excel (H/R 番号付きファイル) → ロング CSV 変換ツール
----------------------------------------------------
対応フォーマット
* ファイル名例: `r6.xlsx` (令和6年), `r5.xlsx`, `h30.xlsx` …
* 対象シート : accommodation_type / scale_class / hotel_breakdown
* 各シートは 2 行ヘッダ (cat1, metric) + データ行
* 出力列順    : municipality,value,0,1,cat1,metric,cat2,table,year
  0,1 は melt 前ヘッダ (cat1/metric) のバックアップ

使い方例:
$ python scripts/convert_excel_to_long.py data/raw/r6.xlsx
"""
import sys
import re
from pathlib import Path
import pandas as pd

# -------------------------------------------------------
SHEETS = [
    "accommodation_type",
    "scale_class",
    "hotel_breakdown",
]
ALIAS = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}

# -------------------------------------------------------
# ヘルパ
# -------------------------------------------------------

def guess_year_from_filename(fn: str) -> int:
    """r6.xlsx → 2024, h30.xlsx → 2018 のように和暦タグを西暦に変換"""
    tag = Path(fn).stem.lower()
    m = re.match(r"([shr])(\d{1,2})", tag)
    if not m:
        raise ValueError("ファイル名に和暦タグ(s/h/r)が見つかりません")
    era, num = m.groups()
    num = int(num)
    return {"s": 1925 + num, "h": 1988 + num, "r": 2018 + num}[era]


def _flatten_columns(mi) -> list[str]:
    """2 レベル MultiIndex をフラット化。
    * `Unnamed*` / 空セル / NaN は無視
    * 子が空なら親だけ、両方あれば `parent/child`
    """
    flat: list[str] = []
    for parent, child in mi:
        parent = "" if pd.isna(parent) else str(parent).strip()
        child  = "" if pd.isna(child)  else str(child).strip()
        if re.match(r"^Unnamed", parent, re.I):
            parent = ""
        if re.match(r"^Unnamed", child, re.I):
            child = ""
        flat.append(f"{parent}/{child}" if child else parent)
    return flat


def ensure_municipality(df: pd.DataFrame) -> pd.DataFrame:
    """市町村列を `municipality` に統一。

    改良ポイント
    -------------
    1. `index` 列を先に判定 – 数値なら捨て、文字列なら採用。
    2. 候補名 (municipality/city/市町村/"")、かつ **非数値型** を優先。
    3. 無ければ最初の **object 型** 列を採用。
    4. どうしても無い場合のみ最左列を強制採用。
    """

    # 1) reset_index() で出来た列の処理
    if "index" in df.columns:
        if pd.api.types.is_numeric_dtype(df["index"]):
            df = df.drop(columns=["index"])
        else:
            df = df.rename(columns={"index": "municipality"})

    # 2) すでに municipality 決定済み？
    if "municipality" in df.columns:
        return df

    cand = {"municipality", "city", "市町村", ""}
    for col in df.columns:
        if (str(col).strip().lower() in cand) and not pd.api.types.is_numeric_dtype(df[col]):
            df = df.rename(columns={col: "municipality"})
            break
    else:
        # object 型列のどれか
        obj_cols = [c for c in df.columns if df[c].dtype == "object"]
        if obj_cols:
            df = df.rename(columns={obj_cols[0]: "municipality"})
        else:
            # 最後の砦
            df = df.rename(columns={df.columns[0]: "municipality"})

    return df


def process_sheet(xlsx: Path, sheet: str, year: int) -> pd.DataFrame:
    """単一シート → ロング形式 DataFrame"""

    # ① 2 行ヘッダ読み込み
    df = pd.read_excel(xlsx, sheet_name=sheet, header=[0, 1])

    # ② 行ラベル(index) → 列へ
    df = df.reset_index()

    # ③ ヘッダをフラット化（Unnamed* を除去）
    df.columns = _flatten_columns(df.columns)

    # ④ 市町村名列の決定
    df = ensure_municipality(df)

    # ⑤ ロング化
    long = df.melt(id_vars="municipality", var_name="col", value_name="value")

    # ⑥ cat 展開 (必ず 3 列に揃える)
    cat = long["col"].str.split("/", expand=True)
    while cat.shape[1] < 3:
        cat[cat.shape[1]] = ""
    cat = cat.iloc[:, :3].rename(columns={0: "cat1", 1: "metric", 2: "cat2"})
    long = pd.concat([long, cat], axis=1).drop(columns="col")

    long["metric"] = long["metric"].map(ALIAS).fillna(long["metric"])
    long["table"] = sheet
    long["year"]  = year

    # デバッグ用バックアップ
    long["0"] = long["cat1"]
    long["1"] = long["metric"]

    cols = [
        "municipality",
        "value",
        "0",
        "1",
        "cat1",
        "metric",
        "cat2",
        "table",
        "year",
    ]
    return long[cols]


def main(xlsx_path: str):
    src = Path(xlsx_path)
    if not src.exists():
        sys.exit(f"❌ {src} not found")

    year = guess_year_from_filename(src.name)
    out = Path(f"data/processed/by_year/long_{year}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    dfs = [process_sheet(src, sh, year) for sh in SHEETS]
    result = pd.concat(dfs, ignore_index=True)
    result.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"✅ saved → {out}  ({result.shape[0]:,} rows)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_excel_to_long.py data/raw/r6.xlsx")
        sys.exit(1)
    main(sys.argv[1])
