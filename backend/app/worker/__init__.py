"""비동기 작업 프로세스의 공용 틀 — `python -m app.worker`(결정 0005, api.md 「워커」).

- `queue.py`: 작업 큐 소비 루프. 집는 SQL·처리·고아 회수는 도메인이 `ConsumerSpec` 으로 준다(작업 함수는 도메인 폴더에).
- `listener.py`: LISTEN 전용 접속 — API 가 보낸 `pg_notify` 로 소비자를 깨운다.
- `scheduler.py`: 주기 작업(고아 회수·만료 정리).
- `notify.py`: API 쪽이 작업 행을 만든 트랜잭션 안에서 부르는 알림.
- `settings.py`: 워커만 읽는 설정. `__main__.py`: 진입점 — 소비자·주기 작업 목록이 등록 지점이다.
"""
