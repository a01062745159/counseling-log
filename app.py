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

# 2. 데이터 불러오기 및 구조 강제화
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

# --- 조회 섹션 (방법 2: 모든 내용이 다 보이는 st.table) ---
st.divider()
st.subheader("📅 전체 상담 내역 (보고용)")

if not df.empty:
    # 1. 보고용 데이터 복사 (원본 데이터 훼손 방지)
    display_df = df.copy()

    # 2. 금액 컬럼에 천 단위 콤마(,) 추가 (가공된 텍스트로 변경)
    display_df['금액'] = display_df['금액'].apply(lambda x: f"{int(x):,}원" if pd.notnull(x) else "0원")

    # 3. 최신 데이터가 가장 위에 오도록 역순 정렬 (선택 사항)
    display_df = display_df.iloc[::-1]

    # 4. 줄 바꿈이 허용되는 st.table 사용
    st.table(display_df)
else:
    st.info("아직 기록된 상담 내역이 없습니다.")
