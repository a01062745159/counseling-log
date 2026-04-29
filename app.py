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
COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장"]
DOCTORS = ["안정선 대표원장", "김동현 대표원장", "이성재 수석원장", "박지호 원장", "이동호 원장", "신효담 원장", "구다솜 원장", "강순영 원장(교정)", "윤소정 원장(교정)"]

try:
    df = conn.read(ttl="0s")
    df = df.dropna(subset=["환자성함"]).copy()
    
    # 진단원장 컬럼이 없으면 추가 (기존 데이터 호환성)
    if '진단원장' not in df.columns:
        df['진단원장'] = ''
    
    # 리콜상태 컬럼이 없으면 추가 (기존 데이터 호환성)
    if '리콜상태' not in df.columns:
        df['리콜상태'] = '미리콜'
except:
    df = pd.DataFrame(columns=EXPECTED_COLS)

# ===== 7개 탭 생성 (정렬된 순서) =====
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📝 상담일지 작성", 
    "📋 상담 기록", 
    "📄 상담 보고", 
    "👤 상담 내용 조회", 
    "📞 미확정 리마인더", 
    "📊 상담 일지 통계",
    "📥 보고자료 내려받기"
])

# ===== TAB 1: 상담일지 작성 =====
with tab1:
    st.header("📝 상담일지 작성")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        consultant = st.selectbox("👤 담당 상담자", COUNSELORS, key="tab1_counselor")
    with col2:
        doctor = st.selectbox("👨‍⚕️ 진단 원장님", DOCTORS, key="tab1_doctor")
    with col3:
        result = st.selectbox("📢 결과", ["미확정", "확정"], key="tab1_result")
    
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
        if name and content:
            new_entry = pd.DataFrame([{
                "날짜": datetime.now().strftime("%Y-%m-%d"),
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
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df[EXPECTED_COLS])
            st.success("✅ 저장되었습니다!")
            st.rerun()

# ===== TAB 2: 상담 기록 (정밀 조회) =====
with tab2:
    st.header("📋 상담 기록")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_counselor_tab2 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab2_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab2 = st.date_input("시작일", today, key="tab2_start")
    with col3:
        end_date_tab2 = st.date_input("종료일", today, key="tab2_end")
    with col4:
        search_name_tab2 = st.text_input("🔍 환자 이름 검색", placeholder="예: 송호선", key="tab2_search")
    
    if not df.empty:
        df_tab2 = df.copy()
        df_tab2['금액_숫자'] = pd.to_numeric(df_tab2['금액'], errors='coerce').fillna(0)
        
        start_str = start_date_tab2.strftime("%Y-%m-%d")
        end_str = end_date_tab2.strftime("%Y-%m-%d")
        df_tab2 = df_tab2[(df_tab2['날짜'] >= start_str) & (df_tab2['날짜'] <= end_str)]
        
        if selected_counselor_tab2 != "전체":
            df_tab2 = df_tab2[df_tab2['상담자'] == selected_counselor_tab2]
        
        if search_name_tab2:
            df_tab2 = df_tab2[df_tab2['환자성함'].str.contains(search_name_tab2, case=False, na=False)]
        
        if '금액_숫자' in df_tab2.columns:
            df_tab2 = df_tab2.drop(columns=['금액_숫자'])
        
        df_tab2 = df_tab2.iloc[::-1]
        
        if not df_tab2.empty:
            st.success(f"✅ {len(df_tab2)}건의 상담 기록")
            st.dataframe(
                df_tab2, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "금액": st.column_config.NumberColumn(format="%,d원", alignment="right"),
                    "상담내용": st.column_config.Column(width="medium")
                }
            )
        else:
            st.warning("❌ 검색 조건에 맞는 상담 기록이 없습니다.")
    else:
        st.info("조회할 데이터가 없습니다")

# ===== TAB 3: 상담 보고 (보고용) =====
with tab3:
    st.header("📄 상담 보고")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_tab3 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab3_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab3 = st.date_input("시작일", today, key="tab3_start")
    with col3:
        end_date_tab3 = st.date_input("종료일", today, key="tab3_end")
    
    if not df.empty:
        df_tab3 = df.copy()
        
        start_str = start_date_tab3.strftime("%Y-%m-%d")
        end_str = end_date_tab3.strftime("%Y-%m-%d")
        df_tab3 = df_tab3[(df_tab3['날짜'] >= start_str) & (df_tab3['날짜'] <= end_str)]
        
        if selected_counselor_tab3 != "전체":
            df_tab3 = df_tab3[df_tab3['상담자'] == selected_counselor_tab3]
        
        df_tab3 = df_tab3.iloc[::-1]
        
        st.subheader("📝 상담내용 상세")
        for idx, row in df_tab3.iterrows():
            with st.expander(f"📌 {row['날짜']} - {row['환자성함']} (차트: {int(float(row['차트번호'])) if pd.notnull(row['차트번호']) and str(row['차트번호']).strip() != '' else ''}) - {row['상담자']}", expanded=True):
                st.markdown(f"**주요포인트:** {row['주요포인트']}")
                st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
    else:
        st.info("조회할 데이터가 없습니다")

# ===== TAB 4: 상담 내용 조회 (환자 검색) =====
with tab4:
    st.header("👤 상담 내용 조회")
    
    st.write("환자 이름 또는 차트번호로 검색하세요. (부분 검색 가능)")
    search_patient = st.text_input("🔍 환자 이름 또는 차트번호 검색", placeholder="예: 송호선, 12345 등")
    
    if not df.empty:
        if search_patient:
            # 환자 이름 또는 차트번호로 검색
            df_search = df[
                (df['환자성함'].str.contains(search_patient, case=False, na=False)) | 
                (df['차트번호'].astype(str).str.contains(search_patient, case=False, na=False))
            ].copy()
            
            if not df_search.empty:
                df_search = df_search.iloc[::-1]
                
                st.success(f"✅ '{search_patient}' 검색 결과: {len(df_search)}건")
                st.divider()
                
                for idx, row in df_search.iterrows():
                    chart_num = str(int(float(row['차트번호']))) if pd.notnull(row['차트번호']) and str(row['차트번호']).strip() != '' else ""
                    with st.expander(
                        f"📌 {row['날짜']} - {row['환자성함']} (차트: {chart_num}) - {row['상담자']}", 
                        expanded=False
                    ):
                        st.markdown(f"**주요포인트:** {row['주요포인트']}")
                        st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
            else:
                st.warning(f"❌ '{search_patient}'에 해당하는 환자가 없습니다.")
        else:
            st.info("환자 이름 또는 차트번호를 입력해주세요.")
    else:
        st.info("데이터가 없습니다")

# ===== TAB 5: 미확정 상담 리마인더 =====
with tab5:
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
                            f"👤 {row['환자성함']} | 차트: {int(float(row['차트번호'])) if pd.notnull(row['차트번호']) else ''} | {row['경과일']}일 경과 | {int(float(row['금액'])):,}원 | ❌ {row['상담결과']} | {row['상담자']}", 
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
                                f"👤 {row['환자성함']} | 차트: {int(float(row['차트번호'])) if pd.notnull(row['차트번호']) else ''} | {row['경과일']}일 | {int(float(row['금액'])):,}원 | {row['상담자']}", 
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

# ===== TAB 6: 상담 일지 통계 =====
with tab6:
    st.header("📊 상담 일지 통계")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_tab6 = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab6_stat_counselor")
    with col2:
        today = datetime.now().date()
        start_date_tab6 = st.date_input("시작일", today, key="tab6_start")
    with col3:
        end_date_tab6 = st.date_input("종료일", today, key="tab6_end")
    
    if not df.empty:
        df_stats = df.copy()
        df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
        
        start_str = start_date_tab6.strftime("%Y-%m-%d")
        end_str = end_date_tab6.strftime("%Y-%m-%d")
        df_stats = df_stats[(df_stats['날짜'] >= start_str) & (df_stats['날짜'] <= end_str)]
        
        if selected_counselor_tab6 != "전체":
            df_stats = df_stats[df_stats['상담자'] == selected_counselor_tab6]
        
        if not df_stats.empty:
            total_count = len(df_stats)
            total_amount = int(df_stats['금액_숫자'].sum())
            confirmed_count = len(df_stats[df_stats['상담결과'] == '확정'])
            unconfirmed_count = len(df_stats[df_stats['상담결과'] == '미확정'])
            confirmed_amount = int(df_stats[df_stats['상담결과'] == '확정']['금액_숫자'].sum())
            unconfirmed_amount = int(df_stats[df_stats['상담결과'] == '미확정']['금액_숫자'].sum())
            agreement_rate = (confirmed_count / total_count * 100) if total_count > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📌 전체 상담건수", f"{total_count}건")
            with col2:
                st.metric("💰 총 상담액", f"{total_amount:,}원")
            with col3:
                st.metric("🎯 동의율", f"{agreement_rate:.1f}%")
            
            st.divider()
            
            col4, col5 = st.columns(2)
            with col4:
                st.subheader("✅ 확정")
                st.metric("확정 건수", f"{confirmed_count}건")
                st.metric("확정 상담액", f"{confirmed_amount:,}원")
            with col5:
                st.subheader("❌ 미확정")
                st.metric("미확정 건수", f"{unconfirmed_count}건")
                st.metric("미확정 상담액", f"{unconfirmed_amount:,}원")
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("결과별 건수")
                result_data = df_stats['상담결과'].value_counts()
                result_order = ['확정', '미확정']
                result_data = result_data.reindex(result_order, fill_value=0)
                if not result_data.empty:
                    st.bar_chart(result_data)
            
            with col_b:
                st.subheader("분류별 건수")
                category_data = df_stats['분류'].value_counts()
                category_order = ['예약 신환', '미예약 신환', '예약 구환', '미예약 구환']
                category_data = category_data.reindex(category_order, fill_value=0)
                if not category_data.empty:
                    st.bar_chart(category_data)
            
            st.divider()
            
            if selected_counselor_tab6 == "전체":
                st.subheader("👥 상담자별 매출 및 성과")
                
                counselor_stats_list = []
                for counselor in COUNSELORS:
                    counselor_data = df_stats[df_stats['상담자'] == counselor]
                    
                    total_sales = int(counselor_data['금액_숫자'].sum())
                    total_count = len(counselor_data)
                    avg_amount = int(counselor_data['금액_숫자'].mean()) if total_count > 0 else 0
                    confirmed = len(counselor_data[counselor_data['상담결과'] == '확정'])
                    unconfirmed = len(counselor_data[counselor_data['상담결과'] == '미확정'])
                    agreement_rate = (confirmed / total_count * 100) if total_count > 0 else 0
                    
                    counselor_stats_list.append({
                        '상담자': counselor,
                        '총매출': f"{total_sales:,}원",
                        '상담건수': total_count,
                        '평균금액': f"{avg_amount:,}원",
                        '확정건수': confirmed,
                        '미확정건수': unconfirmed,
                        '동의율': f"{agreement_rate:.1f}%"
                    })
                
                counselor_sales_df = pd.DataFrame(counselor_stats_list)
                st.dataframe(counselor_sales_df, use_container_width=True, hide_index=True)
                
                counselor_sales_numeric = df_stats.groupby('상담자')['금액_숫자'].sum()
                counselor_sales_numeric = counselor_sales_numeric.reindex(COUNSELORS, fill_value=0)
                st.bar_chart(counselor_sales_numeric)
        else:
            st.info("해당 기간에 상담 기록이 없습니다")
    else:
        st.info("데이터가 없습니다")

# ===== TAB 7: 보고자료 내려받기 =====
with tab7:
    st.header("📥 보고자료 내려받기")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        report_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab7_counselor")
    with col2:
        today = datetime.now().date()
        report_start_date = st.date_input("시작일", today, key="tab7_start")
    with col3:
        report_end_date = st.date_input("종료일", today, key="tab7_end")
    
    if not df.empty:
        df_report = df.copy()
        df_report['금액_숫자'] = pd.to_numeric(df_report['금액'], errors='coerce').fillna(0)
        
        start_str = report_start_date.strftime("%Y-%m-%d")
        end_str = report_end_date.strftime("%Y-%m-%d")
        df_report = df_report[(df_report['날짜'] >= start_str) & (df_report['날짜'] <= end_str)]
        
        if report_counselor != "전체":
            df_report = df_report[df_report['상담자'] == report_counselor]
        
        if not df_report.empty:
            # 통계 계산
            total_count = len(df_report)
            total_amount = int(df_report['금액_숫자'].sum())
            confirmed_count = len(df_report[df_report['상담결과'] == '확정'])
            unconfirmed_count = len(df_report[df_report['상담결과'] == '미확정'])
            confirmed_amount = int(df_report[df_report['상담결과'] == '확정']['금액_숫자'].sum())
            unconfirmed_amount = int(df_report[df_report['상담결과'] == '미확정']['금액_숫자'].sum())
            agreement_rate = (confirmed_count / total_count * 100) if total_count > 0 else 0
            
            # 상단 통계 표시
            st.subheader("📊 상담 통계")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📌 전체 상담건수", f"{total_count}건")
            with col2:
                st.metric("💰 총 상담액", f"{total_amount:,}원")
            with col3:
                st.metric("🎯 동의율", f"{agreement_rate:.1f}%")
            
            col4, col5 = st.columns(2)
            with col4:
                st.metric("✅ 확정 건수", f"{confirmed_count}건")
                st.metric("✅ 확정 상담액", f"{confirmed_amount:,}원")
            with col5:
                st.metric("❌ 미확정 건수", f"{unconfirmed_count}건")
                st.metric("❌ 미확정 상담액", f"{unconfirmed_amount:,}원")
            
            st.divider()
            
            # 상담자별 매출 및 성과
            st.subheader("👥 상담자별 매출 및 성과")
            
            if report_counselor == "전체":
                counselor_stats_list = []
                for counselor in COUNSELORS:
                    counselor_data = df_report[df_report['상담자'] == counselor]
                    
                    total_sales = int(counselor_data['금액_숫자'].sum())
                    total_count = len(counselor_data)
                    avg_amount = int(counselor_data['금액_숫자'].mean()) if total_count > 0 else 0
                    confirmed = len(counselor_data[counselor_data['상담결과'] == '확정'])
                    unconfirmed = len(counselor_data[counselor_data['상담결과'] == '미확정'])
                    agreement_rate = (confirmed / total_count * 100) if total_count > 0 else 0
                    
                    counselor_stats_list.append({
                        '상담자': counselor,
                        '총매출': f"{total_sales:,}원",
                        '상담건수': total_count,
                        '평균금액': f"{avg_amount:,}원",
                        '확정건수': confirmed,
                        '미확정건수': unconfirmed,
                        '동의율': f"{agreement_rate:.1f}%"
                    })
                
                counselor_sales_df = pd.DataFrame(counselor_stats_list)
                st.dataframe(counselor_sales_df, use_container_width=True, hide_index=True)
            else:
                st.info("전체 상담자를 선택해야 상담자별 성과를 볼 수 있습니다.")
            
            st.divider()
            
            # 상담 보고 내용
            st.subheader("📝 상담 보고 내용")
            df_report_sorted = df_report.iloc[::-1]
            
            for idx, row in df_report_sorted.iterrows():
                with st.expander(
                    f"📌 {row['날짜']} - {row['환자성함']} (차트: {int(float(row['차트번호'])) if pd.notnull(row['차트번호']) and str(row['차트번호']).strip() != '' else ''}) - {row['상담자']}", 
                    expanded=False
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**진단 원장:** {row['진단원장']}")
                        st.write(f"**분류:** {row['분류']}")
                        st.write(f"**상담결과:** {row['상담결과']}")
                    with col2:
                        st.write(f"**금액:** {int(float(row['금액'])):,}원")
                        st.write(f"**상담자:** {row['상담자']}")
                    
                    st.markdown(f"**주요포인트:** {row['주요포인트']}")
                    st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
            
            st.divider()
            
            # Excel 다운로드
            st.subheader("📥 Excel 다운로드")
            
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from io import BytesIO
                
                # Excel 파일 생성
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 1. 통계 시트
                    stats_data = {
                        '항목': ['전체 상담건수', '총 상담액', '동의율', '확정 건수', '확정 상담액', '미확정 건수', '미확정 상담액'],
                        '값': [f"{total_count}건", f"{total_amount:,}원", f"{agreement_rate:.1f}%", 
                               f"{confirmed_count}건", f"{confirmed_amount:,}원", f"{unconfirmed_count}건", f"{unconfirmed_amount:,}원"]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='통계', index=False)
                    
                    # 2. 상담자별 성과 시트
                    if report_counselor == "전체":
                        counselor_sales_df.to_excel(writer, sheet_name='상담자별성과', index=False)
                    
                    # 3. 상담 내용 시트
                    report_export_df = df_report_sorted[['날짜', '상담자', '진단원장', '환자성함', '차트번호', '분류', '상담결과', '금액', '주요포인트', '상담내용']].copy()
                    report_export_df.to_excel(writer, sheet_name='상담내용', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 Excel 파일 다운로드",
                    data=output.getvalue(),
                    file_name=f"수려한치과_상담보고_{report_start_date.strftime('%Y%m%d')}_{report_end_date.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.warning("⚠️ Excel 기능을 사용하려면 openpyxl 라이브러리가 필요합니다.")
        else:
            st.info("해당 기간에 상담 기록이 없습니다")
    else:
        st.info("데이터가 없습니다")
