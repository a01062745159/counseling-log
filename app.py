import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re
import plotly.express as px
import plotly.graph_objects as go
from calendar import monthrange

st.set_page_config(page_title="수려한치과 상담일지", layout="wide")

# 스타일 설정
st.markdown("""
    <style>
    [data-testid="stDataFrame"] {
        font-size: 14px !important;
    }
    [data-testid="stDataFrame"] tbody tr {
        height: auto !important;
    }
    [data-testid="stDataFrame"] td {
        white-space: normal !important;
        word-break: break-word !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        max-width: 400px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ===== 📋 Helper Functions (반복 코드 제거) =====
def format_amount(value):
    """금액을 정수로 변환"""
    try:
        return int(float(value)) if pd.notnull(value) else 0
    except:
        return 0

def format_chart_no(value):
    """차트번호 포맷팅"""
    try:
        return str(int(float(value))) if pd.notnull(value) and str(value).strip() != '' else ""
    except:
        return ""

def filter_by_date_range(df, start_date, end_date):
    """날짜 범위로 데이터 필터링"""
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    return df[(df['날짜'] >= start_str) & (df['날짜'] <= end_str)].copy()

def safe_parse_date(value):
    """문자열 날짜를 date 객체로 안전하게 변환 (실패 시 None 반환)"""
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

def load_gsheet_data(conn):
    """Google Sheet에서 데이터 로드 (컬럼 보정 + 날짜 정규화 포함)"""
    expected = ["날짜", "상담자", "진단원장", "환자성함", "차트번호", "분류",
                "상담결과", "금액", "주요포인트", "상담내용", "리콜상태"]
    try:
        df = conn.read(ttl="0s")
        df = df.dropna(subset=["환자성함"]).copy()
        # 누락된 컬럼 보정 (KeyError 방지)
        for col in expected:
            if col not in df.columns:
                df[col] = '미리콜' if col == '리콜상태' else ''
        # 날짜를 항상 'YYYY-MM-DD' 문자열로 통일 (비교·파싱 오류 방지)
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
        df['날짜'] = df['날짜'].fillna('')
        # 리콜상태 빈 값 보정
        df['리콜상태'] = df['리콜상태'].fillna('미리콜').replace('', '미리콜')
        return df
    except Exception:
        st.warning("⚠️ Google Sheets 연결 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        return pd.DataFrame()

def calculate_stats(df):
    """통계 계산"""
    df['금액_숫자'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0)
    
    total_count = len(df)
    total_amount = int(df['금액_숫자'].sum())
    confirmed_count = len(df[df['상담결과'] == '확정'])
    unconfirmed_count = len(df[df['상담결과'] == '미확정'])
    confirmed_amount = int(df[df['상담결과'] == '확정']['금액_숫자'].sum())
    unconfirmed_amount = int(df[df['상담결과'] == '미확정']['금액_숫자'].sum())
    agreement_rate = (confirmed_count / total_count * 100) if total_count > 0 else 0
    
    return {
        'total_count': total_count,
        'total_amount': total_amount,
        'confirmed_count': confirmed_count,
        'unconfirmed_count': unconfirmed_count,
        'confirmed_amount': confirmed_amount,
        'unconfirmed_amount': unconfirmed_amount,
        'agreement_rate': agreement_rate
    }

def display_stats_metrics(stats):
    """통계 메트릭 표시"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📌 전체 상담건수", f"{stats['total_count']}건")
    with col2:
        st.metric("💰 총 상담액", f"{stats['total_amount']:,}원")
    with col3:
        st.metric("🎯 동의율", f"{stats['agreement_rate']:.1f}%")
    
    col4, col5 = st.columns(2)
    with col4:
        st.metric("✅ 확정 건수", f"{stats['confirmed_count']}건")
        st.metric("✅ 확정 상담액", f"{stats['confirmed_amount']:,}원")
    with col5:
        st.metric("❌ 미확정 건수", f"{stats['unconfirmed_count']}건")
        st.metric("❌ 미확정 상담액", f"{stats['unconfirmed_amount']:,}원")

def get_counselor_stats(df, counselors):
    """상담자별 통계 계산"""
    counselor_stats_list = []
    for counselor in counselors:
        counselor_data = df[df['상담자'] == counselor]
        
        total_count = len(counselor_data)
        confirmed = len(counselor_data[counselor_data['상담결과'] == '확정'])
        unconfirmed = len(counselor_data[counselor_data['상담결과'] == '미확정'])
        
        # 확정/미확정 매출 분리
        confirmed_amount = int(counselor_data[counselor_data['상담결과'] == '확정']['금액_숫자'].sum())
        unconfirmed_amount = int(counselor_data[counselor_data['상담결과'] == '미확정']['금액_숫자'].sum())
        
        agreement_rate = (confirmed / total_count * 100) if total_count > 0 else 0
        
        counselor_stats_list.append({
            '상담자': counselor,
            '상담건수': total_count,
            '확정건수': confirmed,
            '미확정건수': unconfirmed,
            '동의율': f"{agreement_rate:.1f}%",
            '확정매출_숫자': confirmed_amount,  # 정렬용 숫자
            '확정매출': f"{confirmed_amount:,}원",
            '미확정매출': f"{unconfirmed_amount:,}원"
        })
    
    result_df = pd.DataFrame(counselor_stats_list)
    
    # 확정매출 기준 내림차순 정렬
    result_df = result_df.sort_values('확정매출_숫자', ascending=False)
    
    # 정렬용 컬럼 제거
    result_df = result_df.drop('확정매출_숫자', axis=1)
    
    return result_df.reset_index(drop=True)

# ===== 🔒 로그인 기능 =====
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 수려한치과 상담일지</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>비밀번호를 입력하세요</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            password = st.text_input("🔑 비밀번호", type="password", placeholder="비밀번호 입력")
            submitted = st.form_submit_button("🔓 로그인", use_container_width=True)
            
            if submitted:
                if password == "2874":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 틀렸습니다. 다시 입력해주세요.")
    st.stop()

# ===== 로그인 성공 후 앱 시작 =====
st.title("📂 수려한치과 상담일지")

conn = st.connection("gsheets", type=GSheetsConnection)
EXPECTED_COLS = ["날짜", "상담자", "진단원장", "환자성함", "차트번호", "분류", "상담결과", "금액", "주요포인트", "상담내용", "리콜상태"]
COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장", "배지윤 팀장", "김소연 팀장", "최수진 팀장"]
DOCTORS = ["안정선 대표원장", "김동현 대표원장", "이성재 수석원장", "박지호 원장", "이동호 원장", "신효담 원장", "구다솜 원장", "강순영 원장(교정)", "윤소정 원장(교정)"]

# 데이터 로드
df = load_gsheet_data(conn)

# ===== 5개 탭 생성 =====
tabs_list = st.tabs([
    "📝 상담일지 작성", 
    "📞 미확정 리마인더", 
    "🔍 상담일지 수정", 
    "📊 보고 자료",
    "📈 통계"
])

# 탭 변수 매핑 (변수명과 실제 탭이 다르므로 주의)
tab_write = tabs_list[0]      # [1] 상담일지 작성
tab_reminder = tabs_list[1]   # [2] 미확정 리마인더
tab_report = tabs_list[2]     # [3] 상담일지 '수정'  (변수명 report 아님 주의)
tab_integrated = tabs_list[3] # [4] '보고 자료'
tab_statistics = tabs_list[4] # [5] 통계

# ===== TAB 1: 상담일지 작성 =====
with tab_write:
    st.header("📝 상담일지 작성")
    
    # 입력 날짜 선택 (우측 상단)
    col_date = st.columns([3, 1])[1]
    with col_date:
        today = datetime.now().date()
        input_date = st.date_input("📅 입력 날짜", today, key="tab1_date")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        consultant = st.selectbox("👤 담당 상담자", [None] + COUNSELORS, format_func=lambda x: "선택하세요" if x is None else x, key="tab1_counselor")
    with col2:
        doctor = st.selectbox("👨‍⚕️ 진단 원장님", [None] + DOCTORS, format_func=lambda x: "선택하세요" if x is None else x, key="tab1_doctor")
    with col3:
        result = st.selectbox("📢 결과", [None, "미확정", "확정"], format_func=lambda x: "선택하세요" if x is None else x, key="tab1_result")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        category = st.selectbox("🏥 분류", ["예약 신환", "미예약 신환", "예약 구환", "미예약 구환"], key="tab1_category")
    with col4:
        name = st.text_input("👤 환자 성함", key="tab1_name")
    with col5:
        chart_no = st.text_input("🔢 차트 번호", key="tab1_chart")

    amount = st.number_input("💰 금액 (원)", min_value=0, step=10000, format="%d", key="tab1_amount")
    points = st.text_input("📍 주요 포인트", key="tab1_points")
    content = st.text_area("💬 상세 상담 내용", height=150, key="tab1_content")

    if st.button("💾 저장하기", use_container_width=True):
        # 필수 필드 검증
        if not name:
            st.error("❌ 환자 성함을 입력해주세요!")
        elif not content:
            st.error("❌ 상담 내용을 입력해주세요!")
        elif consultant is None:
            st.error("❌ 상담자를 선택해주세요!")
        elif doctor is None:
            st.error("❌ 진단 원장을 선택해주세요!")
        elif result is None:
            st.error("❌ 상담 결과를 선택해주세요!")
        else:
            # Google Sheets 연결 확인
            if df.empty:
                st.error("❌ Google Sheets에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.")
            else:
                new_entry = pd.DataFrame([{
                    "날짜": input_date.strftime("%Y-%m-%d"),
                    "상담자": consultant,
                    "진단원장": doctor,
                    "환자성함": name,
                    "차트번호": chart_no,
                    "분류": category,
                    "상담결과": result,
                    "금액": amount,
                    "주요포인트": points,
                    "상담내용": content,
                    "리콜상태": "미리콜"
                }])
                try:
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    conn.update(data=updated_df[EXPECTED_COLS])
                    
                    st.success("✅ 저장되었습니다!", icon="✅")
                    st.balloons()  # 풍선 효과
                    
                    # 저장된 데이터 표시
                    st.subheader("📝 방금 저장된 내용")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**환자명:** {name}")
                        st.write(f"**상담자:** {consultant}")
                        st.write(f"**진단원장:** {doctor}")
                        st.write(f"**분류:** {category}")
                    with col2:
                        st.write(f"**날짜:** {input_date}")
                        st.write(f"**결과:** {result}")
                        st.write(f"**금액:** {amount:,}원")
                        st.write(f"**차트번호:** {chart_no}")
                    
                    st.write(f"**주요포인트:** {points}")
                    st.write(f"**상담내용:** {content}")
                    
                    st.divider()
                    
                    # 입력한 날짜의 내역
                    st.subheader("📋 입력 날짜 내역")
                    selected_day = input_date.strftime("%Y-%m-%d")
                    today_data = updated_df[updated_df['날짜'] == selected_day].copy()
                    
                    if not today_data.empty:
                        today_data = today_data.iloc[::-1]
                        st.write(f"총 **{len(today_data)}건** 입력됨")
                        
                        for idx, row in today_data.iterrows():
                            with st.expander(f"📌 {row['환자성함']} - {row['상담자']} ({row['상담결과']})"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**진단원장:** {row['진단원장']}")
                                    st.write(f"**분류:** {row['분류']}")
                                    st.write(f"**금액:** {int(float(row['금액'])):,}원")
                                with col2:
                                    st.write(f"**차트번호:** {row['차트번호']}")
                                    st.write(f"**주요포인트:** {row['주요포인트']}")
                                st.write(f"**상담내용:** {row['상담내용']}")
                    
                    st.divider()
                    st.info("✏️ 페이지를 새로고침하면 입력칸이 초기화됩니다")
                except Exception as e:
                    st.error("❌ 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

# ===== TAB 2: 상담 보고 (보고용) =====
with tab_report:
    st.header("🔍 상담일지 조회")
    
    # 데이터 새로 읽기 (최신 데이터 가져오기)
    df_tab2_source = load_gsheet_data(conn)
    
    
    if not df_tab2_source.empty:
        st.write("환자 이름 또는 차트번호로 검색하세요. (부분 검색 가능)")
        search_patient = st.text_input("🔍 환자 이름 또는 차트번호 검색", placeholder="예: 송호선, 12345 등", key="tab_report_search")
        
        if search_patient:
            # 환자 이름 또는 차트번호로 검색
            df_search = df_tab2_source[
                (df_tab2_source['환자성함'].str.contains(search_patient, case=False, na=False)) | 
                (df_tab2_source['차트번호'].astype(str).str.contains(search_patient, case=False, na=False))
            ].copy()
            
            if not df_search.empty:
                st.success(f"✅ '{search_patient}' 검색 결과: {len(df_search)}건")
                st.divider()
                
                for idx, row in df_search.iterrows():
                    chart_num = format_chart_no(row['차트번호'])
                    with st.expander(
                        f"📌 {row['날짜']} - {row['환자성함']} (차트: {chart_num}) - {row['상담자']}", 
                        expanded=True
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**분류:** {row['분류']}")
                            st.write(f"**금액:** {format_amount(row['금액']):,}원")
                        with col2:
                            st.write(f"**진단원장:** {row['진단원장']}")
                            # 현재 상담결과 표시
                            current_result = row['상담결과']
                            st.write(f"**현재 상담결과:** {current_result}")
                            
                            # 상담결과 수정하기
                            st.write("**상담결과 수정:**")
                            new_result = st.selectbox(
                                "변경할 상담결과 선택", 
                                ["확정", "미확정"], 
                                index=0 if current_result == "확정" else 1,
                                key=f"result_{idx}_{row['환자성함']}"
                            )
                        with col3:
                            st.write(f"**차트번호:** {chart_num}")
                            
                            # 현재 날짜 표시
                            current_date = row['날짜']
                            st.write(f"**현재 날짜:** {current_date}")
                            
                            # 날짜 수정하기
                            st.write("**날짜 수정:**")
                            date_obj = safe_parse_date(current_date) or datetime.now().date()
                            new_date = st.date_input(
                                "변경할 날짜", 
                                value=date_obj,
                                key=f"date_{idx}_{row['환자성함']}"
                            )
                        
                        # 수정사항이 있으면 저장 버튼 표시
                        has_changes = (new_result != current_result) or (new_date != date_obj)
                        if has_changes:
                            if st.button(f"✅ 저장", key=f"save_{idx}_{row['환자성함']}"):
                                changes = []
                                if new_result != current_result:
                                    changes.append(f"상담결과: {current_result} → {new_result}")
                                if new_date != date_obj:
                                    changes.append(f"날짜: {current_date} → {new_date.strftime('%Y-%m-%d')}")
                                
                                try:
                                    df_tab2_source.loc[idx, '상담결과'] = new_result
                                    df_tab2_source.loc[idx, '날짜'] = new_date.strftime('%Y-%m-%d')
                                    conn.update(data=df_tab2_source[EXPECTED_COLS])
                                    st.success("✅ 변경사항이 저장되었습니다!\n" + "\n".join(changes))
                                    st.rerun()
                                except Exception:
                                    st.error("❌ 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                        
                        st.markdown(f"**주요포인트:** {row['주요포인트']}")
                        st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
            else:
                st.warning(f"❌ '{search_patient}'에 해당하는 환자가 없습니다.")
        else:
            st.info("환자 이름 또는 차트번호를 입력해주세요.")
    else:
        st.info("데이터가 없습니다")

# ===== TAB 3: 상담 내용 조회 (환자 검색) =====

# ===== TAB 3: 미확정 상담 리마인더 =====
with tab_reminder:
    st.header("📞 미확정 상담 리마인더")
    
    col1, col2 = st.columns(2)
    with col1:
        reminder_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab5_counselor")
    with col2:
        st.write("")
    
    if not df.empty:
        df_reminder = df[df['상담결과'] == '미확정'].copy()
        
        if reminder_counselor != "전체":
            df_reminder = df_reminder[df_reminder['상담자'] == reminder_counselor]
        
        if not df_reminder.empty:
            today = datetime.now().date()
            def _elapsed_days(x):
                d = safe_parse_date(x)
                return (today - d).days if d else -1
            df_reminder['경과일'] = df_reminder['날짜'].apply(_elapsed_days)
            df_reminder = df_reminder[df_reminder['경과일'] >= 7]
            
            if not df_reminder.empty:
                df_reminder['리콜상태'] = df_reminder['리콜상태'].fillna('미리콜')
                
                df_need_recall = df_reminder[df_reminder['리콜상태'] == '미리콜'].sort_values('경과일', ascending=False)
                df_recalled = df_reminder[df_reminder['리콜상태'] == '리콜완료'].sort_values('경과일', ascending=False)
                
                # 미리콜 (상단)
                if not df_need_recall.empty:
                    st.subheader(f"🔴 리콜 필요 ({len(df_need_recall)}명)")
                    st.divider()
                    for idx, row in df_need_recall.iterrows():
                        with st.expander(
                            f"👤 {row['환자성함']} | 차트: {format_chart_no(row['차트번호'])} | {row['경과일']}일 경과 | {format_amount(row['금액']):,}원 | ❌ {row['상담결과']} | {row['상담자']}", 
                            expanded=True
                        ):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown(f"**주요포인트:** {row['주요포인트']}")
                                st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
                            
                            with col2:
                                if st.button("✅ 리콜완료", key=f"recall_{idx}", use_container_width=True):
                                    st.session_state[f"confirm_{idx}"] = True
                            
                            if st.session_state.get(f"confirm_{idx}", False):
                                st.warning("정말 리콜완료 하시겠습니까?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✔️ 확인", key=f"confirm_yes_{idx}", use_container_width=True):
                                        df.loc[df.index == idx, '리콜상태'] = '리콜완료'
                                        conn.update(data=df[EXPECTED_COLS])
                                        st.session_state[f"confirm_{idx}"] = False
                                        st.success("리콜 완료되었습니다!")
                                        st.rerun()
                                with col_no:
                                    if st.button("❌ 취소", key=f"confirm_no_{idx}", use_container_width=True):
                                        st.session_state[f"confirm_{idx}"] = False
                                        st.rerun()
                
                # 리콜완료 (하단)
                if not df_recalled.empty:
                    st.divider()
                    with st.expander(f"✅ 리콜 완료 ({len(df_recalled)}명)", expanded=False):
                        for idx, row in df_recalled.iterrows():
                            with st.expander(
                                f"👤 {row['환자성함']} | 차트: {format_chart_no(row['차트번호'])} | {row['경과일']}일 | {format_amount(row['금액']):,}원 | {row['상담자']}", 
                                expanded=False
                            ):
                                col1, col2 = st.columns([3, 1])
                                
                                with col1:
                                    st.markdown(f"**주요포인트:** {row['주요포인트']}")
                                    st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
                                
                                with col2:
                                    if st.button("↩️ 리콜 재진행", key=f"undo_recall_{idx}", use_container_width=True):
                                        st.session_state[f"confirm_undo_{idx}"] = True
                                
                                if st.session_state.get(f"confirm_undo_{idx}", False):
                                    st.warning("리콜 완료를 취소하고 미리콜로 변경하시겠습니까?")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("✔️ 확인", key=f"confirm_undo_yes_{idx}", use_container_width=True):
                                            df.loc[df.index == idx, '리콜상태'] = '미리콜'
                                            conn.update(data=df[EXPECTED_COLS])
                                            st.session_state[f"confirm_undo_{idx}"] = False
                                            st.success("미리콜로 변경되었습니다!")
                                            st.rerun()
                                    with col_no:
                                        if st.button("❌ 취소", key=f"confirm_undo_no_{idx}", use_container_width=True):
                                            st.session_state[f"confirm_undo_{idx}"] = False
                                            st.rerun()
            else:
                st.info("🎉 리콜 필요한 상담이 없습니다!")
        else:
            st.info("미확정 상담이 없습니다.")
    else:
        st.info("데이터가 없습니다.")

# ===== TAB 5: 상담 일지 통계 =====
# ===== TAB 5: 상담 보고 =====
with tab_integrated:
    st.header("📄 상담 보고")
    
    # 데이터 새로고침
    df_integrated = load_gsheet_data(conn)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_integrated = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="integrated_counselor")
    with col2:
        today = datetime.now().date()
        start_date_integrated = st.date_input("시작일", today, key="integrated_start")
    with col3:
        end_date_integrated = st.date_input("종료일", today, key="integrated_end")
    
    if not df_integrated.empty:
        df_report = df_integrated.copy()
        df_report['금액_숫자'] = pd.to_numeric(df_report['금액'], errors='coerce').fillna(0)
        
        start_str = start_date_integrated.strftime("%Y-%m-%d")
        end_str = end_date_integrated.strftime("%Y-%m-%d")
        df_report = df_report[(df_report['날짜'] >= start_str) & (df_report['날짜'] <= end_str)]
        
        if selected_counselor_integrated != "전체":
            df_report = df_report[df_report['상담자'] == selected_counselor_integrated]
        
        if not df_report.empty:
            # 1. 상담일지 통계 (상단)
            stats_integrated = calculate_stats(df_report)
            st.subheader("📊 상담일지 통계")
            display_stats_metrics(stats_integrated)
            
            st.divider()
            
            # 2. 상담자별 매출 및 성과
            if selected_counselor_integrated == "전체":
                st.subheader("👥 상담자별 매출 및 성과")
                
                counselor_sales_df = get_counselor_stats(df_report, COUNSELORS)
                st.dataframe(counselor_sales_df, use_container_width=True, hide_index=True)
                
                st.divider()
            
            # 3. 분류별 상담 현황
            st.subheader("📋 분류별 상담 현황 (확정/미확정)")
            
            category_order = ['예약 신환', '미예약 신환', '예약 구환', '미예약 구환']
            
            category_result_data = []
            for category in category_order:
                category_df = df_report[df_report['분류'] == category]
                confirmed = len(category_df[category_df['상담결과'] == '확정'])
                unconfirmed = len(category_df[category_df['상담결과'] == '미확정'])
                
                category_result_data.append({
                    '분류': category,
                    '확정': confirmed,
                    '미확정': unconfirmed,
                    '합계': confirmed + unconfirmed
                })
            
            category_result_df = pd.DataFrame(category_result_data)
            st.dataframe(category_result_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # 4. 상담내용 상세
            st.metric("📌 상담 건수", f"{len(df_report)}건")
            st.divider()
            
            # ✨ 날짜 과거순 + 같은 날짜면 금액 높은순으로 정렬
            df_report = df_report.sort_values(['날짜', '금액_숫자'], ascending=[True, False])
            
            st.subheader("📝 상담내용 상세")
            for idx, row in df_report.iterrows():
                with st.expander(f"📌 {row['날짜']} - {row['환자성함']} (차트: {format_chart_no(row['차트번호'])}) - {row['상담자']}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**분류:** {row['분류']}")
                        st.write(f"**금액:** {format_amount(row['금액']):,}원")
                    with col2:
                        st.write(f"**진단원장:** {row['진단원장']}")
                        # 상담결과 색상 구분
                        if row['상담결과'] == '확정':
                            st.markdown(f"**상담결과:** <span style='color: blue; font-weight: bold;'>확정</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**상담결과:** <span style='color: red; font-weight: bold;'>미확정</span>", unsafe_allow_html=True)
                    with col3:
                        st.write(f"**차트번호:** {format_chart_no(row['차트번호'])}")
                    
                    st.markdown(f"**주요포인트:** {row['주요포인트']}")
                    st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
        else:
            st.info("해당 기간에 상담 기록이 없습니다")

# ===== [5] 통계 (tab_statistics) =====
with tab_statistics:
    st.header("📈 통계 분석")

    # ===== 🔒 통계 탭 비밀번호 게이트 =====
    if "stats_unlocked" not in st.session_state:
        st.session_state.stats_unlocked = False

    if not st.session_state.stats_unlocked:
        st.warning("🔒 이 탭은 비밀번호 입력 후 확인할 수 있습니다.")
        col_pw1, col_pw2, col_pw3 = st.columns([1, 2, 1])
        with col_pw2:
            with st.form("stats_password_form"):
                stats_pw = st.text_input("🔑 비밀번호", type="password", placeholder="비밀번호 입력")
                stats_submit = st.form_submit_button("🔓 확인", use_container_width=True)
                if stats_submit:
                    if stats_pw == "1103":
                        st.session_state.stats_unlocked = True
                        st.rerun()
                    else:
                        st.error("❌ 비밀번호가 틀렸습니다. 다시 입력해주세요.")
        st.stop()

    df_stats = load_gsheet_data(conn)

    if not df_stats.empty:
        # ----- 기간 선택 -----
        col1, col2, col3 = st.columns(3)
        with col1:
            date_type = st.radio(
                "📅 기간 선택",
                ["월간", "특정 기간"],
                horizontal=True,
                key="stats_date_type"
            )

        if date_type == "월간":
            with col2:
                selected_year = st.selectbox(
                    "연도",
                    range(2020, datetime.now().year + 1),
                    index=datetime.now().year - 2020,
                    key="stats_year"
                )
            with col3:
                selected_month = st.selectbox(
                    "월",
                    range(1, 13),
                    index=datetime.now().month - 1,
                    key="stats_month"
                )
            start_date_stats = datetime(selected_year, selected_month, 1).date()
            last_day = monthrange(selected_year, selected_month)[1]
            end_date_stats = datetime(selected_year, selected_month, last_day).date()
        else:
            with col2:
                start_date_stats = st.date_input("시작일", datetime.now().date(), key="stats_start")
            with col3:
                end_date_stats = st.date_input("종료일", datetime.now().date(), key="stats_end")

        # ----- 날짜 필터링 -----
        df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
        df_f = filter_by_date_range(df_stats, start_date_stats, end_date_stats)

        if not df_f.empty:
            st.divider()

            # ===== 요약 통계 =====
            st.subheader("📊 요약 통계")
            total_count = len(df_f)
            total_amount = int(df_f['금액_숫자'].sum())
            confirmed_count = len(df_f[df_f['상담결과'] == '확정'])
            unconfirmed_count = len(df_f[df_f['상담결과'] == '미확정'])
            agreement_rate = (confirmed_count / total_count * 100) if total_count > 0 else 0
            confirmed_amount = int(df_f[df_f['상담결과'] == '확정']['금액_숫자'].sum())
            unconfirmed_amount = int(df_f[df_f['상담결과'] == '미확정']['금액_숫자'].sum())

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("📌 총 상담건수", f"{total_count}건")
            with c2:
                st.metric("💰 총 매출액", f"{total_amount:,}원")
            with c3:
                st.metric("✅ 확정건수", f"{confirmed_count}건")
            with c4:
                st.metric("❌ 미확정건수", f"{unconfirmed_count}건")
            with c5:
                st.metric("🎯 동의율", f"{agreement_rate:.1f}%")

            ca1, ca2 = st.columns(2)
            with ca1:
                st.metric("✅ 확정 상담매출 총액", f"{confirmed_amount:,}원")
            with ca2:
                st.metric("❌ 미확정 상담매출 총액", f"{unconfirmed_amount:,}원")

            st.divider()

            df_confirmed = df_f[df_f['상담결과'] == '확정']
            df_unconfirmed = df_f[df_f['상담결과'] == '미확정']

            # ===== 상담자별 확정 / 미확정 상담 건수 =====
            st.subheader("👥 상담자별 상담 건수 (확정 / 미확정)")
            col_a, col_b = st.columns(2)

            with col_a:
                confirmed_cnt = df_confirmed['상담자'].value_counts().sort_values(ascending=False)
                if not confirmed_cnt.empty:
                    fig = px.bar(
                        x=confirmed_cnt.index, y=confirmed_cnt.values,
                        labels={'x': '상담자', 'y': '확정 건수'},
                        title="상담자별 확정 상담 건수",
                        text_auto=True, color=confirmed_cnt.values,
                        color_continuous_scale="Blues"
                    )
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("확정 상담 데이터가 없습니다")

            with col_b:
                unconfirmed_cnt = df_unconfirmed['상담자'].value_counts().sort_values(ascending=False)
                if not unconfirmed_cnt.empty:
                    fig = px.bar(
                        x=unconfirmed_cnt.index, y=unconfirmed_cnt.values,
                        labels={'x': '상담자', 'y': '미확정 건수'},
                        title="상담자별 미확정 상담 건수",
                        text_auto=True, color=unconfirmed_cnt.values,
                        color_continuous_scale="Reds"
                    )
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("미확정 상담 데이터가 없습니다")

            st.divider()

            # ===== 상담자별 동의율 =====
            st.subheader("🎯 상담자별 동의율")
            counselor_total = df_f['상담자'].value_counts()
            counselor_confirmed = df_confirmed['상담자'].value_counts().reindex(counselor_total.index, fill_value=0)
            agree_rate = (counselor_confirmed / counselor_total * 100).sort_values(ascending=False)
            if not agree_rate.empty:
                agree_df = pd.DataFrame({'상담자': agree_rate.index, '동의율': agree_rate.values})
                fig_agree = px.bar(
                    agree_df, x='상담자', y='동의율',
                    title="상담자별 동의율 (확정 / 전체)",
                    text='동의율', color='동의율',
                    color_continuous_scale="Tealgrn"
                )
                fig_agree.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_agree.update_layout(showlegend=False, height=400, yaxis_range=[0, 105])
                st.plotly_chart(fig_agree, use_container_width=True)
            else:
                st.info("동의율 데이터가 없습니다")

            st.divider()

            # ===== 상담자별 확정 / 미확정 매출액 =====
            st.subheader("💰 상담자별 매출액 (확정 / 미확정)")
            col_c, col_d = st.columns(2)

            with col_c:
                confirmed_sales = df_confirmed.groupby('상담자')['금액_숫자'].sum().sort_values(ascending=False)
                if not confirmed_sales.empty:
                    fig = px.bar(
                        x=confirmed_sales.index, y=confirmed_sales.values,
                        labels={'x': '상담자', 'y': '확정 매출액 (원)'},
                        title="상담자별 확정 상담 매출액",
                        text_auto=True, color=confirmed_sales.values,
                        color_continuous_scale="Blues"
                    )
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("확정 매출 데이터가 없습니다")

            with col_d:
                unconfirmed_sales = df_unconfirmed.groupby('상담자')['금액_숫자'].sum().sort_values(ascending=False)
                if not unconfirmed_sales.empty:
                    fig = px.bar(
                        x=unconfirmed_sales.index, y=unconfirmed_sales.values,
                        labels={'x': '상담자', 'y': '미확정 매출액 (원)'},
                        title="상담자별 미확정 상담 매출액",
                        text_auto=True, color=unconfirmed_sales.values,
                        color_continuous_scale="Reds"
                    )
                    fig.update_layout(showlegend=False, height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("미확정 매출 데이터가 없습니다")

            st.divider()

            # ===== 상담자별 확정 / 미확정 매출 비중 =====
            st.subheader("📊 상담자별 확정 / 미확정 매출 비중")
            total_sales = confirmed_sales.add(unconfirmed_sales, fill_value=0).sort_values(ascending=False)
            counselors_with_sales = [c for c in total_sales.index if total_sales[c] > 0]
            if counselors_with_sales:
                ratio_rows = []
                for c in counselors_with_sales:
                    conf = int(confirmed_sales.get(c, 0))
                    unconf = int(unconfirmed_sales.get(c, 0))
                    tot = conf + unconf
                    ratio_rows.append({'상담자': c, '구분': '확정', '비중': conf / tot * 100, '매출액': conf})
                    ratio_rows.append({'상담자': c, '구분': '미확정', '비중': unconf / tot * 100, '매출액': unconf})
                ratio_df = pd.DataFrame(ratio_rows)
                ratio_df['표시'] = ratio_df['비중'].map(lambda v: f"{v:.1f}%")
                fig_ratio = px.bar(
                    ratio_df, x='상담자', y='비중', color='구분',
                    title="상담자별 확정/미확정 매출 비중 (100% 기준)",
                    text='표시',
                    color_discrete_map={'확정': '#3366cc', '미확정': '#dc3912'},
                    category_orders={'상담자': counselors_with_sales}
                )
                fig_ratio.update_traces(textposition='inside')
                fig_ratio.update_layout(height=400, yaxis_title='비중 (%)', barmode='stack')
                st.plotly_chart(fig_ratio, use_container_width=True)
            else:
                st.info("매출 비중 데이터가 없습니다")

            st.divider()

            # ===== 상담 결과 분포 (원형 그래프) =====
            st.subheader("✅ 상담 결과 분포")
            result_dist = df_f['상담결과'].value_counts()
            fig_pie = px.pie(
                values=result_dist.values, names=result_dist.index,
                title="상담 결과 분포 (확정/미확정)",
                color=result_dist.index,
                color_discrete_map={'확정': '#3366cc', '미확정': '#dc3912'},
                hole=0
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()

            # ===== 날짜별 상담 건수 추이 (꺾은선 그래프) =====
            st.subheader("📈 날짜별 상담 건수 추이")
            daily_count = df_f.groupby('날짜').size().reset_index(name='상담건수').sort_values('날짜')
            fig_daily = px.line(
                daily_count, x='날짜', y='상담건수',
                title="날짜별 상담 건수 추이", markers=True, line_shape='linear'
            )
            fig_daily.update_traces(line=dict(color='#3366cc', width=3), marker=dict(size=8))
            fig_daily.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig_daily, use_container_width=True)

            st.divider()

            # ===== 요일별 상담 건수 추이 (꺾은선 그래프) =====
            st.subheader("📅 요일별 상담 건수 추이")
            dow = pd.to_datetime(df_f['날짜'], errors='coerce').dt.dayofweek
            dow_count = (
                dow.dropna().astype(int)
                .value_counts()
                .reindex(range(7), fill_value=0)
                .sort_index()
            )
            weekday_labels = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
            fig_dow = px.line(
                x=weekday_labels, y=dow_count.values,
                labels={'x': '요일', 'y': '상담건수'},
                title="요일별 상담 건수 추이", markers=True, line_shape='linear'
            )
            fig_dow.update_traces(line=dict(color='#2ca02c', width=3), marker=dict(size=8))
            fig_dow.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig_dow, use_container_width=True)

        else:
            st.info("해당 기간에 상담 기록이 없습니다")
    else:
        st.info("데이터가 없습니다")
