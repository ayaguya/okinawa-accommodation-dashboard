"""
沖縄県宿泊施設データ可視化ダッシュボード
Okinawa Accommodation Facility Data Visualization Dashboard
"""
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils import (
    load_survey_data, filter_data, create_bar_chart, create_trend_chart,
    get_municipalities, get_accommodation_types, get_year_range,
    create_heatmap, create_comparison_chart, calculate_growth_rate
)
from type_map import METRICS

def main():
    st.set_page_config(
        page_title="沖縄県宿泊施設データ可視化",
        page_icon="\U0001F3E8",
        layout="wide"
    )

    st.title("\U0001F3E8 沖縄県宿泊施設データ可視化ダッシュボード")
    st.markdown("**Okinawa Accommodation Facility Data Visualization Dashboard**")

    # Load data
    data = load_survey_data()

    if data.empty:
        st.warning("\u26a0\ufe0f データが見つかりません。data/processed/ディレクトリにsurvey_*.csvファイルを配置してください。")
        st.info("データが準備できていない場合は、Excel ファイルをインポートしてください。")

        # Show data import section
        with st.expander("\U0001F4E5 データインポート手順"):
            st.markdown("""
            ### データ準備手順:
            1. **Excelファイル配置**: `data/raw/excel/` フォルダに沖縄県のExcelファイルを配置
            2. **変換実行**: `python scripts/convert_all_excel.py` を実行
            3. **ダッシュボード再読み込み**: ブラウザを更新

            ### サンプルデータ生成:
            ```bash
            python scripts/sample_data_generator.py
            ```
            """)
        return

    # Sidebar filters
    st.sidebar.header("\U0001F4CA フィルター設定")

    municipalities = get_municipalities(data)
    selected_municipality = st.sidebar.selectbox("市町村を選択:", municipalities, index=0)

    accommodation_types = get_accommodation_types(data)
    selected_type = st.sidebar.selectbox("宿泊種別を選択:", accommodation_types, index=0)

    year_range = get_year_range(data)
    if len(year_range) > 1:
        start_year, end_year = st.sidebar.select_slider("年度範囲を選択:", options=year_range, value=(min(year_range), max(year_range)))
    else:
        start_year = end_year = year_range[0] if year_range else 2023

    metric_key = st.sidebar.selectbox("表示指標を選択:", list(METRICS.keys()), format_func=lambda x: METRICS[x])

    filtered_data = filter_data(
        data,
        municipality=selected_municipality if selected_municipality != "全体" else None,
        accommodation_type=selected_type if selected_type != "全体" else None,
        start_year=start_year,
        end_year=end_year
    )

    if filtered_data.empty:
        st.warning("選択された条件に該当するデータがありません。")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["\U0001F4CA 概要", "\U0001F4C8 推移分析", "\U0001F5FA\ufe0f ヒートマップ", "\U0001F4CB データ詳細", "\U0001F4E4 エクスポート"])

    with tab1:
        st.header("\U0001F4CA データ概要")

        col1, col2, col3, col4 = st.columns(4)
        latest_year = filtered_data['year'].max()
        latest_data = filtered_data[filtered_data['year'] == latest_year]

        total_facilities = latest_data['facilities'].sum()
        total_rooms = latest_data['rooms'].sum()
        total_capacity = latest_data['capacity'].sum()
        total_minpaku = latest_data['minpaku_registrations'].sum()

        with col1:
            st.metric("総施設数", f"{total_facilities:,}軒")
        with col2:
            st.metric("総客室数", f"{total_rooms:,}室")
        with col3:
            st.metric("総収容人数", f"{total_capacity:,}人")
        with col4:
            st.metric("民泊届出数", f"{total_minpaku:,}件")

        st.subheader(f"{latest_year}年度 {METRICS[metric_key]}分布")

        if selected_municipality == "全体":
            chart_data = latest_data.groupby('municipality')[metric_key].sum().sort_values(ascending=True)
            fig = px.bar(
                x=chart_data.values,
                y=chart_data.index,
                orientation='h',
                title=f"{latest_year}年度 市町村別{METRICS[metric_key]}",
                labels={'x': METRICS[metric_key], 'y': '市町村'}
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            chart_data = latest_data.groupby('accommodation_type')[metric_key].sum()
            fig = px.pie(
                values=chart_data.values,
                names=chart_data.index,
                title=f"{latest_year}年度 {selected_municipality} 宿泊種別{METRICS[metric_key]}分布"
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("\U0001F4C8 推移分析")

        if len(year_range) < 2:
            st.info("推移分析には複数年度のデータが必要です。")
        else:
            trend_data = filtered_data.groupby('year')[metric_key].sum().reset_index()
            fig = px.line(trend_data, x='year', y=metric_key, title=f"{METRICS[metric_key]}の推移", markers=True)
            fig.update_layout(xaxis_title="年度", yaxis_title=METRICS[metric_key])
            st.plotly_chart(fig, use_container_width=True)

            if len(trend_data) >= 2:
                growth_rates = []
                for i in range(1, len(trend_data)):
                    prev_val = trend_data.iloc[i - 1][metric_key]
                    curr_val = trend_data.iloc[i][metric_key]
                    if prev_val > 0:
                        growth_rate = ((curr_val - prev_val) / prev_val) * 100
                        growth_rates.append({'year': trend_data.iloc[i]['year'], 'growth_rate': growth_rate})

                if growth_rates:
                    growth_df = pd.DataFrame(growth_rates)
                    st.subheader("前年比成長率")
                    fig_growth = px.bar(growth_df, x='year', y='growth_rate', title="前年比成長率 (%)",
                                        color='growth_rate', color_continuous_scale=['red', 'yellow', 'green'])
                    fig_growth.update_layout(xaxis_title="年度", yaxis_title="成長率 (%)")
                    st.plotly_chart(fig_growth, use_container_width=True)

            if selected_municipality != "全体":
                st.subheader("宿泊種別別推移比較")
                comparison_data = filtered_data.groupby(['year', 'accommodation_type'])[metric_key].sum().reset_index()
                fig_comparison = px.line(comparison_data, x='year', y=metric_key, color='accommodation_type',
                                         title=f"{selected_municipality} 宿泊種別別{METRICS[metric_key]}推移", markers=True)
                st.plotly_chart(fig_comparison, use_container_width=True)

    with tab3:
        st.header("\U0001F5FA\ufe0f ヒートマップ分析")

        heatmap_data = filtered_data.groupby(['municipality', 'accommodation_type'])[metric_key].sum().reset_index()
        heatmap_pivot = heatmap_data.pivot(index='municipality', columns='accommodation_type', values=metric_key).fillna(0)

        fig_heatmap = px.imshow(heatmap_pivot.values, x=heatmap_pivot.columns, y=heatmap_pivot.index,
                                aspect='auto', title=f"市町村 × 宿泊種別 {METRICS[metric_key]}ヒートマップ",
                                color_continuous_scale='Blues')
        fig_heatmap.update_layout(xaxis_title="宿泊種別", yaxis_title="市町村")
        st.plotly_chart(fig_heatmap, use_container_width=True)

        if len(year_range) > 1:
            st.subheader("年度別市町村ヒートマップ")
            year_heatmap_data = filtered_data.groupby(['year', 'municipality'])[metric_key].sum().reset_index()
            year_heatmap_pivot = year_heatmap_data.pivot(index='municipality', columns='year', values=metric_key).fillna(0)

            fig_year_heatmap = px.imshow(year_heatmap_pivot.values, x=year_heatmap_pivot.columns,
                                          y=year_heatmap_pivot.index, aspect='auto',
                                          title=f"市町村 × 年度 {METRICS[metric_key]}ヒートマップ",
                                          color_continuous_scale='Reds')
            fig_year_heatmap.update_layout(xaxis_title="年度", yaxis_title="市町村")
            st.plotly_chart(fig_year_heatmap, use_container_width=True)

    with tab4:
        st.header("\U0001F4CB データ詳細")
        st.subheader("データサマリー")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("対象年度数", len(filtered_data['year'].unique()))
            st.metric("対象市町村数", len(filtered_data['municipality'].unique()))
        with col2:
            st.metric("対象宿泊種別数", len(filtered_data['accommodation_type'].unique()))
            st.metric("総レコード数", len(filtered_data))

        st.subheader("詳細データテーブル")
        sort_by = st.selectbox("ソート基準:", ['year', 'municipality', 'accommodation_type', metric_key],
                               format_func=lambda x: {'year': '年度', 'municipality': '市町村',
                                                      'accommodation_type': '宿泊種別'}.get(x, METRICS.get(x, x)))
        sort_order = st.radio("ソート順:", ['昇順', '降順'])
        ascending = sort_order == '昇順'
        sorted_data = filtered_data.sort_values(sort_by, ascending=ascending)
        st.dataframe(sorted_data, use_container_width=True, height=400)

        st.subheader("統計サマリー")
        numeric_columns = ['facilities', 'rooms', 'capacity', 'minpaku_registrations']
        summary_stats = filtered_data[numeric_columns].describe()
        st.dataframe(summary_stats, use_container_width=True)

    with tab5:
        st.header("\U0001F4E4 データエクスポート")
        st.subheader("フィルター済みデータのエクスポート")
        export_format = st.selectbox("エクスポート形式:", ["CSV", "Excel", "JSON"])
        include_summary = st.checkbox("サマリー統計を含める", value=True)

        if st.button("エクスポート実行"):
            try:
                export_data = filtered_data.copy()
                if export_format == "CSV":
                    csv_data = export_data.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button("CSVファイルダウンロード", csv_data,
                                       file_name=f"okinawa_accommodation_data_{start_year}_{end_year}.csv",
                                       mime="text/csv")
                elif export_format == "Excel":
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        export_data.to_excel(writer, sheet_name='データ', index=False)
                        if include_summary:
                            summary_data = export_data.groupby(['year', 'municipality', 'accommodation_type']).agg({
                                'facilities': 'sum', 'rooms': 'sum', 'capacity': 'sum', 'minpaku_registrations': 'sum'
                            }).reset_index()
                            summary_data.to_excel(writer, sheet_name='サマリー', index=False)
                    buffer.seek(0)
                    st.download_button("Excelファイルダウンロード", buffer.getvalue(),
                                       file_name=f"okinawa_accommodation_data_{start_year}_{end_year}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                elif export_format == "JSON":
                    json_data = export_data.to_json(orient='records', force_ascii=False, indent=2)
                    st.download_button("JSONファイルダウンロード", json_data,
                                       file_name=f"okinawa_accommodation_data_{start_year}_{end_year}.json",
                                       mime="application/json")
                st.success("エクスポートが完了しました！")
            except Exception as e:
                st.error(f"エクスポートエラー: {str(e)}")

        st.subheader("\U0001F4CA データ品質チェック")
        if st.button("データ品質検証実行"):
            validation_results = {}
            missing_data = filtered_data.isnull().sum()
            validation_results["欠損値"] = "✅ 欠損値なし" if missing_data.sum() == 0 else f"⚠️ {missing_data.sum()}個の欠損値"
            numeric_cols = ['facilities', 'rooms', 'capacity', 'minpaku_registrations']
            negative_values = (filtered_data[numeric_cols] < 0).any().any()
            validation_results["負の値"] = "✅ 負の値なし" if not negative_values else "⚠️ 負の値が存在"
            inconsistent_rooms = (filtered_data['rooms'] > filtered_data['capacity']).any()
            validation_results["客室数-収容人数の整合性"] = "✅ 整合性問題なし" if not inconsistent_rooms else "⚠️ 客室数 > 収容人数のレコードが存在"
            for category, result in validation_results.items():
                (st.success if "✅" in result else st.warning)(f"{category}: {result}")

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
    \U0001F3E8 沖縄県宿泊施設データ可視化ダッシュボード |
    \U0001F4CA Streamlit + Plotly |
    \U0001F4C5 データ更新: 定期更新
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
