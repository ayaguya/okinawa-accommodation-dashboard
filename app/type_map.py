TYPE_MASTER = {
    "リゾートホテル":            "リゾートホテル",
    "ビジネス・宿泊特化型ホテル": "ビジネス・宿泊特化型ホテル",
    "シティーホテル":            "シティーホテル",
    "旅館":                     "旅館",
    "民宿":                     "民宿",
    "ペンション・貸別荘":        "ペンション・貸別荘",
    "ドミトリー・ゲストハウス":   "ドミトリー・ゲストハウス",
    "ウィークリーマンション":      "ウィークリーマンション",
    "団体経営施設":              "団体経営施設",
    "ユースホステル":            "ユースホステル",
    "その他":                   "その他"
}

def normalize_accommodation_type(accommodation_type: str) -> str:
    """
    宿泊種別の正規化処理
    
    Args:
        accommodation_type (str): 入力された宿泊種別
        
    Returns:
        str: 正規化された宿泊種別
    """
    # 大文字小文字を統一
    normalized_type = accommodation_type.strip().lower()
    
    # マスタに存在する場合はそのまま返す
    if normalized_type in TYPE_MASTER:
        return TYPE_MASTER[normalized_type]
        
    # 類似表現のマッピング
    similar_patterns = {
        "ホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネス": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル",
        "ビジネスホテル": "ビジネス・宿泊特化型ホテル"
    }
    
    # 類似パターンのマッチング
    for pattern, mapped_type in similar_patterns.items():
        if pattern in normalized_type:
            return mapped_type
            
    # マスタにない場合は「その他」にマッピング
    return "その他"
