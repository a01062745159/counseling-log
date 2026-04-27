import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="병의원 실시간 상담일지", layout="wide")
st.title("📂 365일 실시간 상담 관리 시스템")

# 1. 구글 스프레드시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("구글 시트 연결 설정이 필요합니다. 오른쪽 하단 Settings -> Secrets를 확인하세요.")
    df = pd.DataFrame(columns=["날짜", "분류", "성함", "차트번호", "상담자", "상담내용", "주요포인트"])

# --- 입력 섹션 ---
with st.expander("📝 신규 상담 기록하기", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
        name = st.text_input("환자 성함")
    with c2:
        chart_no = st.text_input("차트 번호")
        consultant = st.text_input("상담자 성함") # 추가된 항목
    with c3:
        points = st.text_input("주요 포인트")
    
    content = st.text_area("상담 상세 내용")

    if st.button("💾 클라우드에 저장", use_container_width=True):
        if name and content and consultant:
            new_data = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "분류": category, 
                "성함": name, 
                "차트번호": chart_no,
                "상담자": consultant, # 추가된 항목
                "상담내용": content, 
                "주요포인트": points
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success("구글 스프레드시트에 저장되었습니다!")
            st.rerun()
        else:
            st.warning("환자 성함, 상담자 성함, 상담 내용은 필수입니다.")

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역")
st.dataframe(df, use_container_width=True)
