"""
沖縄県宿泊施設種別マスタデータ
Accommodation type master data for Okinawa Prefecture
"""

# 宿泊種別マスタ
TYPE_MASTER = {
    "ホテル": "hotel",
    "旅館": "ryokan",
    "簡易宿所": "simple_accommodation",
    "下宿": "boarding_house",
    "民泊": "minpaku",
    "その他": "others"
}

# 宿泊種別表示名
TYPE_DISPLAY_NAMES = {
    "hotel": "ホテル",
    "ryokan": "旅館",
    "simple_accommodation": "簡易宿所",
    "boarding_house": "下宿",
    "minpaku": "民泊",
    "others": "その他"
}

# 指標マスタ
METRICS = {
    "facilities": "軒数",
    "rooms": "客室数",
    "capacity": "収容人数",
    "minpaku_registrations": "民泊届出数"
}

# 指標表示名
METRIC_DISPLAY_NAMES = {
    "facilities": "軒数",
    "rooms": "客室数",
    "capacity": "収容人数",
    "minpaku_registrations": "民泊届出数"
}

# 年度マスタ（平成19年～令和5年）
YEARS = {
    "平成19年": 2007,
    "平成20年": 2008,
    "平成21年": 2009,
    "平成22年": 2010,
    "平成23年": 2011,
    "平成24年": 2012,
    "平成25年": 2013,
    "平成26年": 2014,
    "平成27年": 2015,
    "平成28年": 2016,
    "平成29年": 2017,
    "平成30年": 2018,
    "令和元年": 2019,
    "令和2年": 2020,
    "令和3年": 2021,
    "令和4年": 2022,
    "令和5年": 2023
}

# 年度表示用逆マップ
YEAR_DISPLAY_NAMES = {v: k for k, v in YEARS.items()}

# 年度範囲定義
def get_year_range(start_year: str = "平成19年", end_year: str = "令和5年") -> tuple[int, int]:
    """
    年度範囲を取得
    
    Args:
        start_year (str): 開始年度（例: "平成19年"）
        end_year (str): 終了年度（例: "令和5年"）
        
    Returns:
        tuple[int, int]: (開始年, 終了年)
    """
    start = YEARS.get(start_year, min(YEARS.values()))
    end = YEARS.get(end_year, max(YEARS.values()))
    return start, end

# 宿泊種別正規化関数
def normalize_accommodation_type(accommodation_type: str) -> str:
    """
    宿泊種別の正規化処理
    
    Args:
        accommodation_type (str): 入力された宿泊種別
        
    Returns:
        str: 正規化された宿泊種別（英語表記）
    """
    if not accommodation_type:
        return "others"
    
    # 文字列の前後の空白を削除
    normalized_type = accommodation_type.strip()
    
    # マスタに存在する場合はそのまま返す
    if normalized_type in TYPE_MASTER:
        return TYPE_MASTER[normalized_type]
        
    # 類似表現のパターンマッチング
    similar_patterns = {
        "ホテル": "hotel",
        "旅館": "ryokan",
        "簡易宿所": "simple_accommodation",
        "下宿": "boarding_house",
        "民泊": "minpaku"
    }
    
    # 大文字小文字を統一して比較
    normalized_type_lower = normalized_type.lower()
    for pattern, mapped_type in similar_patterns.items():
        if pattern.lower() in normalized_type_lower:
            return mapped_type
            
    # マスタにない場合は「その他」にマッピング
    return "others"

# 指標名正規化関数
def normalize_metric(metric: str) -> str:
    """
    指標名の正規化処理
    
    Args:
        metric (str): 入力された指標名
        
    Returns:
        str: 正規化された指標名（英語表記）
    """
    if not metric:
        return "facilities"
    
    # 文字列の前後の空白を削除
    normalized_metric = metric.strip()
    
    # マスタに存在する場合はそのまま返す
    if normalized_metric in METRIC_DISPLAY_NAMES:
        return METRIC_DISPLAY_NAMES[normalized_metric]
        
    # 類似表現のパターンマッチング
    similar_patterns = {
        "軒数": "facilities",
        "客室数": "rooms",
        "収容人数": "capacity",
        "民泊届出数": "minpaku_registrations"
    }
    
    # 大文字小文字を統一して比較
    normalized_metric_lower = normalized_metric.lower()
    for pattern, mapped_metric in similar_patterns.items():
        if pattern.lower() in normalized_metric_lower:
            return mapped_metric
            
    # マスタにない場合は「軒数」にマッピング
    return "facilities"

# 年度正規化関数
def normalize_year(year: str) -> int:
    """
    年度の正規化処理
    
    Args:
        year (str): 入力された年度（例: "平成19年", "2007"）
        
    Returns:
        int: 正規化された西暦
    """
    if not year:
        return min(YEARS.values())
    
    # 文字列の前後の空白を削除
    normalized_year = year.strip()
    
    # 数値のみの場合
    if normalized_year.isdigit():
        return int(normalized_year)
        
    # 年度表記の場合
    if normalized_year in YEARS:
        return YEARS[normalized_year]
        
    # 類似パターンのパターンマッチング
    for year_pattern, year_value in YEARS.items():
        if year_pattern in normalized_year:
            return year_value
            
    # マスタにない場合は最小年度にマッピング
    return min(YEARS.values())

# 市町村名正規化関数
def normalize_municipality(municipality: str) -> str:
    """
    市町村名の正規化処理
    
    Args:
        municipality (str): 入力された市町村名
        
    Returns:
        str: 正規化された市町村名
    """
    if not municipality:
        return "沖縄県その他"
    
    # 文字列の前後の空白を削除
    normalized_municipality = municipality.strip()
    
    # 市町村マスタに存在する場合はそのまま返す
    if normalized_municipality in MUNICIPALITIES:
        return normalized_municipality
        
    # 類似パターンのパターンマッチング
    for m in MUNICIPALITIES:
        if m.lower() in normalized_municipality.lower():
            return m
            
    # マスタにない場合は「沖縄県その他」にマッピング
    return "沖縄県その他"

# 市町村マスタ（沖縄県の市町村）
MUNICIPALITIES = [
    "那覇市", "宜野湾市", "石垣市", "浦添市", "名護市", "糸満市", "沖縄市", "豊見城市",
    "うるま市", "宮古島市", "南城市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町",
    "恩納村", "宜野座村", "金武町", "伊江村", "読谷村", "嘉手納町", "北谷町", "北中城村",
    "中城村", "西原町", "与那原町", "南風原町", "久米島町", "八重瀬町", "多良間村",
    "竹富町", "与那国町"
]

# エリアマスタ（沖縄県のエリア区分）
AREAS = {
    "南部": [
        "那覇市", "糸満市", "豊見城市", "八重瀬町", "南城市", "与那原町", "南風原町"
    ],
    "中部": [
        "沖縄市", "宜野湾市", "浦添市", "うるま市", "読谷村", "嘉手納町", "北谷町",
        "北中城村", "中城村", "西原町"
    ],
    "北部": [
        "名護市", "国頭村", "大宜味村", "東村", "今帰仁村", "本部町", "恩納村",
        "宜野座村", "金武町"
    ],
    "宮古": [
        "宮古島市", "多良間村"
    ],
    "八重山": [
        "石垣市", "竹富町", "与那国町"
    ],
    "離島": [
        "久米島町", "渡嘉敷村", "座間味村", "粟国村", "渡名喜村", "南大東村",
        "北大東村", "伊江村", "伊平屋村", "伊是名村"
    ]
}

# エリア表示名
AREA_DISPLAY_NAMES = {
    "南部": "南部エリア",
    "中部": "中部エリア",
    "北部": "北部エリア",
    "宮古": "宮古エリア",
    "八重山": "八重山エリア",
    "離島": "離島エリア"
}
