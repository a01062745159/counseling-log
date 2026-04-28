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

# 2. 데이터 불러오기
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

# --- 조회 섹션 (모드 전환 기능) ---
st.divider()
c_title, c_mode = st.columns([2, 1])
with c_title:
    st.subheader("📅 상담 내역 조회")
with c_mode:
    # 실장님이 원하시는 대로 모드를 선택할 수 있게 만들었습니다.
    view_mode = st.radio("보기 모드 선택", ["🔍 정밀 조회 (확대/정렬)", "📄 보고서용 (줄바꿈/전체노출)"], horizontal=True)

if not df.empty:
    # 공통: 최신순 정렬
    display_df = df.iloc[::-1].copy()

    if view_mode == "🔍 정밀 조회 (확대/정렬)":
        # 1. 확대 아이콘이 있는 인터랙티브 표
        st.dataframe(
            display_df, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "차트번호": st.column_config.TextColumn("차트번호", alignment="center"),
                "금액": st.column_config.NumberColumn("금액", format="%,d원", alignment="right"),
                "날짜": st.column_config.Column(alignment="center"),
                "상담자": st.column_config.Column(alignment="center"),
                "환자성함": st.column_config.Column(alignment="center"),
                "분류": st.column_config.Column(alignment="center"),
                "상담결과": st.column_config.Column(alignment="center"),
                "주요포인트": st.column_config.Column(width="medium"),
                "상담내용": st.column_config.Column(width="large"),
            }
        )
        st.caption("💡 표 우측 상단 아이콘을 누르면 확대해서 보실 수 있습니다.")
    
    else:
        # 2. 줄 바꿈이 되는 보고서용 표
        # 차트번호 소수점 및 금액 콤마 수동 처리 (st.table용)
        display_df['금액'] = display_df['금액'].apply(lambda x: f"{int(x):,}원" if pd.notnull(x) else "0원")
        def fix_chart(x):
            try: return str(int(float(x)))
            except: return str(x)
        display_df['차트번호'] = display_df['차트번호'].apply(fix_chart)
        
        st.table(display_df)
        st.caption("💡 이 모드는 글자가 잘리지 않아 캡처해서 보고하기 좋습니다.")

else:
    st.info("아직 기록된 상담 내역이 없습니다.")
