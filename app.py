import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="수려한치과 상담일지", layout="wide")
st.title("📂 수려한치과 상담일지")

# 1. 구글 스프레드시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 표준 컬럼 순서
EXPECTED_COLS = ["날짜", "상담자", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용"]

# 2. 데이터 불러오기 (최대한 가볍게)
try:
    # ttl="0s"로 실시간 데이터 확인
    raw_df = conn.read(ttl="0s")
    
    # 💡 [핵심] 환자성함이 비어있는 모든 행은 데이터가 없는 것으로 간주하고 삭제합니다.
    # 이 코드가 있어야 구글 시트의 수천 개 빈 줄을 무시합니다.
    df = raw_df.dropna(subset=["환자성함"]).copy()
    
    # 만약 시트 자체가 아예 비어있다면 빈 데이터프레임 생성
    if df.empty:
        df = pd.DataFrame(columns=EXPECTED_COLS)
except Exception as e:
    df = pd.DataFrame(columns=EXPECTED_COLS)

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
            
            # 기존 데이터와 합치기
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df[EXPECTED_COLS])
            
            st.success(f"✅ {name} 환자님 기록 완료!")
            st.rerun()
        else:
            st.warning("⚠️ 환자 성함은 꼭 입력해주세요.")

# --- 조회 섹션 ---
st.divider()
st.subheader("📅 전체 상담 내역")

if not df.empty:
    # 정렬 및 콤마 표시가 가능한 정밀 조회 모드로 기본 설정
    # (에러를 일으킬 수 있는 날짜 필터는 일단 뺐습니다. 잘 되는지 확인부터 해요!)
    st.dataframe(
        df.iloc[::-1], # 최신순
        use_container_width=True,
        hide_index=True,
        column_config={
            "금액": st.column_config.NumberColumn(format="%,d원"),
            "차트번호": st.column_config.TextColumn(),
            "상담내용": st.column_config.Column(width="large")
        }
    )
else:
    st.info("아직 저장된 상담 내역이 없습니다. 첫 기록을 남겨보세요!")
