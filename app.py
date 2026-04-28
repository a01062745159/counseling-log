import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# --- 🎨 글자 크기 '절대 고정' 스타일 (CSS) ---
st.markdown("""
    <style>
    [data-testid="stTable"] {
        font-size: 14px !important;
    }
    [data-testid="stTable"] h1, [data-testid="stTable"] h2, [data-testid="stTable"] h3,
    [data-testid="stTable"] h4, [data-testid="stTable"] h5, [data-testid="stTable"] h6 {
        font-size: 14px !important;
        font-weight: bold !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline !important;
        line-height: 1.5 !important;
    }
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
COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"]

# 2. 데이터 불러오기
try:
    raw_df = conn.read(ttl="0s")
    df = raw_df.dropna(subset=["환자성함"]).copy()
    if df.empty:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 사이드바 조회 설정 ---
with st.sidebar:
    st.header("🔍 데이터 필터")
    
    # [추가] 상담자별 필터
    selected_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS)
    
    # 날짜 범위 선택
    today = datetime.now().date()
    start_date = st.date_input("조회 시작일", today - timedelta(days=7))
    end_date = st.date_input("조회 종료일", today)
    
    st.divider()
    view_mode = st.radio("👀 보기 모드", ["🔍 정밀 조회 (확대/정렬)", "📄 보고용 (줄바꿈/캡처)"])
    all_view = st.checkbox("전체 기간 보기")

# --- 입력 섹션 ---
with st.expander("📝 새 상담 기록하기", expanded=False):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("👤 상담자", COUNSELORS)
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
    content = st.text_area("💬 상세 내용", height=200)

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
            st.success("✅ 저장 완료!")
            st.rerun()

# --- 데이터 필터링 및 출력 ---
st.divider()
if not df.empty:
    df_display = df.copy()
    
    # 날짜 필터링 적용
    df_display['temp_date'] = pd.to_datetime(df_display['날짜'], errors='coerce').dt.date
    if not all_view:
        mask = (df_display['temp_date'] >= start_date) & (df_display['temp_date'] <= end_date)
        mask = mask | df_display['temp_date'].isna()
        df_display = df_display.loc[mask]

    # [추가] 상담자 필터링 적용
    if selected_counselor != "전체":
        df_display = df_display[df_display['상담자'] == selected_counselor]

    final_df = df_display.drop(columns=['temp_date']).iloc[::-1]

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
        # 📄 보고용 모드 가공
        report_df = final_df.copy()
        report_df['금액'] = report_df['금액'].apply(lambda x: f"{int(float(x or 0)):,}원")
        
        def clean_chart(x):
            try: return str(int(float(x))) if pd.notnull(x) and str(x).strip() != "" else ""
            except: return str(x)
        report_df['차트번호'] = report_df['차트번호'].apply(clean_chart)

        def sanitize(text):
            if not isinstance(text, str): return text
            text = re.sub(r'(?m)^#', '＃', text)
            text = text.replace('-', '─')
            return text

        report_df['상담내용'] = report_df['상담내용'].apply(sanitize)
        report_df['주요포인트'] = report_df['주요포인트'].apply(sanitize)
        
        st.table(report_df)
else:
    st.info("조회할 데이터가 없습니다.")
