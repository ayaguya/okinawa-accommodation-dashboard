"""
沖縄県宿泊施設データ処理ユーティリティ
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from app.type_map import (
    METRICS, TYPE_MASTER, TYPE_DISPLAY_NAMES, METRIC_DISPLAY_NAMES,
    MUNICIPALITIES, YEARS, YEAR_DISPLAY_NAMES
)

# データ品質チェック関数
def validate_data(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    データ品質チェックを実行
    
    Args:
        df: データフレーム
        
    Returns:
        Dict[str, List[str]]: エラー項目とその詳細
    """
    errors = {
        'missing_values': [],
        'invalid_types': [],
        'outliers': [],
        'inconsistencies': []
    }
    
    # 欠損値チェック
    missing = df.isnull().sum()
    for col in df.columns:
        if missing[col] > 0:
            errors['missing_values'].append(f"{col}: {missing[col]}件の欠損値")
    
    # 数値型チェック
    numeric_cols = ['facilities', 'rooms', 'capacity', 'minpaku_registrations']
    for col in numeric_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            errors['invalid_types'].append(f"{col}: 数値型ではありません")
    
    # 外れ値チェック
    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        if not outliers.empty:
            errors['outliers'].append(f"{col}: {len(outliers)}件の外れ値")
    
    # 一貫性チェック
    if df['year'].min() < 2007 or df['year'].max() > 2023:
        errors['inconsistencies'].append("年度範囲が不正です")
    
    return errors

# データ読み込み関数
def load_survey_data(
    data_dir: Path = Path("../data/processed"),
    validate: bool = True
) -> pd.DataFrame:
    """
    複数のCSVファイルからデータを読み込み、結合する
    
    Args:
        data_dir: CSVファイルが格納されているディレクトリ
        validate: データ品質チェックを実行するかどうか
        
    Returns:
        pd.DataFrame: 統合されたデータフレーム
        
    Raises:
        FileNotFoundError: データファイルが見つからない場合
        ValueError: データ品質チェックに失敗した場合
    """
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError("データファイルが見つかりません。Excelファイルを変換してください。")
    
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        dfs.append(df)
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # データ品質チェック
    if validate:
        errors = validate_data(combined_df)
        if any(errors.values()):
            error_msg = "データ品質チェックに失敗しました:\n"
            for key, items in errors.items():
                if items:
                    error_msg += f"\n{key}:\n" + "\n".join(items)
            raise ValueError(error_msg)
    
    return combined_df

# 高度なデータフィルタリング関数
def filter_data(
    df: pd.DataFrame,
    municipalities: Optional[List[str]] = None,
    accommodation_types: Optional[List[str]] = None,
    year_range: Optional[Tuple[int, int]] = None,
    metric: Optional[str] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> pd.DataFrame:
    """
    高度なデータフィルタリング
    
    Args:
        df: 元のデータフレーム
        municipalities: 対象の市町村リスト
        accommodation_types: 対象の宿泊種別リスト
        year_range: 年度範囲（開始年, 終了年）
        metric: 指標名
        min_value: 最小値フィルタ
        max_value: 最大値フィルタ
        
    Returns:
        フィルタリングされたデータフレーム
    """
    filtered = df.copy()
    
    # 市町村フィルタ
    if municipalities:
        filtered = filtered[filtered['municipality'].isin(municipalities)]
    
    # 宿泊種別フィルタ
    if accommodation_types:
        filtered = filtered[filtered['accommodation_type'].isin(accommodation_types)]
    
    # 年度範囲フィルタ
    if year_range:
        start_year, end_year = year_range
        filtered = filtered[(filtered['year'] >= start_year) & (filtered['year'] <= end_year)]
    
    if metric:
        if min_value is not None:
            filtered = filtered[filtered[metric] >= min_value]
        if max_value is not None:
            filtered = filtered[filtered[metric] <= max_value]
    
    return filtered

def create_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = None,
    barmode: str = 'group',
    labels: Dict[str, str] = None
) -> go.Figure:
    """Create customizable bar chart"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle'
        )
        return fig
    
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        barmode=barmode,
        labels=labels or {x: x, y: y}
    )
    
    fig.update_layout(
        font_family="Arial Unicode MS",
        title_font_size=20,
        xaxis_title_font_size=16,
        yaxis_title_font_size=16,
        height=500
    )
    
    return fig

def create_trend_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str = None,
    labels: Dict[str, str] = None
) -> go.Figure:
    """Create trend line chart"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle'
        )
        return fig
    
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        labels=labels or {x: x, y: y}
    )
    
    fig.update_layout(
        font_family="Arial Unicode MS",
        title_font_size=20,
        xaxis_title_font_size=16,
        yaxis_title_font_size=16,
        height=400
    )
    
    return fig

def create_heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: str,
    labels: Dict[str, str] = None
) -> go.Figure:
    """Create heatmap"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle'
        )
        return fig
    
    # Pivot data for heatmap
    heatmap_data = df.pivot(index=y, columns=x, values=z)
    
    fig = px.imshow(
        heatmap_data,
        labels=labels or {"x": x, "y": y, "color": z},
        aspect="auto",
        title=title
    )
    
    fig.update_layout(
        font_family="Arial Unicode MS",
        title_font_size=20,
        height=600
    )
    
    return fig

def create_comparison_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: str,
    labels: Dict[str, str] = None
) -> go.Figure:
    """Create comparison chart"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle'
        )
        return fig
    
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        labels=labels or {x: x, y: y}
    )
    
    fig.update_layout(
        font_family="Arial Unicode MS",
        title_font_size=20,
        xaxis_title_font_size=16,
        yaxis_title_font_size=16,
        height=400
    )
    
    return fig

def calculate_growth_rate(
    df: pd.DataFrame,
    metric: str,
    group_by: List[str] = ['municipality', 'accommodation_type']
) -> pd.DataFrame:
    """Calculate year-over-year growth rate"""
    if df.empty:
        return pd.DataFrame()
    
    df = df.sort_values(['year'] + group_by)
    df['growth_rate'] = df.groupby(group_by)[metric].pct_change()
    df['growth_rate_color'] = df['growth_rate'].apply(
        lambda x: 'red' if x < 0 else 'green'
    )
    
    return df

def get_municipalities(df: pd.DataFrame) -> List[str]:
    """Get list of unique municipalities"""
    if df.empty:
        return []
    
    return sorted(df['municipality'].unique())

def get_accommodation_types(df: pd.DataFrame) -> List[str]:
    """Get list of unique accommodation types"""
    if df.empty:
        return []
    
    return sorted(df['accommodation_type'].unique())

def get_year_range(df: pd.DataFrame) -> Tuple[int, int]:
    """Get min and max years from data"""
    if df.empty:
        return (2007, 2023)
    
    return int(df['year'].min()), int(df['year'].max())

def get_metrics() -> List[str]:
    """Get list of available metrics"""
    return list(METRICS.keys())

def get_data_quality_report(df: pd.DataFrame) -> Dict:
    """Generate data quality report"""
    if df.empty:
        return {
            "status": "empty",
            "message": "データがありません",
            "details": {}
        }
    
    report = {
        "status": "ok",
        "message": "データ品質チェックが完了しました",
        "details": {
            "total_records": len(df),
            "year_range": f"{df['year'].min()} - {df['year'].max()}",
            "municipalities": len(df['municipality'].unique()),
            "accommodation_types": len(df['accommodation_type'].unique()),
            "missing_data": {}
        }
    }
    
    # Check for missing data
    for col in df.columns:
        missing_count = df[col].isna().sum()
        missing_pct = (missing_count / len(df)) * 100
        report["details"]["missing_data"][col] = {
            "count": missing_count,
            "percentage": round(missing_pct, 2)
        }
    
    return report

def export_data(df: pd.DataFrame, filename: str = "accommodation_data.csv") -> None:
    """Export data to CSV"""
    if df.empty:
        raise ValueError("データがありません")
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"データを {filename} にエクスポートしました")

def get_summary_stats(df: pd.DataFrame, group_by: List[str] = ['municipality', 'accommodation_type']) -> pd.DataFrame:
    """Calculate summary statistics"""
    if df.empty:
        return pd.DataFrame()
    
    metrics = list(METRICS.keys())
    summary = df.groupby(group_by)[metrics].agg([
        "count", "mean", "median", "std", "min", "max", "sum"
    ]).round(2)
    
    summary.columns = pd.MultiIndex.from_tuples([
        (f"{metric}_{stat}", f"{METRICS[metric]}_{stat}")
        for metric in metrics
        for stat in ["count", "mean", "median", "std", "min", "max", "sum"]
    ])
    
    return summary.reset_index()
