import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

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

def load_gsheet_data(conn):
    """Google Sheet에서 데이터 로드"""
    try:
        df = conn.read(ttl="0s")
        df = df.dropna(subset=["환자성함"]).copy()
        if '진단원장' not in df.columns:
            df['진단원장'] = ''
        if '리콜상태' not in df.columns:
            df['리콜상태'] = '미리콜'
        return df
    except Exception as e:
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
    "📊 보고 자료"
])

# 탭 변수 매핑
tab_write = tabs_list[0]      # 상담일지 작성
tab_reminder = tabs_list[1]   # 미확정 리마인더
tab_report = tabs_list[2]     # 상담일지 수정
tab_integrated = tabs_list[3] # 보고 자료

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
                    
                    # 오늘의 입력 내역
                    st.subheader("📋 오늘의 입력 내역")
                    today = datetime.now().date().strftime("%Y-%m-%d")
                    today_data = updated_df[updated_df['날짜'] == today].copy()
                    
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
    try:
        df_tab2_source = conn.read(ttl="0s")
        df_tab2_source = df_tab2_source.dropna(subset=["환자성함"]).copy()
    except Exception as e:
        st.warning("⚠️ Google Sheets 연결 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        df_tab2_source = pd.DataFrame()
    
    
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
                            date_obj = datetime.strptime(current_date, "%Y-%m-%d").date()
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
                                
                                st.success(f"✅ 변경 완료!\n" + "\n".join(changes))
                                # TODO: Google Sheets 업데이트 코드 추가 필요
                        
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
            df_reminder['경과일'] = df_reminder['날짜'].apply(
                lambda x: (today - datetime.strptime(x, "%Y-%m-%d").date()).days
            )
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
    try:
        df_integrated = conn.read(ttl="0s")
        df_integrated = df_integrated.dropna(subset=["환자성함"]).copy()
        if '진단원장' not in df_integrated.columns:
            df_integrated['진단원장'] = ''
        if '리콜상태' not in df_integrated.columns:
            df_integrated['리콜상태'] = '미리콜'
    except Exception as e:
        st.warning("⚠️ Google Sheets 연결 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        df_integrated = pd.DataFrame()
    
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
            
            df_report = df_report.iloc[::-1]
            
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
