# 환경 부트스트랩

[English](environment-bootstrap.md) | [한국어](environment-bootstrap.ko.md)

이 저장소는 특정 개인의 기기·회사 설정을 공개하지 않으면서 개인 AI 작업
환경의 이식 가능한 부분을 다시 만들기 위한 기반을 제공합니다.

## 복구하는 것

Codex 기준으로 다음 항목을 준비합니다.

- `~/.codex/AGENTS.md`: 이식 가능한 skill-first·안전 규칙
- `~/.agents/skills`: 이 저장소의 공용 스킬을 가리키는 링크
- `~/.agent-garden/profile.ini`: 로컬 경로와 활성 integration 설정

설치된 스킬은 심볼릭 링크이므로 이 저장소를 안정적인 경로에 두어야 합니다.
이후 저장소를 업데이트하면 연결된 스킬 본문도 함께 갱신됩니다.

## 복구하지 않는 것

공개 부트스트랩은 다음 항목을 복사하거나 생성하지 않습니다.

- credential, token, cookie, SSH key, connector session
- `~/.codex/config.toml`과 provider 인증 설정
- 대화 기록과 telemetry
- 회사 전용 절차, 저장소 이름, URL, 채널, 별칭
- commit, push, 발행, 메시지, 배포, 티켓 변경 권한

이 값들은 호스트가 관리하거나 로컬에만 두거나, 사용자가 소유한 비공개
저장소에서 별도로 관리해야 합니다.

## 새 환경에 설치하기

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden

./scripts/bootstrap.sh --target codex
./scripts/bootstrap.sh --target codex --apply
```

기본 실행은 dry run입니다. 기존 사용자 규칙이나 충돌하는 스킬이 발견되면
실제 변경 전에 중단합니다.

설치 후 `~/.agent-garden/profile.ini`를 수정합니다. 공개 템플릿의 모든
integration은 비활성 상태입니다. 새 환경에서 실제 사용하는 항목만 활성화한
뒤 다음 검사를 실행합니다.

```bash
python3 core/skills/environment-profile/scripts/profile_doctor.py
```

Codex를 다시 시작하고, 활성화한 integration마다 읽기 전용 요청을 하나씩
검증한 다음 외부 변경을 허용합니다.

## 비공개 백업 선택지

로컬 프로필은 개인 비공개 저장소에 백업할 수 있습니다. 비공개 저장소를
클론한 뒤 `AGENT_GARDEN_PROFILE`이 해당 파일을 가리키게 하거나, 검토한 값만
기본 사용자 프로필로 옮깁니다. 파일을 추적하기 전에 remote가 비공개인지
확인하고, 프로필에는 인증 정보를 넣지 않습니다.

```bash
AGENT_GARDEN_PROFILE="$HOME/path/to/private-profile.ini" \
  ./scripts/bootstrap.sh --target codex --apply
```

## 새 스킬을 추가할 때

모든 새 스킬은 필요에 따라 다음 네 영역으로 나눕니다.

| 종류 | 위치 |
| --- | --- |
| 재사용 가능한 판단, 절차, 안전 규칙 | `core` |
| 재사용 가능한 서비스·엔진 동작 | `integrations` |
| 실제 경로, 저장소, 브랜치, URL, workspace, 별칭 | 로컬 프로필 |
| 회사 전용 절차·용어 | private extension |

이 분류는 `workflow-maintenance`의 필수 단계입니다. 다른 사용자가 개인 경로나
서비스 식별자를 바꾸기 위해 `SKILL.md`를 직접 수정해야 한다면 아직 이식 가능한
스킬이 아닙니다.

## 기존 환경에 적용할 때

부트스트랩을 자동 병합 도구로 사용하지 않습니다. 충돌이 나오면 기존 파일과
공개 adapter를 직접 비교해 필요한 규칙만 병합합니다. 명령은 기존 파일을 대신
백업하거나 덮어쓰지 않습니다.
