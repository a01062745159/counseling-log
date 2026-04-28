import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

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

# --- 사이드바 필터링 섹션 ---
with st.sidebar:
    st.header("🔍 데이터 검색/필터")
    
    # 날짜 필터링 (기본값: 최근 일주일)
    today = datetime.now()
    start_date = st.date_input("시작일", today - timedelta(days=7))
    end_date = st.date_input("종료일", today)
    
    st.divider()
    # 보기 모드 선택 (사이드바로 이동하여 메인 화면을 더 넓게 쓰게 했습니다)
    view_mode = st.radio("👀 보기 모드 선택", ["🔍 정밀 조회", "📄 보고서용"])

# --- 입력 섹션 ---
with st.expander("📝 기록하기", expanded=False): # 입력창은 필요할 때만 열도록 기본값을 닫음(False)으로 변경
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

# --- 데이터 필터링 로직 ---
if not df.empty:
    # 1. 날짜 컬럼을 비교 가능한 날짜 형식으로 임시 변환
    # "26년 04월 28일" -> datetime 객체
    df_temp = df.copy()
    df_temp['date_obj'] = pd.to_datetime(df_temp['날짜'], format='%y년 %m월 %d일').dt.date
    
    # 2. 선택한 날짜 범위에 맞는 데이터만 필터링
    mask = (df_temp['date_obj'] >= start_date) & (df_temp['date_obj'] <= end_date)
    filtered_df = df_temp.loc[mask].drop(columns=['date_obj']) # 임시 컬럼 삭제
    
    # --- 조회 섹션 ---
    st.divider()
    st.subheader(f"📅 상담 내역 ({start_date.strftime('%y/%m/%d')} ~ {end_date.strftime('%y/%m/%d')})")
    
    if filtered_df.empty:
        st.info("선택하신 기간에는 상담 기록이 없습니다.")
    else:
        # 최신순 정렬
        display_df = filtered_df.iloc[::-1].copy()

        if view_mode == "🔍 정밀 조회":
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
        else:
            # 보고서용 (st.table) 포맷 가공
            display_df['금액'] = display_df['금액'].apply(lambda x: f"{int(x):,}원" if pd.notnull(x) else "0원")
            def fix_chart(x):
                try: return str(int(float(x)))
                except: return str(x)
            display_df['차트번호'] = display_df['차트번호'].apply(fix_chart)
            
            st.table(display_df)
else:
    st.info("아직 기록된 상담 내역이 없습니다.")
