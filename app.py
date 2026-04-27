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
    df = pd.DataFrame(columns=["날짜", "상담자", "환자성함", "분류", "차트번호", "주요포인트", "상담내용"])

# --- 입력 섹션 ---
with st.expander("📝 기록", expanded=True):
    # 상단 2열 배치: 기본 정보
    c1, c2 = st.columns(2)
    with c1:
        # 상담자 성함을 선택형(selectbox)으로 수정
        consultant = st.selectbox("상담자 성함", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
        name = st.text_input("환자 성함")
    with c2:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
        chart_no = st.text_input("차트 번호")
    
    # 하단 전면 배치: 주요 포인트 및 상세 내용
    points = st.text_input("📍 주요 포인트 (한 줄 요약)")
    content = st.text_area("💬 상담 상세 내용", height=150)

    if st.button("💾 클라우드에 저장", use_container_width=True):
        if name and content: # 상담자는 선택형이므로 항상 값이 있음
            new_data = pd.DataFrame([{
                "날짜": datetime.now().strftime("%y년 %m월 %d일"),
                "상담자": consultant,
                "환자성함": name,
                "분류": category,
                "차트번호": chart_no,
                "주요포인트": points,
                "상담내용": content
            }])
            
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            
            st.success(f"{name} 환자님 상담 기록이 완료되었습니다!")
            st.rerun()
        else:
            st.warning("환자 성함과 상담 내용은 필수 입력 사항입니다.")

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역")
st.dataframe(df.style.set_properties(**{'text-align': 'center'}), use_container_width=True)
