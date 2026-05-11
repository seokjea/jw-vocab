from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "단어 암기장"
DATA_PATH = Path("data/words.csv")
LEADERBOARD_PATH = Path("leaderboard.json")
SET_SIZE = 100

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
            margin-bottom: 1.5rem;
        }
        .progress-box {
            text-align: center;
            font-size: 1.5rem;
            font-weight: 800;
            margin: 1rem 0 1.5rem 0;
        }
        .question-box {
            text-align: center;
            border: 2px solid #0f172a;
            background: #d9f7df;
            border-radius: 10px;
            padding: 1rem;
            font-size: 1.35rem;
            font-weight: 800;
            margin-bottom: 1.5rem;
        }
        div.stButton > button {
            width: 100%;
            min-height: 3.3rem;
            border-radius: 14px;
            font-size: 1.05rem;
            font-weight: 700;
        }
        .answer-card {
            border: 2px solid #0f172a;
            background: #e8f3ff;
            border-radius: 22px;
            padding: 2.2rem .8rem;
            text-align: center;
            min-height: 110px;
            font-size: 1.1rem;
            font-weight: 800;
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
    df["id"] = df["id"].astype(int)
    df["set_no"] = ((df["id"] - 1) // SET_SIZE) + 1
    return df


def load_leaderboard() -> dict:
    if not LEADERBOARD_PATH.exists():
        return {}
    try:
        return json.loads(LEADERBOARD_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_leaderboard(data: dict) -> None:
    LEADERBOARD_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def current_week_label() -> str:
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return f"{start.month}/{start.day} ~ {end.month}/{end.day}"


def add_score(user_id: str, count: int) -> None:
    board = load_leaderboard()
    week = current_week_label()
    board.setdefault(user_id, {})
    board[user_id][week] = int(board[user_id].get(week, 0)) + int(count)
    save_leaderboard(board)


def init_session() -> None:
    defaults = {
        "logged_in": False,
        "user_id": "",
        "page": "login",
        "selected_set": None,
        "quiz_mode": None,
        "quiz_order": [],
        "quiz_pos": 0,
        "last_result": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def reset_quiz(df: pd.DataFrame, set_no: int, mode: str) -> None:
    ids = df[df["set_no"] == set_no]["id"].tolist()
    random.shuffle(ids)
    st.session_state.selected_set = set_no
    st.session_state.quiz_mode = mode
    st.session_state.quiz_order = ids
    st.session_state.quiz_pos = 0
    st.session_state.last_result = None


def login_screen() -> None:
    st.markdown('<div class="title-box">단어 암기장</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-box">ID와 PW를 입력하면 바로 시작합니다.</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        user_id = st.text_input("ID", placeholder="user_id_example")
        password = st.text_input("PW", type="password", placeholder="password_example")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if not user_id.strip() or not password.strip():
            st.warning("ID와 PW를 모두 입력해주세요.")
            return
        st.session_state.logged_in = True
        st.session_state.user_id = user_id.strip()
        go("main")


def main_screen() -> None:
    st.markdown('<div class="title-box">메인 화면</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-box">현재 사용자: <b>{st.session_state.user_id}</b></div>',
        unsafe_allow_html=True,
    )

    if st.button("교육부 필수 어휘"):
        go("sets")
    if st.button("리더보드"):
        go("leaderboard")
    if st.button("로그아웃"):
        st.session_state.clear()
        st.rerun()


def set_screen(df: pd.DataFrame) -> None:
    total_sets = int(df["set_no"].max())
    st.markdown('<div class="title-box">교육부 필수 어휘</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-box">총 {len(df):,}개 단어 / {SET_SIZE}개 단위 세트</div>',
        unsafe_allow_html=True,
    )

    selected = st.selectbox(
        "세트 선택",
        options=list(range(1, total_sets + 1)),
        format_func=lambda x: f"세트 {x}: {(x-1)*SET_SIZE+1} ~ {min(x*SET_SIZE, len(df))}",
    )

    mode = st.radio(
        "시험 방식",
        options=["meaning", "word"],
        format_func=lambda x: "한글 뜻 맞추기" if x == "meaning" else "영어 단어 맞추기",
        horizontal=True,
    )

    if st.button("시험 시작"):
        reset_quiz(df, selected, mode)
        go("quiz")

    if st.button("메인으로"):
        go("main")


def make_options(df: pd.DataFrame, answer_row: pd.Series, mode: str) -> list[str]:
    answer = answer_row["meaning"] if mode == "meaning" else answer_row["word"]
    pool_col = "meaning" if mode == "meaning" else "word"
    wrong_pool = df[df["id"] != int(answer_row["id"])][pool_col].tolist()
    wrong = random.choice(wrong_pool)
    options = [answer, wrong]
    random.shuffle(options)
    return options


def quiz_screen(df: pd.DataFrame) -> None:
    if not st.session_state.quiz_order:
        go("sets")

    set_no = st.session_state.selected_set
    mode = st.session_state.quiz_mode
    order = st.session_state.quiz_order
    pos = st.session_state.quiz_pos
    total = len(order)

    if pos >= total:
        go("clear")

    current_id = order[pos]
    row = df[df["id"] == current_id].iloc[0]
    progress = pos + 1

    st.markdown(
        f'<div class="sub-box">UI 시험창 - {"한글 뜻 맞추기" if mode == "meaning" else "영어 단어 맞추기"}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="progress-box">{progress} / {total}</div>', unsafe_allow_html=True
    )

    question = row["word"] if mode == "meaning" else row["meaning"]
    st.markdown(f'<div class="question-box">{question}</div>', unsafe_allow_html=True)

    options_key = f"options_{set_no}_{mode}_{current_id}_{pos}"
    if options_key not in st.session_state:
        st.session_state[options_key] = make_options(df, row, mode)

    answer = row["meaning"] if mode == "meaning" else row["word"]
    options = st.session_state[options_key]

    cols = st.columns(2)
    for i, option in enumerate(options):
        with cols[i]:
            st.markdown(f'<div class="answer-card">{option}</div>', unsafe_allow_html=True)
            if st.button(f"선택 {i + 1}", key=f"pick_{i}_{current_id}_{pos}"):
                if option == answer:
                    st.session_state.quiz_pos += 1
                    if st.session_state.quiz_pos >= total:
                        add_score(st.session_state.user_id, total)
                        go("clear")
                    st.rerun()
                else:
                    st.session_state.last_result = {
                        "wrong_question": question,
                        "correct_answer": answer,
                    }
                    reset_quiz(df, set_no, mode)
                    go("wrong")

    st.caption("오답을 선택하면 현재 세트가 처음부터 다시 시작됩니다.")
    if st.button("나가기"):
        go("sets")


def wrong_screen() -> None:
    st.markdown('<div class="title-box">오답입니다</div>', unsafe_allow_html=True)
    result = st.session_state.last_result
    if result:
        st.warning(f"정답: {result['correct_answer']}")
    st.write("현재 세트가 처음부터 다시 시작됩니다. 단어 순서는 다시 랜덤으로 섞였습니다.")
    if st.button("다시 시작"):
        go("quiz")
    if st.button("나가기"):
        go("sets")


def clear_screen(df: pd.DataFrame) -> None:
    set_no = st.session_state.selected_set
    total_sets = int(df["set_no"].max())
    start = (set_no - 1) * SET_SIZE + 1
    end = min(set_no * SET_SIZE, len(df))

    st.markdown('<div class="title-box">세트 클리어</div>', unsafe_allow_html=True)
    st.success(f"{start} ~ {end}번 단어를 완료했습니다. 리더보드에 반영되었습니다.")

    col1, col2 = st.columns(2)
    with col1:
        if set_no < total_sets and st.button("다음 세트로"):
            reset_quiz(df, set_no + 1, st.session_state.quiz_mode)
            go("quiz")
    with col2:
        if st.button("나가기"):
            go("sets")


def leaderboard_screen() -> None:
    st.markdown('<div class="title-box">리더보드</div>', unsafe_allow_html=True)
    board = load_leaderboard()
    user_id = st.session_state.user_id
    st.markdown(f'<div class="sub-box">{user_id}</div>', unsafe_allow_html=True)

    rows = []
    for week, count in board.get(user_id, {}).items():
        rows.append({"날짜": week, "총 외운 단어 수": count})

    if rows:
        st.table(pd.DataFrame(rows))
    else:
        st.info("아직 완료한 세트가 없습니다.")

    if st.button("메인으로"):
        go("main")


def main() -> None:
    inject_css()
    init_session()
    df = load_words()

    if not st.session_state.logged_in:
        login_screen()
        return

    page = st.session_state.page
    if page == "main":
        main_screen()
    elif page == "sets":
        set_screen(df)
    elif page == "quiz":
        quiz_screen(df)
    elif page == "wrong":
        wrong_screen()
    elif page == "clear":
        clear_screen(df)
    elif page == "leaderboard":
        leaderboard_screen()
    else:
        go("main")


if __name__ == "__main__":
    main()
