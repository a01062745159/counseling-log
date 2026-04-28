import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# --- 🎨 글자 크기 강제 고정 스타일 (CSS) ---
st.markdown("""
    <style>
    /* 표 내부의 모든 글자 크기 조절 */
    table {
        font-size: 13px !important;
    }
    /* 제목 기호(#)를 써도 커지지 않게 강제 고정 */
    td h1, td h2, td h3, td h4, td b {
        font-size: 13px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    /* 상담내용 칸은 왼쪽 정렬, 나머지는 중앙 */
    td {
        vertical-align: middle !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]

# 2. 데이터 불러오기
try:
    raw_df = conn.read(ttl="0s")
    df = raw_df.dropna(subset=["환자성함"]).copy()
    if df.empty:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 사이드바 필터 ---
with st.sidebar:
    st.header("🔍 조회 설정")
    today = datetime.now().date()
    start_date = st.date_input("시작일", today - timedelta(days=7))
    end_date = st.date_input("종료일", today)
    
    st.divider()
    view_mode = st.radio("👀 보기 모드", ["🔍 정밀 조회", "📄 보고용"])
    all_view = st.checkbox("전체 데이터 보기")

# --- 입력 섹션 ---
with st.expander("📝 새 상담 기록하기", expanded=True):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("상담자", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("결과", ["미확정", "확정"])
    
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("환자 성함")
    with row2_c3:
        chart_no = st.text_input("차트 번호")

    amount = st.number_input("금액 (원)", min_value=0, step=10000, format="%d")
    points = st.text_input("📍 주요 포인트")
    content = st.text_area("💬 상세 상담 내용", height=150)

    if st.button("💾 저장하기", use_container_width=True):
        if name:
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
            st.success("저장 완료!")
            st.rerun()

# --- 데이터 필터링 및 출력 ---
st.divider()
if not df.empty:
    df_temp = df.copy()
    df_temp['date_obj'] = pd.to_datetime(df_temp['날짜'], errors='coerce').dt.date
    
    if not all_view:
        mask = (df_temp['date_obj'] >= start_date) & (df_temp['date_obj'] <= end_date)
        mask = mask | df_temp['date_obj'].isna()
        display_df = df_temp.loc[mask].drop(columns=['date_obj'])
    else:
        display_df = df_temp.drop(columns=['date_obj'])

    display_df = display_df.iloc[::-1] # 최신순

    if view_mode == "🔍 정밀 조회":
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "금액": st.column_config.NumberColumn(format="%,d원"),
                "차트번호": st.column_config.TextColumn()
            }
        )
    else:
        # 보고서용 표 가공
        report_df = display_df.copy()
        report_df['금액'] = report_df['금액'].apply(lambda x: f"{int(float(x or 0)):,}원")
        # 차트번호 소수점 제거 로직 강화
        def clean_chart(x):
            try: return str(int(float(x))) if pd.notnull(x) and str(x).strip() != "" else ""
            except: return str(x)
        report_df['차트번호'] = report_df['차트번호'].apply(clean_chart)
        
        # HTML로 변환하여 출력 (스타일 유지)
        st.table(report_df)
else:
    st.info("데이터가 없습니다.")
