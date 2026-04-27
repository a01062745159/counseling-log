import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="병의원 실시간 상담일지", layout="wide")
st.title("📂 365일 실시간 상담 관리 시스템")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 기존 데이터 불러오기 (헤더 순서 유지)
try:
    df = conn.read(ttl="0s")
except:
    df = pd.DataFrame(columns=["날짜", "상담자", "환자성함", "분류", "차트번호", "주요포인트", "상담내용"])

# --- 입력 섹션 ---
with st.expander("📝 신규 상담 기록하기", expanded=True):
    # 입력 칸 배치 조정 (상담자 우선)
    c1, c2, c3 = st.columns(3)
    with c1:
        consultant = st.text_input("상담자 성함")
        name = st.text_input("환자 성함")
    with c2:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
        chart_no = st.text_input("차트 번호")
    with c3:
        points = st.text_input("주요 포인트")
    
    content = st.text_area("상담 상세 내용", height=150)

    if st.button("💾 클라우드에 저장", use_container_width=True):
        if name and content and consultant:
            # 요청하신 순서대로 데이터 구성
            new_data = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "상담자": consultant,
                "환자성함": name,
                "분류": category,
                "차트번호": chart_no,
                "주요포인트": points,
                "상담내용": content
            }])
            
            # 데이터 합치기 및 구글 시트 업데이트
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            
            st.success(f"{name} 환자님 상담 기록이 완료되었습니다!")
            st.rerun()
        else:
            st.warning("상담자, 환자 성함, 상담 내용은 필수 입력 사항입니다.")

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역 (최근 기록이 아래에 추가됩니다)")
st.dataframe(df, use_container_width=True)
