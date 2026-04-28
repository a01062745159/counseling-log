import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# --- 🎨 글자 크기 '핵폭탄급' 고정 스타일 (CSS) ---
st.markdown("""
    <style>
    /* 1. 표 전체 글자 크기 고정 */
    [data-testid="stTable"] {
        font-size: 13px !important;
    }
    /* 2. 제목 기호(#)가 들어간 모든 요소를 일반 텍스트로 강제 변환 */
    [data-testid="stTable"] td h1, 
    [data-testid="stTable"] td h2, 
    [data-testid="stTable"] td h3, 
    [data-testid="stTable"] td h4,
    [data-testid="stTable"] td h5,
    [data-testid="stTable"] td h6,
    [data-testid="stTable"] td b,
    [data-testid="stTable"] td strong {
        font-size: 13px !important;
        font-weight: bold !important; /* 크기는 작게, 대신 두껍게 유지 */
        margin: 0 !important;
        padding: 0 !important;
        display: inline !important; /* 줄바꿈 방지 */
        line-height: 1.2 !important;
    }
    /* 3. 표 칸 안의 줄바꿈 허용 및 정렬 */
    [data-testid="stTable"] td {
        white-space: normal !important;
        word-break: break-all !important;
        vertical-align: middle !important;
        line-height: 1.4 !important;
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

# --- 사이드바 조회 설정 ---
with st.sidebar:
    st.header("🔍 조회 설정")
    today = datetime.now().date()
    start_date = st.date_input("조회 시작일", today - timedelta(days=7))
    end_date = st.date_input("조회 종료일", today)
    
    st.divider()
    view_mode = st.radio("👀 보기 모드 선택", ["🔍 정밀 조회 (확대/정렬)", "📄 보고용 (줄바꿈/캡처)"])
    all_view = st.checkbox("전체 기간 데이터 보기")

# --- 입력 섹션 ---
with st.expander("📝 새 상담 기록하기", expanded=False):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("👤 상담자", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("📢 결과", ["미확정", "확정"])
    
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("🏥 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("👤 환자 성함")
    with row2_c3:
        chart_no = st.text_input("🔢 차트 번호")

    amount = st.number_input("💰 금액 (원 단위)", min_value=0, step=10000, format="%d")
    points = st.text_input("📍 주요 포인트")
    content = st.text_area("💬 상세 상담 내용", height=150)

    if st.button("💾 스프레드시트에 저장", use_container_width=True):
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
            st.success(f"✅ 저장되었습니다!")
            st.rerun()

# --- 필터링 및 출력 ---
st.divider()
if not df.empty:
    df_display = df.copy()
    df_display['temp_date'] = pd.to_datetime(df_display['날짜'], errors='coerce').dt.date
    
    if not all_view:
        mask = (df_display['temp_date'] >= start_date) & (df_display['temp_date'] <= end_date)
        mask = mask | df_display['temp_date'].isna()
        filtered_df = df_display.loc[mask].drop(columns=['temp_date'])
    else:
        filtered_df = df_display.drop(columns=['temp_date'])

    final_df = filtered_df.iloc[::-1]

    if view_mode == "🔍 정밀 조회 (확대/정렬)":
        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "금액": st.column_config.NumberColumn("금액", format="%,d원", alignment="right"),
                "차트번호": st.column_config.TextColumn("차트번호", alignment="center"),
                "상담내용": st.column_config.Column("상담 상세 내용", width="large")
            }
        )
    else:
        # 보고용 가공
        report_df = final_df.copy()
        report_df['금액'] = report_df['금액'].apply(lambda x: f"{int(float(x or 0)):,}원")
        
        # 차트번호 소수점 제거 및 문자열화
        def clean_chart(x):
            try: return str(int(float(x))) if pd.notnull(x) and str(x).strip() != "" else ""
            except: return str(x)
        report_df['차트번호'] = report_df['차트번호'].apply(clean_chart)
        
        # 💡 [핵심] 제목 기호(#)가 있어도 커지지 않도록 한 번 더 방어
        st.table(report_df)
else:
    st.info("조회할 데이터가 없습니다.")
