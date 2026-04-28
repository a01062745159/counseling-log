import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

st.markdown("""
    <style>
    [data-testid="stTable"] { font-size: 14px !important; }
    [data-testid="stTable"] td { white-space: pre-wrap !important; padding: 12px !important; }
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

with st.sidebar:
    st.header("🔍 데이터 검색/필터")
    selected_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS)
    today = datetime.now().date()
    start_date = st.date_input("시작일", today - timedelta(days=7))
    end_date = st.date_input("종료일", today)
    st.divider()
    view_mode = st.radio("👀 보기 모드", ["🔍 정밀 조회", "📄 보고용"])
    all_view = st.checkbox("전체 기간 보기")

with st.expander("📝 새 상담 기록하기", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        consultant = st.selectbox("상담자", COUNSELORS)
    with col2:
        result = st.selectbox("결과", ["미확정", "확정"])
    
    col3, col4, col5 = st.columns(3)
    with col3:
        category = st.selectbox("분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with col4:
        name = st.text_input("환자 성함")
    with col5:
        chart_no = st.text_input("차트 번호")

    amount = st.number_input("금액 (원)", min_value=0, step=10000, format="%d")
    points = st.text_input("주요 포인트")
    content = st.text_area("상담 내용", height=150)

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

tab1, tab2 = st.tabs(["📊 실적 현황", "📋 상담 기록"])

with tab1:
    st.header("📊 상담자별 실적")
    
    if not df.empty:
        stat_counselor = st.selectbox("상담자", ["전체"] + COUNSELORS, key="stat")
        
        df_stats = df.copy()
        df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
        
        if stat_counselor != "전체":
            df_stats = df_stats[df_stats['상담자'] == stat_counselor]
        
        if not df_stats.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("상담 건수", f"{len(df_stats)}건")
            with col2:
                st.metric("총 매출", f"{int(df_stats['금액_숫자'].sum()):,}원")
            with col3:
                confirmed = len(df_stats[df_stats['상담결과'] == '확정'])
                st.metric("확정 건수", f"{confirmed}건")
            with col4:
                avg = int(df_stats['금액_숫자'].mean()) if len(df_stats) > 0 else 0
                st.metric("평균 금액", f"{avg:,}원")
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("분류별 건수")
                category_data = df_stats['분류'].value_counts()
                if not category_data.empty:
                    st.bar_chart(category_data)
            
            with col_b:
                st.subheader("결과별 건수")
                result_data = df_stats['상담결과'].value_counts()
                if not result_data.empty:
                    st.bar_chart(result_data)
            
            st.divider()
            
            if stat_counselor == "전체":
                st.subheader("상담자별 매출")
                counselor_sales = df_stats.groupby('상담자')['금액_숫자'].agg(['sum', 'count', 'mean'])
                counselor_sales.columns = ['총매출', '상담건수', '평균금액']
                counselor_sales['총매출'] = counselor_sales['총매출'].astype(int)
                counselor_sales['상담건수'] = counselor_sales['상담건수'].astype(int)
                counselor_sales['평균금액'] = counselor_sales['평균금액'].astype(int)
                counselor_sales = counselor_sales.sort_values('총매출', ascending=False)
                st.dataframe(counselor_sales, use_container_width=True)
                st.bar_chart(counselor_sales['총매출'])
    else:
        st.info("데이터가 없습니다")

with tab2:
    st.header("📋 상담 기록")
    
    if not df.empty:
        df_view = df.copy()
        
        if selected_counselor != "전체":
            df_view = df_view[df_view['상담자'] == selected_counselor]
        
        df_view = df_view.iloc[::-1]
        
        if view_mode == "🔍 정밀 조회":
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            st.table(df_view)
    else:
        st.info("조회할 데이터가 없습니다")
