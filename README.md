# 단어 암기 웹사이트 - Streamlit 버전

교육부 선정 필수어휘 데이터를 기반으로 만든 모바일/태블릿 우선 Streamlit 단어 시험 웹앱입니다.

## 핵심 기능

- 간단 로그인: 회원가입 없이 ID/PW 입력 후 세션 저장
- 교육부 필수 어휘 학습
- 100단어 단위 세트 구성
- 한글 뜻 맞추기 / 영어 단어 맞추기 모드 지원
- 오답 선택 시 현재 세트 처음부터 초기화
- 세트 시작 및 초기화 시 단어 순서 랜덤 셔플
- 세트 완료 시 리더보드 반영
- 로컬 JSON 기반 리더보드 저장

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## GitHub 업로드

```bash
git init
git add .
git commit -m "Initial Streamlit word quiz app"
git branch -M main
git remote add origin https://github.com/<본인아이디>/<저장소명>.git
git push -u origin main
```

## 기본 로그인

현재 데모용으로 아무 ID/PW나 입력하면 로그인되도록 되어 있습니다. 특정 ID/PW만 허용하고 싶으면 `app.py`의 `login_screen()` 부분에서 검증 조건을 추가하면 됩니다.
