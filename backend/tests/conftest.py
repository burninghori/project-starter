"""테스트 설정 선로드와 공용 plugin 등록.

`app` 을 import 하기 전에 `.env.test` 를 환경변수로 올린다. 그래야 `app.config.settings` 가
개발자의 backend/.env 가 아니라 테스트 설정으로 만들어진다.
"""

from pathlib import Path

from dotenv import load_dotenv

TEST_ENV_PATH = Path(__file__).resolve().parents[1] / ".env.test"

if not load_dotenv(TEST_ENV_PATH, override=True):
    raise RuntimeError(f"테스트 환경 파일을 읽을 수 없다: {TEST_ENV_PATH}")

pytest_plugins = (
    "tests.plugins.markers",
    "tests.plugins.db_lifecycle",
    "tests.plugins.api_client",
    "tests.plugins.storage",
    "tests.plugins.auth",
    "tests.plugins.password_cost",
)
