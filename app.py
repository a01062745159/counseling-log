import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

st.markdown("""
    <style>
    [data-testid="stDataFrame"] {
        font-size: 14px !important;
    }
    [data-testid="stDataFrame"] tbody tr {
        height: auto !important;
    }
    [data-testid="stDataFrame"] td {
        white-space: normal !important;
        word-break: break-word !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        max-width: 400px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📂 수려한치과 상담일지")

conn = st.connection("gsheets", type=GSheetsConnection)
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]
COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"]

try:
    df = conn.read(ttl="0s")
    df = df.dropna(subset=["환자성함"]).copy()
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# ===== 4개 탭 생성 =====
tab1, tab2, tab3, tab4 = st.tabs(["📝 상담일지 작성", "📋 상담 기록", "📄 상담 보고", "📊 상담 일지 통계"])

# ===== TAB 1: 상담일지 작성 =====
with tab1:
    st.header("📝 상담일지 작성")
    
    col1, col2 = st.columns(2)
    with col1:
        consultant = st.selectbox("👤 담당 상담자", COUNSELORS, key="tab1_counselor")
    with col2:
        result = st.selectbox("📢 결과", ["미확정", "확정"], key="tab1_result")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        category = st.selectbox("🏥 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"], key="tab1_category")
    with col4:
        name = st.text_input("👤 환자 성함", key="tab1_name")
    with col5:
        chart_no = st.text_input("🔢 차트 번호", key="tab1_chart")

    amount = st.number_input("💰 금액 (원)", min_value=0, step=10000, format="%d", key="tab1_amount")
    points = st.text_input("📍 주요 포인트", key="tab1_points")
    content = st.text_area("💬 상세 상담 내용", height=150, key="tab1_content")

    if st.button("💾 저장하기", use_container_width=True):
        if name and content:
            new_entry = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d"),
                "상담자": consultant,
                "환자성함": name,
                "차트번호": chart_no,
                "분류": category,
                "상담결과": result,
                "금액": amount,
                "주요포인트": points,
                "상담내용": content
            }])
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df[EXPECTED_COLS])
            st.success("✅ 저장되었습니다!")
            st.rerun()

# ===== TAB 2: 상담 기록 (정밀 조회) =====
with tab2:
    st.header("📋 상담 기록")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_tab2 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab2_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab2 = st.date_input("시작일", today, key="tab2_start")
    with col3:
        end_date_tab2 = st.date_input("종료일", today, key="tab2_end")
    
    if not df.empty:
        df_tab2 = df.copy()
        df_tab2['금액_숫자'] = pd.to_numeric(df_tab2['금액'], errors='coerce').fillna(0)
        
        # 날짜 필터
        start_str = start_date_tab2.strftime("%Y-%m-%d")
        end_str = end_date_tab2.strftime("%Y-%m-%d")
        df_tab2 = df_tab2[(df_tab2['날짜'] >= start_str) & (df_tab2['날짜'] <= end_str)]
        
        # 상담자 필터
        if selected_counselor_tab2 != "전체":
            df_tab2 = df_tab2[df_tab2['상담자'] == selected_counselor_tab2]
        
        df_tab2 = df_tab2.iloc[::-1]
        
        st.dataframe(
            df_tab2, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "금액": st.column_config.NumberColumn(format="%,d원", alignment="right"),
                "상담내용": st.column_config.Column(width="medium")
            }
        )
    else:
        st.info("조회할 데이터가 없습니다")

# ===== TAB 3: 상담 보고 (보고용) =====
with tab3:
    st.header("📄 상담 보고")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_tab3 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab3_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab3 = st.date_input("시작일", today, key="tab3_start")
    with col3:
        end_date_tab3 = st.date_input("종료일", today, key="tab3_end")
    
    if not df.empty:
        df_tab3 = df.copy()
        
        # 날짜 필터
        start_str = start_date_tab3.strftime("%Y-%m-%d")
        end_str = end_date_tab3.strftime("%Y-%m-%d")
        df_tab3 = df_tab3[(df_tab3['날짜'] >= start_str) & (df_tab3['날짜'] <= end_str)]
        
        # 상담자 필터
        if selected_counselor_tab3 != "전체":
            df_tab3 = df_tab3[df_tab3['상담자'] == selected_counselor_tab3]
        
        df_tab3 = df_tab3.iloc[::-1]
        
        st.subheader("📝 상담내용 상세")
        for idx, row in df_tab3.iterrows():
            with st.expander(f"📌 {row['날짜']} - {row['상담자']} - {row['환자성함']} ({row['금액']:,.0f}원)", expanded=True):
                st.markdown(f"**주요포인트:** {row['주요포인트']}")
                st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
    else:
        st.info("조회할 데이터가 없습니다")

# ===== TAB 4: 실적 현황 =====
with tab4:
    st.header("📊 상담 일지 통계")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_tab4 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab4_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab4 = st.date_input("시작일", today, key="tab4_start")
    with col3:
        end_date_tab4 = st.date_input("종료일", today, key="tab4_end")
    
    if not df.empty:
        df_stats = df.copy()
        df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
        
        # 날짜 필터
        start_str = start_date_tab4.strftime("%Y-%m-%d")
        end_str = end_date_tab4.strftime("%Y-%m-%d")
        df_stats = df_stats[(df_stats['날짜'] >= start_str) & (df_stats['날짜'] <= end_str)]
        
        # 상담자 필터
        if selected_counselor_tab4 != "전체":
            df_stats = df_stats[df_stats['상담자'] == selected_counselor_tab4]
        
        if not df_stats.empty:
            # 데이터 계산
            total_count = len(df_stats)
            total_amount = int(df_stats['금액_숫자'].sum())
            confirmed_count = len(df_stats[df_stats['상담결과'] == '확정'])
            unconfirmed_count = len(df_stats[df_stats['상담결과'] == '미확정'])
            confirmed_amount = int(df_stats[df_stats['상담결과'] == '확정']['금액_숫자'].sum())
            unconfirmed_amount = int(df_stats[df_stats['상담결과'] == '미확정']['금액_숫자'].sum())
            agreement_rate = (confirmed_count / total_count * 100) if total_count > 0 else 0
            
            # 상단: 주요 지표
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📌 전체 상담건수", f"{total_count}건")
            with col2:
                st.metric("💰 총 상담액", f"{total_amount:,}원")
            with col3:
                st.metric("🎯 동의율", f"{agreement_rate:.1f}%")
            
            st.divider()
            
            # 중단: 확정/미확정
            col4, col5 = st.columns(2)
            with col4:
                st.subheader("✅ 확정")
                st.metric("확정 건수", f"{confirmed_count}건")
                st.metric("확정 상담액", f"{confirmed_amount:,}원")
            with col5:
                st.subheader("❌ 미확정")
                st.metric("미확정 건수", f"{unconfirmed_count}건")
                st.metric("미확정 상담액", f"{unconfirmed_amount:,}원")
            
            st.divider()
            
            # 그래프
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("결과별 건수")
                result_data = df_stats['상담결과'].value_counts()
                result_order = ['확정', '미확정']
                result_data = result_data.reindex(result_order, fill_value=0)
                if not result_data.empty:
                    st.bar_chart(result_data)
            
            with col_b:
                st.subheader("분류별 건수")
                category_data = df_stats['분류'].value_counts()
                category_order = ['예약 신환', '미예약 신환', '예약 구환', '미예약 구환']
                category_data = category_data.reindex(category_order, fill_value=0)
                if not category_data.empty:
                    st.bar_chart(category_data)
            
            st.divider()
            
            # 상담자별 매출 (전체 선택시만)
            if selected_counselor_tab4 == "전체":
                st.subheader("👥 상담자별 매출")
                counselor_sales = df_stats.groupby('상담자')['금액_숫자'].agg(['sum', 'count', 'mean'])
                counselor_sales.columns = ['총매출', '상담건수', '평균금액']
                counselor_sales['총매출'] = counselor_sales['총매출'].astype(int)
                counselor_sales['상담건수'] = counselor_sales['상담건수'].astype(int)
                counselor_sales['평균금액'] = counselor_sales['평균금액'].astype(int)
                counselor_sales = counselor_sales.sort_values('총매출', ascending=False)
                st.dataframe(counselor_sales, use_container_width=True)
                st.bar_chart(counselor_sales['총매출'])
        else:
            st.info("해당 기간에 상담 기록이 없습니다")
    else:
        st.info("데이터가 없습니다")
