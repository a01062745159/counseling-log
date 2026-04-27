import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="병의원 실시간 상담일지", layout="wide")
st.title("📂 365일 실시간 상담 관리 시스템")

# 1. 구글 스프레드시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 기존 데이터 불러오기
try:
    df = conn.read(ttl="0s") # 실시간 조회를 위해 캐시 끔
except:
    df = pd.DataFrame(columns=["날짜", "분류", "성함", "차트번호", "상담내용", "주요포인트"])

# --- 입력 섹션 ---
with st.expander("📝 신규 상담 기록하기", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
        name = st.text_input("환자 성함")
    with c2:
        chart_no = st.text_input("차트 번호")
        points = st.text_input("주요 포인트")
    content = st.text_area("상담 상세 내용")

    if st.button("💾 클라우드에 저장"):
        if name and content:
            new_data = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "분류": category, "성함": name, "차트번호": chart_no,
                "상담내용": content, "주요포인트": points
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df) # 구글 시트 업데이트
            st.success("구글 스프레드시트에 안전하게 저장되었습니다!")
            st.rerun()

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역")
st.dataframe(df, use_container_width=True)