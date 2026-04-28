import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# --- 🎨 글자 크기 '철벽 방어' 스타일 (CSS) ---
st.markdown("""
    <style>
    /* 1. 표(st.table) 안의 모든 글자를 14px로 고정 */
    [data-testid="stTable"] {
        font-size: 14px !important;
    }
    /* 2. 기호 때문에 제목(h1~h6)이 생겨도 무조건 본문 크기로 강제 축소 */
    [data-testid="stTable"] h1, [data-testid="stTable"] h2, [data-testid="stTable"] h3,
    [data-testid="stTable"] h4, [data-testid="stTable"] h5, [data-testid="stTable"] h6 {
        font-size: 14px !important;
        font-weight: bold !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline !important;
        line-height: 1.5 !important;
    }
    /* 3. 줄바꿈 및 여백 최적화 */
    [data-testid="stTable"] td {
        white-space: pre-wrap !important;
        vertical-align: top !important;
        line-height: 1.6 !important;
        padding: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]
# 상담자 목록 (나중에 인원이 바뀌면 여기서 수정하세요)
COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"]

# 2. 데이터 불러오기
try:
    raw_df = conn.read(ttl="0s")
    # 환자성함이 비어있는 빈 줄은 무시 (로딩 속도 개선)
    df = raw_df.dropna(subset=["환자성함"]).copy()
    if df.empty:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 🔍 사이드바 필터 설정 (여기에 상담자 필터가 들어있습니다!) ---
with st.sidebar:
    st.header("🔍 데이터 검색/필터")
    
    # ✅ 상담자 선택 필터 (전체 또는 특정 인물)
    selected_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS)
    
    # 날짜 범위 선택
    today = datetime.now().date()
    start_date = st.date_input("시작일", today - timedelta(days=7))
    end_date = st.date_input("종료일", today)
    
    st.divider()
    view_mode = st.radio("👀 보기 모드", ["🔍 정밀 조회 (확대/정렬)", "📄 보고용 (줄바꿈/캡처)"])
    all_view = st.checkbox("전체 기간 보기 (날짜 필터 해제)")

# --- 📝 입력 섹션 ---
with st.expander("📝 새 상담 기록하기", expanded=False):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("👤 담당 상담자", COUNSELORS)
    with row1_c2:
        result = st.selectbox("📢 결과", ["미확정", "확정"])
    
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("🏥 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("👤 환자 성함")
    with row2_c3:
        chart_no = st.text_input("🔢 차트 번호")

    amount = st.number_input("💰 금액 (원)", min_value=0, step=10000, format="%d")
    points = st.text_input("📍 주요 포인트")
    content = st.text_area("💬 상세 상담 내용", height=200)

    if st.button("💾 저장하기", use_container_width=True):
        if name and content:
            new_entry = pd.DataFrame([{
                "날짜": datetime.now().strftime("%y년 %m월 %d일"),
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
            st.success("✅ 안전하게 저장되었습니다!")
            st.rerun()

# --- 📊 탭 나누기: 실적 vs 상담기록 ---
tab1, tab2 = st.tabs(["📊 실적 현황", "📋 상담 기록"])

with tab1:
    st.header("📊 상담자별 실적 현황")
    
    if not df.empty:
        # 데이터 준비
        df_stats = df.copy()
        df_stats['temp_date'] = pd.to_datetime(df_stats['날짜'], errors='coerce').dt.date
        
        if not all_view:
            mask = (df_stats['temp_date'] >= start_date) & (df_stats['temp_date'] <= end_date)
            mask = mask | df_stats['temp_date'].isna()
            df_stats = df_stats.loc[mask]
        
        # 상담자 선택 (실적 보기)
        stat_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="stat_counselor")
        
        if stat_counselor != "전체":
            df_stats = df_stats[df_stats['상담자'] == stat_counselor]
        
        if not df_stats.empty:
            # 금액 변환 (숫자로)
            df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
            
            # 1️⃣ 상단: 주요 지표
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_count = len(df_stats)
                st.metric("📌 상담 건수", f"{total_count}건")
            
            with col2:
                total_amount = df_stats['금액_숫자'].sum()
                st.metric("💰 총 매출", f"{int(total_amount):,}원")
            
            with col3:
                confirmed = len(df_stats[df_stats['상담결과'] == '확정'])
                st.metric("✅ 확정 건수", f"{confirmed}건")
            
            with col4:
                avg_amount = df_stats['금액_숫자'].mean()
                st.metric("📊 평균 금액", f"{int(avg_amount):,}원")
            
            st.divider()
            
            # 2️⃣ 분류별 건수
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("🏥 상담 분류별 건수")
                category_count = df_stats['분류'].value_counts().sort_values(ascending=True)
                st.bar_chart(category_count)
            
            with col_b:
                st.subheader("📢 상담 결과")
                result_count = df_stats['상담결과'].value_counts()
                st.bar_chart(result_count)
            
            st.divider()
            
            # 3️⃣ 상담자별 실적 (전체 선택시만)
            if stat_counselor == "전체":
                st.subheader("👥 상담자별 실적 비교")
                
                counselor_stats = df_stats.groupby('상담자').agg({
                    '환자성함': 'count',  # 상담 건수
                    '금액_숫자': 'sum',    # 총 금액
                }).rename(columns={'환자성함': '상담건수', '금액_숫자': '총매출'})
                
                counselor_stats['평균금액'] = (counselor_stats['총매출'] / counselor_stats['상담건수']).round(0).astype(int)
                counselor_stats['총매출'] = counselor_stats['총매출'].astype(int)
                counselor_stats = counselor_stats.sort_values('총매출', ascending=False)
                
                st.dataframe(
                    counselor_stats,
                    use_container_width=True,
                    column_config={
                        "상담건수": st.column_config.NumberColumn(format="%d건", alignment="center"),
                        "총매출": st.column_config.NumberColumn(format="%,d원", alignment="right"),
                        "평균금액": st.column_config.NumberColumn(format="%,d원", alignment="right"),
                    }
                )
                
                st.divider()
                st.bar_chart(counselor_stats['총매출'])
        else:
            st.info("📭 조회 기간에 상담 기록이 없습니다.")
    else:
        st.info("📭 데이터가 없습니다.")

with tab2:
    st.header("📋 상담 기록 상세")
    
    # --- 📅 데이터 필터링 로직 ---
    if not df.empty:
        df_filtered = df.copy()
        
        # 1. 날짜 필터링 적용
        df_filtered['temp_date'] = pd.to_datetime(df_filtered['날짜'], errors='coerce').dt.date
        if not all_view:
            mask = (df_filtered['temp_date'] >= start_date) & (df_filtered['temp_date'] <= end_date)
            mask = mask | df_filtered['temp_date'].isna() # 날짜 형식이 다른 과거 데이터도 포함
            df_filtered = df_filtered.loc[mask]

        # 2. ✅ 상담자 필터링 적용 (핵심!)
        if selected_counselor != "전체":
            df_filtered = df_filtered[df_filtered['상담자'] == selected_counselor]

        # 최신순 정렬
        final_df = df_filtered.drop(columns=['temp_date']).iloc[::-1]

        if view_mode == "🔍 정밀 조회 (확대/정렬)":
            st.dataframe(
                final_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "금액": st.column_config.NumberColumn(format="%,d원", alignment="right"),
                    "차트번호": st.column_config.TextColumn(alignment="center"),
                    "상담내용": st.column_config.Column(width="large")
                }
            )
        else:
            # 📄 보고용 모드 데이터 가공
            report_df = final_df.copy()
            report_df['금액'] = report_df['금액'].apply(lambda x: f"{int(float(x or 0)):,}원")
            
            def clean_chart(x):
                try: return str(int(float(x))) if pd.notnull(x) and str(x).strip() != "" else ""
                except: return str(x)
            report_df['차트번호'] = report_df['차트번호'].apply(clean_chart)

            # 기호 세니타이징 (글자 크기 커지는 현상 완전 방어)
            def sanitize(text):
                if not isinstance(text, str): return text
                text = re.sub(r'(?m)^#', '＃', text) # 줄 맨 앞의 # 방어
                text = text.replace('-', '─')        # 하이픈 연달아 쓰기 방어
                return text

            report_df['상담내용'] = report_df['상담내용'].apply(sanitize)
            report_df['주요포인트'] = report_df['주요포인트'].apply(sanitize)
            
            st.table(report_df)
    else:
        st.info("조회할 데이터가 없습니다.")
