import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")
st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 표준 컬럼 순서
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]

# 2. 데이터 불러오기 (최대한 가볍게)
try:
    raw_df = conn.read(ttl="0s")
    # 환자성함이 비어있는 행은 무시 (로딩 속도 개선)
    df = raw_df.dropna(subset=["환자성함"]).copy()
    if df.empty:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except Exception as e:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 사이드바: 날짜 필터 조회 ---
with st.sidebar:
    st.header("🔍 기간별 조회")
    today = datetime.now().date()
    start_date = st.date_input("시작일", today - timedelta(days=7))
    end_date = st.date_input("종료일", today)
    
    st.divider()
    st.caption("팁: 차트번호는 콤마 없이 표시되며, 금액에는 자동으로 콤마가 붙습니다.")

# --- 입력 섹션 ---
with st.expander("📝 새 상담 기록하기", expanded=True):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("상담자 성함", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("상담 결과", ["미확정", "확정"])
    
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("환자 성함")
    with row2_c3:
        chart_no = st.text_input("차트 번호")

    amount = st.number_input("상담 금액 (원)", min_value=0, step=10000, format="%d")
    points = st.text_input("📍 주요 포인트")
    content = st.text_area("💬 상담 상세 내용", height=150)

    if st.button("💾 스프레드시트에 저장", use_container_width=True):
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
            
            st.success(f"✅ {name} 환자님 기록 완료!")
            st.rerun()
        else:
            st.warning("⚠️ 환자 성함은 꼭 입력해주세요.")

# --- 조회 및 필터링 섹션 ---
st.divider()
st.subheader("📅 상담 내역 내역")

if not df.empty:
    # 날짜 필터링 로직
    df_display = df.copy()
    # 날짜 형식이 달라도 읽을 수 있도록 처리
    df_display['date_obj'] = pd.to_datetime(df_display['날짜'], errors='coerce').dt.date
    
    # 선택한 기간의 데이터만 필터링
    mask = (df_display['date_obj'] >= start_date) & (df_display['date_obj'] <= end_date)
    # 날짜 형식이 안 맞아서 NaT가 된 데이터도 일단 포함 (데이터 누락 방지)
    mask = mask | df_display['date_obj'].isna()
    df_filtered = df_display.loc[mask].drop(columns=['date_obj'])

    # 최신순 정렬 및 데이터프레임 표시
    st.dataframe(
        df_filtered.iloc[::-1], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "금액": st.column_config.NumberColumn("상담 금액", format="%,d원", alignment="right"),
            "차트번호": st.column_config.TextColumn("차트번호", alignment="center"),
            "상담내용": st.column_config.Column("상담 상세 내용", width="large"),
            "주요포인트": st.column_config.Column("주요 포인트", width="medium"),
            "날짜": st.column_config.Column(alignment="center"),
            "상담자": st.column_config.Column(alignment="center"),
            "환자성함": st.column_config.Column(alignment="center"),
            "분류": st.column_config.Column(alignment="center"),
            "상담결과": st.column_config.Column(alignment="center"),
        }
    )
else:
    st.info("아직 저장된 상담 내역이 없습니다.")
