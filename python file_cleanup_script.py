import os
import shutil
from pathlib import Path

def cleanup_and_verify_files():
    """
    古いファイルを削除し、正しいファイルの存在を確認
    """
    
    by_year_dir = Path("data/processed/by_year")
    
    print("🧹 ファイル整理を開始します")
    
    # 現在のファイル状況を確認
    print(f"\n📁 {by_year_dir} の現在の内容:")
    if by_year_dir.exists():
        for file in sorted(by_year_dir.glob("*hotel_breakdown*.csv")):
            file_size = file.stat().st_size
            print(f"  📄 {file.name} ({file_size:,} bytes)")
    else:
        print("  ディレクトリが存在しません")
        return
    
    # 2024年のファイルを詳しく確認
    hotel_2024_files = list(by_year_dir.glob("*2024*hotel_breakdown*.csv"))
    
    if len(hotel_2024_files) > 1:
        print(f"\n⚠️ 2024年のhotel_breakdownファイルが複数あります:")
        for file in hotel_2024_files:
            print(f"  {file.name}")
        
        # ファイル内容を確認して正しいファイルを特定
        correct_file = None
        for file in hotel_2024_files:
            try:
                import pandas as pd
                df = pd.read_csv(file)
                miyako_total = df[
                    (df['city'] == '宮古島市') & 
                    (df['metric'] == 'facilities') & 
                    (df['cat1'] == 'total')
                ]['value']
                
                if not miyako_total.empty:
                    total_value = miyako_total.iloc[0]
                    print(f"    {file.name}: 宮古島市軒数 = {total_value}")
                    if total_value > 50:  # 正しい値は112
                        correct_file = file
                        print(f"    ✅ 正しいファイル: {file.name}")
                    else:
                        print(f"    ❌ 間違ったファイル: {file.name}")
            except Exception as e:
                print(f"    エラー: {file.name} - {e}")
        
        # 正しいファイルがある場合、他を削除
        if correct_file:
            target_name = "long_2024_hotel_breakdown.csv"
            target_path = by_year_dir / target_name
            
            for file in hotel_2024_files:
                if file != correct_file:
                    print(f"  🗑️ 削除: {file.name}")
                    file.unlink()
            
            # 正しいファイルを標準名にリネーム
            if correct_file.name != target_name:
                print(f"  📝 リネーム: {correct_file.name} → {target_name}")
                correct_file.rename(target_path)
    
    # 最終確認
    print(f"\n✅ 整理後のファイル:")
    for file in sorted(by_year_dir.glob("*hotel_breakdown*.csv")):
        try:
            import pandas as pd
            df = pd.read_csv(file)
            year = file.name.split('_')[1]
            miyako_total = df[
                (df['city'] == '宮古島市') & 
                (df['metric'] == 'facilities') & 
                (df['cat1'] == 'total')
            ]['value']
            
            if not miyako_total.empty:
                total_value = miyako_total.iloc[0]
                print(f"  📄 {file.name}: 宮古島市軒数 = {total_value}")
        except Exception as e:
            print(f"  📄 {file.name}: エラー - {e}")

def verify_data_structure():
    """
    データ構造が正しいかを確認
    """
    print(f"\n🔍 データ構造の検証")
    
    file_path = Path("data/processed/by_year/long_2024_hotel_breakdown.csv")
    
    if not file_path.exists():
        print("❌ long_2024_hotel_breakdown.csv が見つかりません")
        return
    
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        
        print(f"📊 総レコード数: {len(df)}")
        
        # 宮古島市のデータ確認
        miyako_data = df[df['city'] == '宮古島市']
        print(f"🏝️ 宮古島市レコード数: {len(miyako_data)}")
        
        # カテゴリ確認
        categories = sorted(df['cat1'].unique())
        print(f"📋 カテゴリ数: {len(categories)}")
        
        # 規模別とホテル種別の分離可能性を確認
        hotel_type_scale_categories = [cat for cat in categories if '_' in cat and cat != 'total']
        print(f"🏨 ホテル種別_規模カテゴリ: {len(hotel_type_scale_categories)}")
        
        # 期待される規模とホテル種別
        expected_hotel_types = ['resort_hotel', 'business_hotel', 'city_hotel', 'ryokan']
        expected_scales = ['large', 'medium', 'small']
        
        print(f"\n📈 宮古島市の2024年データ（軒数）:")
        facilities_data = miyako_data[miyako_data['metric'] == 'facilities'].sort_values('cat1')
        for _, row in facilities_data.iterrows():
            print(f"  {row['cat1']}: {row['value']}")
        
        # 正しいtotal値の確認
        total_facilities = miyako_data[
            (miyako_data['metric'] == 'facilities') & 
            (miyako_data['cat1'] == 'total')
        ]['value'].iloc[0]
        
        print(f"\n🎯 Total軒数: {total_facilities}")
        if total_facilities > 50:
            print("✅ データが正しく修正されています")
        else:
            print("❌ まだ間違ったデータです")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    cleanup_and_verify_files()
    verify_data_structure()
    
    print(f"\n📝 次のステップ:")
    print("1. Streamlitアプリを停止（Ctrl+C）")
    print("2. アプリを再起動: streamlit run okinawa_accommodation_dashboard.py")
    print("3. Tab3で宮古島市のデータを確認")