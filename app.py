import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# --- 🎨 글자 크기 및 스타일 강제 고정 (CSS) ---
# 이 부분이 '현수막' 현상을 막아주는 핵심입니다!
st.markdown("""
    <style>
    /* 1. 표 내부의 모든 글자(제목 포함) 크기를 14px로 고정 */
    div[data-testid="stTable"] table {
        font-size: 14px !important;
    }
    div[data-testid="stTable"] td, 
    div[data-testid="stTable"] th,
    div[data-testid="stTable"] td * {
        font-size: 14px !important;
        line-height: 1.5 !important;
        font-weight: normal !important;
        display: inline !important; /* 제목 기호 때문에 줄바꿈 되는 것 방지 */
    }
    /* 2. 강조 표시(**)나 제목(#)을 써도 글자가 안 커지게 방어 */
    div[data-testid="stTable"] b, 
    div[data-testid="stTable"] strong, 
    div[data-testid="stTable"] h1, 
    div[data-testid="stTable"] h2, 
    div[data-testid="stTable"] h3 {
        font-size: 14px !important;
        margin: 0 !important;
        padding: 0 !important;
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
    all_view = st.checkbox("전체 데이터 보기 (날짜 무시)")

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
    points = st.text_input("📍 주요 포인트 (한 줄 요약)")
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
            st.success(f"✅ {name} 환자님 기록 완료!")
            st.rerun()

# --- 필터링 및 출력 ---
st.divider()
if not df.empty:
    df_display = df.copy()
    # 날짜 필터링을 위한 변환 (errors='coerce'로 에러 방어)
    df_display['temp_date'] = pd.to_datetime(df_display['날짜'], errors='coerce').dt.date
    
    if not all_view:
        mask = (df_display['temp_date'] >= start_date) & (df_display['temp_date'] <= end_date)
        mask = mask | df_display['temp_date'].isna() # 날짜 없는 예전 데이터도 일단 포함
        filtered_df = df_display.loc[mask].drop(columns=['temp_date'])
    else:
        filtered_df = df_display.drop(columns=['temp_date'])

    final_df = filtered_df.iloc[::-1] # 최신순

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
        # 보고용(st.table) 가공
        report_df = final_df.copy()
        # 금액 콤마 추가
        report_df['금액'] = report_df['금액'].apply(lambda x: f"{int(float(x or 0)):,}원")
        # 차트번호 소수점 제거
        def clean_chart(x):
            try: return str(int(float(x))) if pd.notnull(x) and str(x).strip() != "" else ""
            except: return str(x)
        report_df['차트번호'] = report_df['차트번호'].apply(clean_chart)
        
        # 스타일이 적용된 테이블 출력
        st.table(report_df)
else:
    st.info("조회할 데이터가 없습니다.")
