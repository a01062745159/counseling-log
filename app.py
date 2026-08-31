import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic
import pandas as pd
from datetime import datetime, timedelta
import re
import uuid
import plotly.express as px
import plotly.graph_objects as go
from calendar import monthrange

# AI 요약에 사용할 모델. 나중에 더 저렴하거나 좋은 모델이 나오면 이 값만 바꾸면 됩니다.
AI_SUMMARY_MODEL = "claude-3-5-haiku-latest"

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

# ===== 📄 시트 컬럼 순서 (Google Sheet 실제 헤더와 반드시 동일해야 함) =====
# ⚠️ 기존 시트에는 "고유ID" 컬럼이 없습니다. 이 코드를 배포하기 전에
#    migrate_add_unique_id.py를 먼저 1회 실행해서 A열에 고유ID를 추가해주세요.
SPREADSHEET_HEADER = [
    "고유ID", "날짜", "상담자", "진단원장", "환자성함", "차트번호", "분류",
    "상담결과", "금액", "주요포인트", "상담내용", "리콜상태"
]

COUNSELORS = ["오용성 실장", "서해 실장", "김지향 과장", "박승미 과장", "배지윤 팀장", "최수진 팀장"]
DOCTORS = ["안정선 대표원장", "김동현 대표원장", "이성재 수석원장", "박지호 원장", "신효담 원장", "구다솜 원장", "조수빈 원장", "조형준 원장", "강순영 원장(교정)", "윤소정 원장(교정)"]

# ===== 📋 Helper Functions (반복 코드 제거) =====
def format_amount(value):
    """금액을 정수로 변환"""
    try:
        return int(float(value)) if pd.notnull(value) else 0
    except Exception:
        return 0

def format_chart_no(value):
    """차트번호 포맷팅"""
    try:
        return str(int(float(value))) if pd.notnull(value) and str(value).strip() != '' else ""
    except Exception:
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

        confirmed_amount = int(counselor_data[counselor_data['상담결과'] == '확정']['금액_숫자'].sum())
        unconfirmed_amount = int(counselor_data[counselor_data['상담결과'] == '미확정']['금액_숫자'].sum())

        agreement_rate = (confirmed / total_count * 100) if total_count > 0 else 0

        counselor_stats_list.append({
            '상담자': counselor,
            '상담건수': total_count,
            '확정건수': confirmed,
            '미확정건수': unconfirmed,
            '동의율': f"{agreement_rate:.1f}%",
            '확정매출_숫자': confirmed_amount,
            '확정매출': f"{confirmed_amount:,}원",
            '미확정매출': f"{unconfirmed_amount:,}원"
        })

    result_df = pd.DataFrame(counselor_stats_list)
    result_df = result_df.sort_values('확정매출_숫자', ascending=False)
    result_df = result_df.drop('확정매출_숫자', axis=1)

    return result_df.reset_index(drop=True)

@st.cache_resource(show_spinner=False)
def get_ai_client():
    """secrets.toml의 [ai] anthropic_api_key로 AI 클라이언트를 만듭니다. 키가 없으면 None 반환."""
    try:
        api_key = st.secrets["ai"]["anthropic_api_key"]
    except Exception:
        return None
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


def summarize_consultation(content: str) -> str:
    """상세 상담 내용을 AI로 짧게 요약해서 '주요 포인트'용 문장을 만들어줍니다."""
    client = get_ai_client()
    if client is None:
        st.error("❌ AI 요약 기능을 쓰려면 secrets.toml에 [ai] anthropic_api_key 설정이 필요합니다.")
        return ""
    try:
        message = client.messages.create(
            model=AI_SUMMARY_MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "다음은 치과 상담 내용입니다. 상담일지의 '주요 포인트' 칸에 들어갈 수 있도록, "
                    "핵심만 한국어로 한두 문장, 최대한 짧게 요약해줘. 서론이나 설명 없이 요약 문장만 출력해줘.\n\n"
                    f"{content}"
                )
            }]
        )
        return message.content[0].text.strip()
    except Exception:
        st.error("❌ AI 요약 중 오류가 발생했습니다. API 키가 올바른지, 사용량 한도를 확인해주세요.")
        return ""


def render_consultation_detail(row, key_prefix):
    """상담 상세 내용을 보여주는 공통 렌더링 함수 (조회/보고 탭에서 중복 제거)"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**분류:** {row.get('분류', '')}")
        st.write(f"**금액:** {format_amount(row.get('금액')):,}원")
    with col2:
        st.write(f"**진단원장:** {row.get('진단원장', '')}")
        st.write(f"**차트번호:** {format_chart_no(row.get('차트번호'))}")
    with col3:
        result = row.get('상담결과', '')
        color = 'blue' if result == '확정' else 'red'
        st.markdown(f"**상담결과:** <span style='color:{color}; font-weight:bold;'>{result}</span>", unsafe_allow_html=True)

    st.markdown(f"**주요포인트:** {row.get('주요포인트', '')}")
    st.markdown(f"**상담내용:**\n\n{row.get('상담내용', '')}")


# ===== 🔌 Google Sheets 연결 (gspread 직접 사용) =====
# 새 상담 저장은 append_row로 "새 행만" 추가하고, 기존 기록 수정은 고유ID로 그 행만
# 콕 집어 update_cell 하기 때문에 여러 명이 동시에 사용해도 서로 데이터를 덮어쓸 위험이 없습니다.
# (기존 방식은 전체 시트를 읽어서 통째로 다시 쓰는 방식이라 동시 저장 시 유실 위험이 있었습니다)

@st.cache_resource(show_spinner=False)
def get_worksheet():
    """서비스 계정 인증으로 워크시트 객체를 가져옵니다. secrets.toml의 [connections.gsheets]를
    그대로 사용하므로 기존 secrets 설정을 바꿀 필요는 없습니다."""
    gs_secrets = dict(st.secrets["connections"]["gsheets"])
    spreadsheet_url = gs_secrets.pop("spreadsheet")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(gs_secrets, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(spreadsheet_url)
    return sh.sheet1


@st.cache_data(ttl=30, show_spinner=False)
def load_gsheet_data(_ws):
    """Google Sheet에서 데이터 로드 (30초 캐시 - 저장/수정 직후에는 캐시를 즉시 비워서 최신 상태를 보여줍니다)"""
    try:
        records = _ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=SPREADSHEET_HEADER)

        for col in SPREADSHEET_HEADER:
            if col not in df.columns:
                df[col] = '미리콜' if col == '리콜상태' else ''

        df = df.dropna(subset=["환자성함"]).copy()
        df = df[df['환자성함'].astype(str).str.strip() != ''].copy()

        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
        df['날짜'] = df['날짜'].fillna('')
        df['리콜상태'] = df['리콜상태'].fillna('미리콜').replace('', '미리콜')
        df['고유ID'] = df['고유ID'].astype(str).replace('nan', '')

        return df
    except Exception:
        st.warning("⚠️ Google Sheets 연결 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        return pd.DataFrame(columns=SPREADSHEET_HEADER)


def append_record(ws, record: dict):
    """새 상담 기록을 시트 맨 끝에 한 행만 추가 (기존 행은 전혀 건드리지 않음)"""
    row = [str(record.get(col, "")) for col in SPREADSHEET_HEADER]
    ws.append_row(row, value_input_option="USER_ENTERED")


def update_record_fields(ws, unique_id: str, updates: dict) -> bool:
    """고유ID로 해당 행을 찾아 지정한 컬럼(들)만 정확히 수정. 다른 행/컬럼은 건드리지 않음."""
    if not unique_id:
        return False
    try:
        id_col_num = SPREADSHEET_HEADER.index("고유ID") + 1
        cell = ws.find(unique_id, in_column=id_col_num)
    except Exception:
        cell = None
    if cell is None:
        return False
    for col_name, value in updates.items():
        col_num = SPREADSHEET_HEADER.index(col_name) + 1
        ws.update_cell(cell.row, col_num, str(value))
    return True


# ===== 🔒 로그인 기능 (기존 방식 유지) =====
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
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("📂 수려한치과 상담일지")
with header_col2:
    st.write("")
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.stats_unlocked = False
        st.rerun()

ws = get_worksheet()

# 데이터 로드
df = load_gsheet_data(ws)

# ===== 5개 탭 생성 =====
tabs_list = st.tabs([
    "📝 상담일지 작성",
    "📞 미확정 리마인더",
    "🔍 상담일지 조회/수정",
    "📊 보고 자료",
    "📈 통계"
])

tab_write = tabs_list[0]      # 상담일지 작성
tab_reminder = tabs_list[1]   # 미확정 리마인더
tab_edit = tabs_list[2]       # 상담일지 조회/수정 (구 tab_report - 이름을 실제 용도에 맞게 변경)
tab_summary = tabs_list[3]    # 보고 자료 (구 tab_integrated - 이름을 실제 용도에 맞게 변경)
tab_statistics = tabs_list[4] # 통계

# ===== TAB 1: 상담일지 작성 =====
with tab_write:
    st.header("📝 상담일지 작성")

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
    content = st.text_area("💬 상세 상담 내용", height=150, key="tab1_content")

    col_points, col_ai = st.columns([4, 1])
    with col_points:
        points = st.text_input("📍 주요 포인트", key="tab1_points")
    with col_ai:
        st.write("")
        if st.button("🤖 AI 요약", use_container_width=True, help="상세 상담 내용을 바탕으로 주요 포인트를 자동으로 채워줍니다"):
            if not content or not content.strip():
                st.warning("먼저 상세 상담 내용을 입력해주세요.")
            else:
                with st.spinner("AI가 요약하는 중..."):
                    summary = summarize_consultation(content)
                if summary:
                    st.session_state["tab1_points"] = summary
                    st.rerun()

    submitted = st.button("💾 저장하기", use_container_width=True)

    if submitted:
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
            new_record = {
                "고유ID": str(uuid.uuid4()),
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
            }
            try:
                append_record(ws, new_record)
                load_gsheet_data.clear()  # 캐시 무효화 → 다음 조회 시 최신 데이터 반영

                st.success("✅ 저장되었습니다!", icon="✅")
                st.balloons()

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

                # 입력한 날짜의 내역 (방금 저장한 내용을 화면에서 바로 보여주기 위해, 기존 df에 새 기록만 더해 표시)
                st.subheader("📋 입력 날짜 내역")
                selected_day = input_date.strftime("%Y-%m-%d")
                today_data = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
                today_data = today_data[today_data['날짜'] == selected_day].copy()

                if not today_data.empty:
                    today_data = today_data.iloc[::-1]
                    st.write(f"총 **{len(today_data)}건** 입력됨")

                    for idx, row in today_data.iterrows():
                        with st.expander(f"📌 {row['환자성함']} - {row['상담자']} ({row['상담결과']})"):
                            render_consultation_detail(row, key_prefix=f"just_saved_{idx}")

                st.divider()
                st.info("✏️ 다음 항목을 입력하기 시작하시면 위 입력칸들은 자동으로 초기화됩니다")

                # 다음 입력을 위해 폼 내용 초기화 (위젯 키를 지우면 다음 렌더링에서 빈 값으로 다시 시작함)
                for k in ["tab1_name", "tab1_chart", "tab1_points", "tab1_content",
                          "tab1_counselor", "tab1_doctor", "tab1_result"]:
                    st.session_state.pop(k, None)
                st.session_state["tab1_amount"] = 0
            except Exception:
                st.error("❌ 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

# ===== TAB 2: 미확정 상담 리마인더 =====
with tab_reminder:
    st.header("📞 미확정 상담 리마인더")

    col1, col2 = st.columns(2)
    with col1:
        reminder_counselor = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="tab2_counselor")
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

                if not df_need_recall.empty:
                    st.subheader(f"🔴 리콜 필요 ({len(df_need_recall)}명)")
                    st.divider()
                    for idx, row in df_need_recall.iterrows():
                        unique_id = row.get('고유ID', '')
                        row_key = unique_id or f"idx{idx}"
                        with st.expander(
                            f"👤 {row['환자성함']} | 차트: {format_chart_no(row['차트번호'])} | {row['경과일']}일 경과 | {format_amount(row['금액']):,}원 | ❌ {row['상담결과']} | {row['상담자']}",
                            expanded=True
                        ):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**주요포인트:** {row['주요포인트']}")
                                st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
                            with col2:
                                if not unique_id:
                                    st.caption("⚠️ 이 기록은 고유ID가 없어 상태 변경이 불가합니다. (마이그레이션 필요)")
                                elif st.button("✅ 리콜완료", key=f"recall_{row_key}", use_container_width=True):
                                    st.session_state[f"confirm_{row_key}"] = True

                            if st.session_state.get(f"confirm_{row_key}", False):
                                st.warning("정말 리콜완료 하시겠습니까?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✔️ 확인", key=f"confirm_yes_{row_key}", use_container_width=True):
                                        if update_record_fields(ws, unique_id, {"리콜상태": "리콜완료"}):
                                            load_gsheet_data.clear()
                                            st.session_state[f"confirm_{row_key}"] = False
                                            st.success("리콜 완료되었습니다!")
                                            st.rerun()
                                        else:
                                            st.error("❌ 해당 기록을 찾지 못했습니다. 새로고침 후 다시 시도해주세요.")
                                with col_no:
                                    if st.button("❌ 취소", key=f"confirm_no_{row_key}", use_container_width=True):
                                        st.session_state[f"confirm_{row_key}"] = False
                                        st.rerun()

                if not df_recalled.empty:
                    st.divider()
                    with st.expander(f"✅ 리콜 완료 ({len(df_recalled)}명)", expanded=False):
                        for idx, row in df_recalled.iterrows():
                            unique_id = row.get('고유ID', '')
                            row_key = unique_id or f"idx{idx}"
                            with st.expander(
                                f"👤 {row['환자성함']} | 차트: {format_chart_no(row['차트번호'])} | {row['경과일']}일 | {format_amount(row['금액']):,}원 | {row['상담자']}",
                                expanded=False
                            ):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**주요포인트:** {row['주요포인트']}")
                                    st.markdown(f"**상담내용:**\n\n{row['상담내용']}")
                                with col2:
                                    if not unique_id:
                                        st.caption("⚠️ 고유ID 없음 (마이그레이션 필요)")
                                    elif st.button("↩️ 리콜 재진행", key=f"undo_recall_{row_key}", use_container_width=True):
                                        st.session_state[f"confirm_undo_{row_key}"] = True

                                if st.session_state.get(f"confirm_undo_{row_key}", False):
                                    st.warning("리콜 완료를 취소하고 미리콜로 변경하시겠습니까?")
                                    col_yes, col_no = st.columns(2)
                                    with col_yes:
                                        if st.button("✔️ 확인", key=f"confirm_undo_yes_{row_key}", use_container_width=True):
                                            if update_record_fields(ws, unique_id, {"리콜상태": "미리콜"}):
                                                load_gsheet_data.clear()
                                                st.session_state[f"confirm_undo_{row_key}"] = False
                                                st.success("미리콜로 변경되었습니다!")
                                                st.rerun()
                                            else:
                                                st.error("❌ 해당 기록을 찾지 못했습니다. 새로고침 후 다시 시도해주세요.")
                                    with col_no:
                                        if st.button("❌ 취소", key=f"confirm_undo_no_{row_key}", use_container_width=True):
                                            st.session_state[f"confirm_undo_{row_key}"] = False
                                            st.rerun()
            else:
                st.info("🎉 리콜 필요한 상담이 없습니다!")
        else:
            st.info("미확정 상담이 없습니다.")
    else:
        st.info("데이터가 없습니다.")

# ===== TAB 3: 상담일지 조회/수정 =====
with tab_edit:
    st.header("🔍 상담일지 조회/수정")

    df_edit_source = load_gsheet_data(ws)

    if not df_edit_source.empty:
        st.write("환자 이름 또는 차트번호로 검색하세요. (부분 검색 가능)")
        search_patient = st.text_input("🔍 환자 이름 또는 차트번호 검색", placeholder="예: 송호선, 12345 등", key="tab_edit_search")

        if search_patient:
            df_search = df_edit_source[
                (df_edit_source['환자성함'].str.contains(search_patient, case=False, na=False)) |
                (df_edit_source['차트번호'].astype(str).str.contains(search_patient, case=False, na=False))
            ].copy()

            if not df_search.empty:
                st.success(f"✅ '{search_patient}' 검색 결과: {len(df_search)}건")
                st.divider()

                for idx, row in df_search.iterrows():
                    chart_num = format_chart_no(row['차트번호'])
                    unique_id = row.get('고유ID', '')
                    row_key = unique_id or f"idx{idx}"
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
                            current_result = row['상담결과']
                            st.write(f"**현재 상담결과:** {current_result}")
                            st.write("**상담결과 수정:**")
                            new_result = st.selectbox(
                                "변경할 상담결과 선택",
                                ["확정", "미확정"],
                                index=0 if current_result == "확정" else 1,
                                key=f"result_{row_key}"
                            )
                        with col3:
                            st.write(f"**차트번호:** {chart_num}")
                            current_date = row['날짜']
                            st.write(f"**현재 날짜:** {current_date}")
                            st.write("**날짜 수정:**")
                            date_obj = safe_parse_date(current_date) or datetime.now().date()
                            new_date = st.date_input(
                                "변경할 날짜",
                                value=date_obj,
                                key=f"date_{row_key}"
                            )

                        if not unique_id:
                            st.warning("⚠️ 이 기록은 고유ID가 없어 수정할 수 없습니다. 관리자에게 마이그레이션을 요청해주세요.")
                        else:
                            has_changes = (new_result != current_result) or (new_date != date_obj)
                            if has_changes:
                                if st.button("✅ 저장", key=f"save_{row_key}"):
                                    updates = {}
                                    changes = []
                                    if new_result != current_result:
                                        updates["상담결과"] = new_result
                                        changes.append(f"상담결과: {current_result} → {new_result}")
                                    if new_date != date_obj:
                                        updates["날짜"] = new_date.strftime('%Y-%m-%d')
                                        changes.append(f"날짜: {current_date} → {new_date.strftime('%Y-%m-%d')}")

                                    try:
                                        if update_record_fields(ws, unique_id, updates):
                                            load_gsheet_data.clear()
                                            st.success("✅ 변경사항이 저장되었습니다!\n" + "\n".join(changes))
                                            st.rerun()
                                        else:
                                            st.error("❌ 해당 기록을 찾지 못했습니다. 새로고침 후 다시 시도해주세요.")
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

# ===== TAB 4: 보고 자료 =====
with tab_summary:
    st.header("📄 상담 보고")

    df_summary_source = load_gsheet_data(ws)

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_counselor_summary = st.selectbox("👤 상담자 선택", ["전체"] + COUNSELORS, key="summary_counselor")
    with col2:
        today = datetime.now().date()
        start_date_summary = st.date_input("시작일", today, key="summary_start")
    with col3:
        end_date_summary = st.date_input("종료일", today, key="summary_end")

    if not df_summary_source.empty:
        df_report = df_summary_source.copy()
        df_report['금액_숫자'] = pd.to_numeric(df_report['금액'], errors='coerce').fillna(0)

        start_str = start_date_summary.strftime("%Y-%m-%d")
        end_str = end_date_summary.strftime("%Y-%m-%d")
        df_report = df_report[(df_report['날짜'] >= start_str) & (df_report['날짜'] <= end_str)]

        if selected_counselor_summary != "전체":
            df_report = df_report[df_report['상담자'] == selected_counselor_summary]

        if not df_report.empty:
            stats_summary = calculate_stats(df_report)
            st.subheader("📊 상담일지 통계")
            display_stats_metrics(stats_summary)

            st.divider()

            if selected_counselor_summary == "전체":
                st.subheader("👥 상담자별 매출 및 성과")
                counselor_sales_df = get_counselor_stats(df_report, COUNSELORS)
                st.dataframe(counselor_sales_df, use_container_width=True, hide_index=True)
                st.divider()

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
            st.metric("📌 상담 건수", f"{len(df_report)}건")

            # ⬇️ CSV 다운로드 (엑셀에서 한글이 깨지지 않도록 utf-8-sig 사용)
            download_cols = ['날짜', '상담자', '진단원장', '환자성함', '차트번호', '분류', '상담결과', '금액', '주요포인트', '상담내용']
            csv_bytes = df_report[download_cols].to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "⬇️ 현재 보고 자료 CSV로 다운로드",
                data=csv_bytes,
                file_name=f"상담보고_{start_str}_{end_str}.csv",
                mime="text/csv"
            )

            st.divider()

            df_report_sorted = df_report.sort_values(['날짜', '금액_숫자'], ascending=[True, False])

            st.subheader("📝 상담내용 상세")
            # 개요 표를 먼저 보여주고, 상세는 아래 expander에서 확인 (건수가 많을 때 화면이 무거워지는 것 방지)
            overview_df = df_report_sorted[['날짜', '환자성함', '차트번호', '상담자', '분류', '상담결과', '금액']].copy()
            overview_df['차트번호'] = overview_df['차트번호'].apply(format_chart_no)
            overview_df['금액'] = overview_df['금액'].apply(lambda v: f"{format_amount(v):,}원")
            st.dataframe(overview_df, use_container_width=True, hide_index=True)

            for idx, row in df_report_sorted.iterrows():
                with st.expander(f"📌 {row['날짜']} - {row['환자성함']} (차트: {format_chart_no(row['차트번호'])}) - {row['상담자']}", expanded=True):
                    render_consultation_detail(row, key_prefix=f"summary_{idx}")
        else:
            st.info("해당 기간에 상담 기록이 없습니다")

# ===== TAB 5: 통계 =====
with tab_statistics:
    st.header("📈 통계 분석")

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

    df_stats = load_gsheet_data(ws)

    if not df_stats.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            date_type = st.radio("📅 기간 선택", ["월간", "특정 기간"], horizontal=True, key="stats_date_type")

        if date_type == "월간":
            with col2:
                selected_year = st.selectbox("연도", range(2020, datetime.now().year + 1), index=datetime.now().year - 2020, key="stats_year")
            with col3:
                selected_month = st.selectbox("월", range(1, 13), index=datetime.now().month - 1, key="stats_month")
            start_date_stats = datetime(selected_year, selected_month, 1).date()
            last_day = monthrange(selected_year, selected_month)[1]
            end_date_stats = datetime(selected_year, selected_month, last_day).date()
        else:
            with col2:
                start_date_stats = st.date_input("시작일", datetime.now().date(), key="stats_start")
            with col3:
                end_date_stats = st.date_input("종료일", datetime.now().date(), key="stats_end")

        df_stats['금액_숫자'] = pd.to_numeric(df_stats['금액'], errors='coerce').fillna(0)
        df_f = filter_by_date_range(df_stats, start_date_stats, end_date_stats)

        if not df_f.empty:
            st.divider()
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
