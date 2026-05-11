from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client

APP_TITLE = "JW's Vocabulary"
DATA_PATH = Path("data/words.csv")
SET_SIZE = 100

USER_TABLE = "vocab_users"
RECORD_TABLE = "vocab_records"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📘",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 720px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }
        .title-box {
            text-align: center;
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: .25rem;
        }
        .sub-box {
            text-align: center;
            color: #64748b;
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
        }
        .progress-box {
            text-align: center;
            font-size: 1.65rem;
            font-weight: 800;
            margin: 1rem 0 1.5rem 0;
        }
        .question-box {
            text-align: center;
            border: 2px solid #0f172a;
            background: #d9f7df;
            color: #111827;
            border-radius: 10px;
            padding: 1.25rem;
            font-size: 1.65rem;
            font-weight: 800;
            margin-bottom: 1.5rem;
        }
        div.stButton > button {
            width: 100%;
            min-height: 3.3rem;
            border-radius: 14px;
            font-size: 1.1rem;
            font-weight: 700;
            color: #111827 !important;
            background: #e8f3ff;
            border: 2px solid #cbd5e1;
        }
        div.stButton > button:hover {
            background: #dbeafe;
            border-color: #94a3b8;
            color: #111827 !important;
        }
        .answer-wrap div.stButton > button {
            min-height: 8.5rem;
            border-radius: 26px;
            font-size: 1.45rem;
            font-weight: 800;
            white-space: normal;
            line-height: 1.5;
            padding: 1rem;
        }
        @media (max-width: 640px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .title-box { font-size: 1.85rem; }
            .sub-box { font-size: 1.05rem; }
            .progress-box { font-size: 1.5rem; }
            .question-box {
                font-size: 1.55rem;
                padding: 1.15rem;
            }
            .answer-wrap div.stButton > button {
                font-size: 1.3rem;
                min-height: 7.5rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_words() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error("data/words.csv 파일을 찾을 수 없습니다.")
        st.stop()

    df = pd.read_csv(DATA_PATH)
    required_cols = {"word", "meaning"}

    if not required_cols.issubset(set(df.columns)):
        st.error("words.csv에는 word, meaning 컬럼이 필요합니다.")
        st.stop()

    df = df.dropna(subset=["word", "meaning"]).reset_index(drop=True)

    df["id"] = range(1, len(df) + 1)
    df["word"] = df["word"].astype(str)
    df["meaning"] = df["meaning"].astype(str)
    df["set_no"] = ((df["id"] - 1) // SET_SIZE) + 1

    return df

def get_secret_value(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


def get_app_pepper() -> str:
    pepper = get_secret_value("APP_PEPPER", "")
    if not pepper:
        pepper = "local-dev-pepper-change-this"
    return pepper


def hash_password(password: str) -> str:
    value = f"{get_app_pepper()}::{password}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_week_label() -> str:
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return f"{start.month}/{start.day} ~ {end.month}/{end.day}"


@st.cache_resource
def get_supabase() -> Client:
    try:
        url = str(st.secrets["SUPABASE_URL"])
        key = str(st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error(
            "Supabase 연결 정보가 없습니다. "
            ".streamlit/secrets.toml 또는 Streamlit Cloud Secrets를 설정해주세요."
        )
        st.stop()

    return create_client(url, key)


def fetch_user(user_id: str) -> dict[str, Any] | None:
    supabase = get_supabase()
    result = (
        supabase.table(USER_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return rows[0]


def ensure_admin_user() -> None:
    admin_id = get_secret_value("ADMIN_ID", "admin")
    admin_password = get_secret_value("ADMIN_PASSWORD", "admin123")
    admin_name = get_secret_value("ADMIN_NAME", "관리자")

    if fetch_user(admin_id) is not None:
        return

    supabase = get_supabase()
    supabase.table(USER_TABLE).insert(
        {
            "user_id": admin_id,
            "password_hash": hash_password(admin_password),
            "name": admin_name,
            "role": "admin",
            "created_at": now_text(),
        }
    ).execute()


def register_user(user_id: str, password: str, name: str) -> tuple[bool, str]:
    user_id = user_id.strip()
    password = password.strip()
    name = name.strip()

    if not user_id or not password or not name:
        return False, "이름, ID, PW를 모두 입력해주세요."
    if len(user_id) < 3:
        return False, "ID는 최소 3글자 이상으로 입력해주세요."
    if len(password) < 4:
        return False, "PW는 최소 4글자 이상으로 입력해주세요."
    if fetch_user(user_id) is not None:
        return False, "이미 사용 중인 ID입니다."

    supabase = get_supabase()
    supabase.table(USER_TABLE).insert(
        {
            "user_id": user_id,
            "password_hash": hash_password(password),
            "name": name,
            "role": "student",
            "created_at": now_text(),
        }
    ).execute()
    return True, "회원가입이 완료되었습니다. 로그인해주세요."


def authenticate_user(user_id: str, password: str) -> tuple[bool, dict[str, Any] | None]:
    user = fetch_user(user_id.strip())
    if user is None:
        return False, None
    if str(user.get("password_hash", "")) != hash_password(password.strip()):
        return False, None
    return True, user


def add_record(user_id: str, name: str, set_no: int, count: int) -> None:
    supabase = get_supabase()
    supabase.table(RECORD_TABLE).insert(
        {
            "user_id": user_id,
            "name": name,
            "week": current_week_label(),
            "set_no": int(set_no),
            "word_count": int(count),
            "completed_at": now_text(),
        }
    ).execute()


def get_user_weekly_summary(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    result = (
        supabase.table(RECORD_TABLE)
        .select("week, word_count")
        .eq("user_id", user_id)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return pd.DataFrame(columns=["날짜", "총 외운 단어 수"])

    df = pd.DataFrame(rows)
    df["word_count"] = pd.to_numeric(df["word_count"], errors="coerce").fillna(0).astype(int)
    summary = (
        df.groupby("week", as_index=False)["word_count"]
        .sum()
        .rename(columns={"week": "날짜", "word_count": "총 외운 단어 수"})
    )
    return summary


def get_admin_records() -> pd.DataFrame:
    supabase = get_supabase()
    result = (
        supabase.table(RECORD_TABLE)
        .select("user_id, name, week, set_no, word_count, completed_at")
        .order("completed_at", desc=True)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return pd.DataFrame(columns=["ID", "이름", "주차", "세트", "완료 단어 수", "완료 시각"])

    df = pd.DataFrame(rows)
    result_df = df.rename(
        columns={
            "user_id": "ID",
            "name": "이름",
            "week": "주차",
            "set_no": "세트",
            "word_count": "완료 단어 수",
            "completed_at": "완료 시각",
        }
    )
    result_df["완료 단어 수"] = pd.to_numeric(result_df["완료 단어 수"], errors="coerce").fillna(0).astype(int)
    return result_df[["ID", "이름", "주차", "세트", "완료 단어 수", "완료 시각"]]


def init_session() -> None:
    defaults = {
        "logged_in": False,
        "user_id": "",
        "user_name": "",
        "user_role": "",
        "page": "login",
        "selected_set": None,
        "quiz_order": [],
        "quiz_pos": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def reset_quiz(df: pd.DataFrame, set_no: int) -> None:
    ids = df[df["set_no"] == set_no]["id"].tolist()
    random.shuffle(ids)
    st.session_state.selected_set = set_no
    st.session_state.quiz_order = ids
    st.session_state.quiz_pos = 0
    for key in list(st.session_state.keys()):
        if key.startswith("options_") or key.startswith("mode_"):
            del st.session_state[key]


def login_screen() -> None:
    st.markdown('<div class="title-box">JW\'s Vocabulary</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-box">ID와 PW를 입력하면 바로 시작합니다.</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        user_id = st.text_input("ID", placeholder="학생 ID를 입력하세요")
        password = st.text_input("PW", type="password", placeholder="비밀번호를 입력하세요")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if not user_id.strip() or not password.strip():
            st.warning("ID와 PW를 모두 입력해주세요.")
            return
        ok, user = authenticate_user(user_id, password)
        if not ok or user is None:
            st.error("ID 또는 PW가 올바르지 않습니다.")
            return
        st.session_state.logged_in = True
        st.session_state.user_id = str(user["user_id"])
        st.session_state.user_name = str(user["name"])
        st.session_state.user_role = str(user["role"])
        if st.session_state.user_role == "admin":
            go("admin")
        else:
            go("main")

    st.divider()
    if st.button("회원가입"):
        go("signup")


def signup_screen() -> None:
    st.markdown('<div class="title-box">회원가입</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-box">가입 후 같은 ID로 학습 기록을 확인할 수 있습니다.</div>', unsafe_allow_html=True)

    with st.form("signup_form"):
        name = st.text_input("이름", placeholder="이름을 입력하세요")
        user_id = st.text_input("ID", placeholder="사용할 ID를 입력하세요")
        password = st.text_input("PW", type="password", placeholder="비밀번호를 입력하세요")
        password_check = st.text_input("PW 확인", type="password", placeholder="비밀번호를 다시 입력하세요")
        submitted = st.form_submit_button("가입하기")

    if submitted:
        if password != password_check:
            st.error("PW와 PW 확인이 일치하지 않습니다.")
            return
        ok, message = register_user(user_id, password, name)
        if ok:
            st.success(message)
            if st.button("로그인 화면으로"):
                go("login")
        else:
            st.error(message)

    if st.button("로그인으로 돌아가기"):
        go("login")


def main_screen() -> None:
    st.markdown('<div class="title-box">JW\'s Vocabulary</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-box">{st.session_state.user_name}님</div>', unsafe_allow_html=True)

    if st.button("교육부 필수 어휘"):
        go("sets")
    if st.button("내 기록"):
        go("leaderboard")
    if st.session_state.user_role == "admin":
        if st.button("관리자 리더보드"):
            go("admin")
    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()


def set_screen(df: pd.DataFrame) -> None:
    total_sets = int(df["set_no"].max())
    st.markdown('<div class="title-box">교육부 필수 어휘</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-box">총 {len(df):,}개 단어 / {SET_SIZE}개 단위 세트</div>', unsafe_allow_html=True)

    selected = st.selectbox(
        "세트 선택",
        options=list(range(1, total_sets + 1)),
        format_func=lambda x: f"세트 {x}: {(x - 1) * SET_SIZE + 1} ~ {min(x * SET_SIZE, len(df))}",
    )
    st.caption("한글 뜻 맞추기와 영어 단어 맞추기가 문제마다 랜덤으로 출제됩니다.")
    if st.button("시험 시작"):
        reset_quiz(df, selected)
        go("quiz")
    if st.button("메인으로"):
        go("main")


def make_options(df: pd.DataFrame, answer_row: pd.Series, mode: str) -> list[str]:
    answer = answer_row["meaning"] if mode == "meaning" else answer_row["word"]
    pool_col = "meaning" if mode == "meaning" else "word"

    current_set_no = int(answer_row["set_no"])
    current_word_id = int(answer_row["id"])

    same_set_df = df[
        (df["set_no"] == current_set_no) &
        (df["id"] != current_word_id)
    ]

    wrong_pool = same_set_df[pool_col].dropna().astype(str).tolist()

    if not wrong_pool:
        wrong_pool = df[df["id"] != current_word_id][pool_col].dropna().astype(str).tolist()

    wrong = random.choice(wrong_pool) if wrong_pool else "오답 없음"

    options = [str(answer), str(wrong)]
    random.shuffle(options)

    return options


def quiz_screen(df: pd.DataFrame) -> None:
    if not st.session_state.quiz_order:
        go("sets")

    set_no = st.session_state.selected_set
    order = st.session_state.quiz_order
    pos = st.session_state.quiz_pos
    total = len(order)
    if pos >= total:
        go("clear")

    current_id = order[pos]
    row = df[df["id"] == current_id].iloc[0]
    progress = pos + 1

    mode_key = f"mode_{set_no}_{current_id}_{pos}"
    if mode_key not in st.session_state:
        st.session_state[mode_key] = random.choice(["meaning", "word"])
    mode = st.session_state[mode_key]

    mode_label = "한글 뜻 맞추기" if mode == "meaning" else "영어 단어 맞추기"
    st.markdown(f'<div class="sub-box">{mode_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-box">{progress} / {total}</div>', unsafe_allow_html=True)

    question = row["word"] if mode == "meaning" else row["meaning"]
    st.markdown(f'<div class="question-box">{question}</div>', unsafe_allow_html=True)

    options_key = f"options_{set_no}_{mode}_{current_id}_{pos}"
    if options_key not in st.session_state:
        st.session_state[options_key] = make_options(df, row, mode)

    answer = str(row["meaning"] if mode == "meaning" else row["word"])
    options = st.session_state[options_key]

    st.markdown('<div class="answer-wrap">', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, option in enumerate(options):
        with cols[i]:
            if st.button(str(option), key=f"pick_{i}_{current_id}_{pos}"):
                if str(option) == answer:
                    st.session_state.quiz_pos += 1
                    if st.session_state.quiz_pos >= total:
                        add_record(st.session_state.user_id, st.session_state.user_name, int(set_no), total)
                        go("clear")
                    st.rerun()
                else:
                    reset_quiz(df, int(set_no))
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("나가기"):
        go("sets")


def clear_screen(df: pd.DataFrame) -> None:
    set_no = st.session_state.selected_set
    total_sets = int(df["set_no"].max())
    start = (set_no - 1) * SET_SIZE + 1
    end = min(set_no * SET_SIZE, len(df))

    st.markdown('<div class="title-box">세트 클리어</div>', unsafe_allow_html=True)
    st.success(f"{start} ~ {end}번 단어를 완료했습니다. 기록에 반영되었습니다.")

    col1, col2 = st.columns(2)
    with col1:
        if set_no < total_sets and st.button("다음 세트로"):
            reset_quiz(df, set_no + 1)
            go("quiz")
    with col2:
        if st.button("나가기"):
            go("sets")


def leaderboard_screen() -> None:
    st.markdown('<div class="title-box">내 기록</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-box">{st.session_state.user_name}님</div>', unsafe_allow_html=True)
    summary = get_user_weekly_summary(st.session_state.user_id)
    if summary.empty:
        st.info("아직 완료한 세트가 없습니다.")
    else:
        st.table(summary)
    if st.button("메인으로"):
        go("main")


def admin_screen() -> None:
    if st.session_state.user_role != "admin":
        st.error("관리자만 접근할 수 있습니다.")
        if st.button("메인으로"):
            go("main")
        return

    st.markdown('<div class="title-box">관리자 리더보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-box">Supabase에 저장된 전체 완료 기록입니다.</div>', unsafe_allow_html=True)

    records = get_admin_records()
    if records.empty:
        st.info("아직 저장된 기록이 없습니다.")
    else:
        st.dataframe(records, use_container_width=True)
        summary = (
            records.groupby(["ID", "이름", "주차"], as_index=False)["완료 단어 수"]
            .sum()
            .sort_values(by=["주차", "완료 단어 수"], ascending=[True, False])
        )
        st.markdown("### 주차별 요약")
        st.dataframe(summary, use_container_width=True)

        csv = records.to_csv(index=False).encode("utf-8-sig")
        st.download_button("전체 기록 CSV 다운로드", csv, "jw_vocab_records.csv", "text/csv")
        summary_csv = summary.to_csv(index=False).encode("utf-8-sig")
        st.download_button("주차별 요약 CSV 다운로드", summary_csv, "jw_vocab_weekly_summary.csv", "text/csv")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("메인으로"):
            go("main")
    with col2:
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()


def main() -> None:
    inject_css()
    init_session()
    df = load_words()
    ensure_admin_user()

    page = st.session_state.page
    if not st.session_state.logged_in:
        if page == "signup":
            signup_screen()
        else:
            login_screen()
        return

    if page == "main":
        main_screen()
    elif page == "sets":
        set_screen(df)
    elif page == "quiz":
        quiz_screen(df)
    elif page == "clear":
        clear_screen(df)
    elif page == "leaderboard":
        leaderboard_screen()
    elif page == "admin":
        admin_screen()
    elif page == "signup":
        go("main")
    else:
        go("main")


if __name__ == "__main__":
    main()
