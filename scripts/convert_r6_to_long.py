from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

# 定数定義
RAW = Path("data/raw/r6.xlsx")
OUT = Path("data/processed/by_year/long_2024.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

ALIAS = {"軒数": "facilities", "客室数": "rooms", "収容人数": "capacity"}
SHEETS = ["accommodation_type", "scale_class", "hotel_breakdown"]

# 市町村名の正規化辞書（必要に応じて追加）
CITY_NORMALIZATION = {
    "石垣": "石垣市",
    "竹富": "竹富町",
    "与那国": "与那国町",
    # 他の市町村名も必要に応じて追加
}


def ensure_city(df: pd.DataFrame) -> pd.DataFrame:
    """市町村列を city に統一"""
    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
    for c in df.columns:
        if str(c).strip().lower() in {"city", "municipality", "市町村"}:
            return df.rename(columns={c: "city"})
    return df.rename(columns={df.columns[0]: "city"})


def main():
    """メイン処理"""
    print("=== プロセス開始 ===")
    print(f"入力ファイル: {RAW}")
    print(f"出力ファイル: {OUT}")
    
    dfs = []
    
    for sheet in SHEETS:
        print(f"\n=== {sheet} の処理開始 ===")
        try:
            # データ読み込み（複数のヘッダー行に対応）
            df = pd.read_excel(RAW, sheet_name=sheet, header=[0, 1])
            print(f"  読み込み完了: 形状={df.shape}")
            
            # ヘッダフラット化
            df.columns = [b if b else a for a, b in df.columns]
            print(f"  ヘッダフラット化完了: 列数={len(df.columns)}")
            
            # city列の確保
            df = ensure_city(df)
            print(f"  city列設定完了")
            
            # データのピボット（ロング形式に変換）
            df = (df
                .melt(id_vars="city", var_name="col", value_name="value")
                .assign(table=sheet, year=2024)
                .pipe(lambda d: d.join(
                    d["col"].str.split("/", expand=True)
                        .rename(columns={0: "cat1", 1: "metric", 2: "cat2"})
                ))
            )
            
            # メトリクス名のマッピング
            df["metric"] = df["metric"].map(ALIAS).fillna(df["metric"])
            
            # データクリーニング
            df = df[df["cat1"] == "total"]  # cat1 が "total" のデータのみを保持
            df["cat1"] = "total"  # 一貫性のため明示的に設定
            
            # カラム名の変更
            df = df.rename(columns={"city": "municipality"})
            
            # areaカラムの追加（全て未分類として扱う）
            df['area'] = '未分類'
            
            # 必要な列のみを選択
            df_final = df[["year", "municipality", "area", "table", "cat1", "cat2", "metric", "value"]]
            
            # データのソート
            df_final = df_final.sort_values(["year", "municipality", "table", "metric"])
            
            print(f"  処理完了: 最終形状={df_final.shape}")
            dfs.append(df_final)
            
        except Exception as e:
            print(f"  エラー: {sheet} の処理中にエラーが発生しました")
            print(f"  詳細: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # 結果の結合と保存
    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        # 重複の削除
        result = result.drop_duplicates()
        # CSVとして保存
        result.to_csv(OUT, index=False, encoding='utf-8')
        print(f"\n=== 完了 ===")
        print(f"✅ 2024 CSV saved → {OUT}")
        print(f"最終データ形状: {result.shape}")
    else:
        print("\nエラー: どのシートも正常に処理できませんでした")

if __name__ == "__main__":
    main()
