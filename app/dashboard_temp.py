import streamlit as st
import pandas as pd
import plotly.express as px
from app.utils import (
    load_survey_data,
    filter_data,
    create_bar_chart,
    create_trend_chart,
    create_heatmap,
    calculate_growth_rate,
    get_municipalities,
    get_accommodation_types,
    get_available_years,
    get_summary_stats
)
from app.type_map import METRICS

def main():
    st.set_page_config(
        page_title="沖縄県宿泊施設データ可視化ダッシュボード",
        page_icon="🏨",
        layout="wide"
    )
    
    # データの読み込み
    try:
        df = load_survey_data()
    except FileNotFoundError as e:
        st.error(str(e))
        return
    
    # データのサマリー表示
    stats = get_summary_stats(df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("データ年度数", stats["num_years"])
    with col2:
        st.metric("市町村数", stats["num_municipalities"])
    with col3:
        st.metric("宿泊種別数", stats["num_types"])
    with col4:
        st.metric("総軒数", f"{stats['total_facilities']:,}")
    
    # サイドバーのフィルタ設定
    st.sidebar.header("フィルタ設定")
    
    # 年度範囲スライダー
    available_years = get_available_years(df)
    min_year, max_year = st.sidebar.slider(
        "表示年度範囲",
        min_value=min(available_years),
        max_value=max(available_years),
        value=(min(available_years), max(available_years))
    )
    
    # 市町村選択
    municipalities = st.sidebar.multiselect(
        "市町村",
        options=get_municipalities(df),
        default=get_municipalities(df)
    )
    
    # 宿泊種別選択
    accommodation_types = st.sidebar.multiselect(
        "宿泊種別",
        options=get_accommodation_types(df),
        default=get_accommodation_types(df)
    )
    
    # 指標選択
    metric = st.sidebar.selectbox(
        "表示指標",
        options=list(METRICS.keys()),
        format_func=lambda x: METRICS[x]
    )
    
    # データのフィルタリング
    filtered_df = filter_data(
        df,
        municipalities=municipalities,
        accommodation_types=accommodation_types,
        start_year=min_year,
        end_year=max_year,
        metric=metric
    )
    
    # タブ式UI
    tab1, tab2, tab3 = st.tabs(["📊 概要", "📈 推移分析", "🗺️ 地域比較"])
    
    with tab1:
        st.header("📊 概要")
        
        # 市町村別棒グラフ
        st.subheader("市町村別宿泊施設数")
        if not filtered_df.empty:
            bar_fig = create_bar_chart(
                filtered_df,
                x="municipality",
                y=metric,
                title="市町村別宿泊施設数",
                color="accommodation_type"
            )
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
            st.warning("表示するデータがありません。フィルタ条件を調整してください。")
    
    with tab2:
        st.header("📈 推移分析")
        
        # 年次推移グラフ
        st.subheader("年次推移")
        if not filtered_df.empty:
            trend_fig = create_trend_chart(
                filtered_df,
                x="year",
                y=metric,
                title="年次推移",
                color="accommodation_type"
            )
            st.plotly_chart(trend_fig, use_container_width=True)
            
            # 成長率グラフ
            growth_df = calculate_growth_rate(filtered_df, metric)
            growth_fig = create_bar_chart(
                growth_df,
                x="year",
                y="growth_rate",
                title="年間成長率",
                color="accommodation_type"
            )
            st.plotly_chart(growth_fig, use_container_width=True)
        else:
            st.warning("表示するデータがありません。フィルタ条件を調整してください。")
    
    with tab3:
        st.header("🗺️ 地域比較")
        
        # ヒートマップ
        st.subheader("市町村別宿泊施設分布")
        if not filtered_df.empty:
            heatmap_fig = create_heatmap(
                filtered_df,
                x="year",
                y="municipality",
                z=metric,
                title="市町村別宿泊施設分布"
            )
            st.plotly_chart(heatmap_fig, use_container_width=True)
            
            # 上位/下位市町村ランキング
            st.subheader("ランキング")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("上位5市町村")
                top5 = filtered_df.groupby("municipality")[metric].sum().nlargest(5)
                st.dataframe(top5)
            
            with col2:
                st.subheader("下位5市町村")
                bottom5 = filtered_df.groupby("municipality")[metric].sum().nsmallest(5)
                st.dataframe(bottom5)
        else:
            st.warning("表示するデータがありません。フィルタ条件を調整してください。")

if __name__ == "__main__":
    main()
