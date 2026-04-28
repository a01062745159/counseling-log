import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")
st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 데이터 불러오기
try:
    df = conn.read(ttl="0s")
except:
    df = pd.DataFrame(columns=["날짜", "상담자", "환자성함", "분류", "차트번호", "상담결과", "주요포인트", "상담내용"])

# --- 입력 섹션 ---
with st.expander("📝 기록", expanded=True):
    
    # 1행: 상담자 성함 / 상담 결과 (가로 2칸)
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("👤 상담자 성함", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("상담 결과", ["미확정", "확정"])
    
    # 2행: 환자 분류 / 환자 성함 / 차트번호 (가로 3칸)
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("환자 성함")
    with row2_c3:
        chart_no = st.text_input("차트 번호")
        
    # 3행: 주요 포인트 (가로 1칸 전체)
    points = st.text_input("📍 주요 포인트 (한 줄 요약)")
    
    # 4행: 상담 상세내용 (가로 1칸 전체)
    content = st.text_area("💬 상담 상세 내용", height=200)

    # 저장 버튼
    if st.button("💾 클라우드에 저장", use_container_width=True):
        if name and content:
            new_data = pd.DataFrame([{
                "날짜": datetime.now().strftime("%y년 %m월 %d일"),
                "상담자": consultant,
                "환자성함": name,
                "분류": category,
                "차트번호": chart_no,
                "상담결과": result,
                "주요포인트": points,
                "상담내용": content
            }])
            
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            
            st.success(f"✅ {name} 환자님의 상담 기록이 저장되었습니다!")
            st.rerun()
        else:
            st.warning("⚠️ 환자 성함과 상담 내용은 필수입니다.")

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역")
st.dataframe(df, use_container_width=True)
