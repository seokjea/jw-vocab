# JW's Vocabulary - Supabase Version

Streamlit 기반 단어 학습 웹앱입니다. 회원가입/로그인/학습 완료 기록은 Supabase에 저장됩니다.

## 로컬 실행

```bash
cd ~/jw-vocab
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Supabase Secrets

`.streamlit/secrets.toml` 파일을 만들고 아래 형식으로 작성합니다.

```toml
SUPABASE_URL = "https://프로젝트ID.supabase.co"
SUPABASE_KEY = "Supabase API Key"
APP_PEPPER = "아무 긴 랜덤 문자열"

ADMIN_ID = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "관리자"
```

`.streamlit/secrets.toml`은 GitHub에 올리면 안 됩니다.
