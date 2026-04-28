import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="수려한치과 상담일지", layout="wide")
st.title("📂 수려한치과 상담일지")

conn = st.connection("gsheets", type=GSheetsConnection)
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]

try:
    df = conn.read(ttl="0s")
    if list(df.columns) != EXPECTED_COLS:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 입력 섹션 ---
with st.expander("📝 기록하기", expanded=True):
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("👤 상담자 성함", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("📢 상담 결과", ["미확정", "확정"])
    
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("🏥 환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("👤 환자 성함")
    with row2_c3:
        chart_no = st.text_input("🔢 차트 번호")

    amount = st.number_input("💰 상담 금액 (원)", min_value=0, step=10000, format="%d")
    points = st.text_input("📍 주요 포인트 (한 줄 요약)")
    content = st.text_area("💬 상담 상세 내용", height=200)

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
            updated_df = updated_df[EXPECTED_COLS]
            conn.update(data=updated_df)
            st.success(f"✅ {name} 환자님의 기록이 저장되었습니다!")
            st.rerun()
        else:
            st.warning("⚠️ 필수 항목을 입력해주세요.")

# --- 조회 섹션 (다시 st.dataframe으로 변경하여 확대 기능 살림) ---
st.divider()
st.subheader("📅 전체 상담 내역 (우측 상단 확대 아이콘 사용 가능)")

if not df.empty:
    # 최신순 정렬
    display_df = df.iloc[::-1].copy()

    st.dataframe(
        display_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "날짜": st.column_config.Column(alignment="center"),
            "상담자": st.column_config.Column(alignment="center"),
            "환자성함": st.column_config.Column(alignment="center"),
            # 차트번호를 문자열로 취급하여 콤마/소수점 제거
            "차트번호": st.column_config.TextColumn("차트번호", alignment="center"),
            "분류": st.column_config.Column(alignment="center"),
            "상담결과": st.column_config.Column(alignment="center"),
            "금액": st.column_config.NumberColumn("상담 금액", format="%,d원", alignment="right"),
            # 내용을 아주 넓게 설정
            "주요포인트": st.column_config.Column("📍 주요 포인트", width="large"),
            "상담내용": st.column_config.Column("💬 상담 상세 내용", width="large"),
        }
    )
else:
    st.info("아직 기록된 상담 내역이 없습니다.")
