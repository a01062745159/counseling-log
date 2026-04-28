import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")
st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 표준 컬럼 순서 (9개)
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]

# 2. 데이터 불러오기 및 구조 강제화
try:
    df = conn.read(ttl="0s")
    if list(df.columns) != EXPECTED_COLS:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# --- 입력 섹션 ---
with st.expander("📝 기록하기", expanded=True):
    # 1행: 상담자 및 결과
    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        consultant = st.selectbox("상담자 성함", ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"])
    with row1_c2:
        result = st.selectbox("상담 결과", ["미확정", "확정"])
    
    # 2행: 환자 정보
    row2_c1, row2_c2, row2_c3 = st.columns(3)
    with row2_c1:
        category = st.selectbox("환자 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"])
    with row2_c2:
        name = st.text_input("환자 성함")
    with row2_c3:
        chart_no = st.text_input("차트 번호")

    # 3행: 금액 (원 단위)
    amount = st.number_input("상담 금액 (원)", min_value=0, step=10000, format="%d")
        
    # 4행: 주요 포인트
    points = st.text_input("📍 주요 포인트 (한 줄 요약)")
    
    # 5행: 상세 상담 내용
    content = st.text_area("💬 상담 상세 내용", height=200)

    # 저장 버튼
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
            
            # 기존 데이터와 합쳐서 순서 고정 후 업데이트
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            updated_df = updated_df[EXPECTED_COLS]
            conn.update(data=updated_df)
            
            st.success(f"✅ {name} 환자님의 상담 기록이 저장되었습니다!")
            st.rerun()
        else:
            st.warning("⚠️ 환자 성함과 상세 상담 내용은 필수입니다.")

# --- 조회 섹션 (보고서 캡처용 설정) ---
st.divider()
st.subheader("📅 전체 상담 내역 (보고용 캡처)")

# 여기서 모든 정렬과 콤마 표시를 강제로 설정합니다.
st.dataframe(
    df, 
    use_container_width=True,
    hide_index=True, # 왼쪽 인덱스 번호 숨김
    column_config={
        "날짜": st.column_config.Column("날짜", alignment="center"),
        "상담자": st.column_config.Column("상담자", alignment="center"),
        "환자성함": st.column_config.Column("환자성함", alignment="center"),
        "차트번호": st.column_config.Column("차트번호", alignment="center"),
        "분류": st.column_config.Column("분류", alignment="center"),
        "상담결과": st.column_config.Column("상담결과", alignment="center"),
        "금액": st.column_config.NumberColumn(
            "상담 금액",
            format="%,d원",      # 천 단위 콤마(,)와 '원' 표시
            alignment="right"     # 금액은 우측 정렬
        ),
        "주요포인트": st.column_config.Column("주요 포인트", width="medium"),
        "상담내용": st.column_config.Column("상담 상세 내용", width="large"),
    }
)
