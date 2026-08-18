# 상세 적용 가이드

[English](adoption.md) | [한국어](adoption.ko.md)

한 번에 기존 개인 설정을 교체하지 마세요. 복제본 검증, 임시 프로젝트에 소수
스킬 설치, 실제 라우팅 확인을 거친 뒤 사용자 전체 설치로 넓히는 순서가
안전합니다.

## 1. 복제하고 검증하기

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden
./scripts/validate.sh
```

검증 항목은 다음과 같습니다.

- Agent Skill 필수 구조와 상대 링크
- 합성 라우팅 사례 형식
- 로컬 사용 감사 파서와 개인정보 경계
- context 문자 수 budget
- 공개 금지 패턴과 미해결 placeholder

검증 통과는 저장소 자체의 불변 조건을 확인합니다. 자연어 요청마다 호스트가
항상 올바르게 라우팅한다는 뜻은 아닙니다.

## 2. 대상과 범위 선택하기

| 옵션 | 의미 | 설치 경로 |
| --- | --- | --- |
| `--target claude` | Claude Code만 | `.claude/skills` |
| `--target codex` | Codex만 | `.agents/skills` |
| `--target cursor` | Cursor만 | `.agents/skills` |
| `--target all` | Claude와 Cursor/Codex 공용 경로 | 두 경로에 한 번씩 |
| `--scope project` | 한 프로젝트에만 | `--root` 아래 |
| `--scope user` | 관련된 모든 로컬 프로젝트 | 사용자 홈 아래 |

Cursor와 Codex는 의도적으로 `.agents/skills`를 공유합니다. `all`을 사용해도
공용 경로를 두 번 설치하지 않습니다.

## 3. 2~3개의 스킬로 시작하기

각 `SKILL.md` 상단의 `description`을 읽고 실제로 반복하는 업무만 고릅니다.
첫 세트로는 다음 구성이 무난합니다.

- `intake`: 모호한 요청을 범위가 있는 작업 단위로 정리
- `critical-review`: 배포를 막아야 할 수준의 리뷰
- `side-effect-check`: 소비처와 회귀 가능 경로 추적

반복 가능한 `--skill` 옵션으로 선택한 것만 미리 봅니다.

```bash
mkdir -p work/demo-project
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --skill intake \
  --skill critical-review \
  --skill side-effect-check
```

아직 변경하지 않는 dry run입니다. 모든 `PLAN` 행의 원본과 목적지를
확인하세요.

## 4. 덮어쓰기 없이 적용하기

같은 명령 끝에 `--apply`를 붙입니다.

```bash
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --skill intake \
  --skill critical-review \
  --skill side-effect-check \
  --apply
```

설치기는 현재 clone을 가리키는 symbolic link를 만듭니다. 따라서 clone은
안정적인 경로에 보관해야 합니다. 목적지에 같은 이름이 이미 있으면 `SKIP`으로
알리고 절대 덮어쓰지 않습니다. 양쪽 내용을 비교한 뒤 충돌을 직접
해결하세요.

전체 스킬을 설치하려면 `--skill` 옵션을 모두 생략합니다.

## 5. 호스트 규칙은 직접 병합하기

설치기는 always-on 설정을 수정하지 않습니다. 사용하는 호스트의 adapter를
검토하세요.

- Claude Code: `adapters/claude/CLAUDE.md`
- Codex: `adapters/codex/AGENTS.md`
- Cursor: `adapters/cursor/rules/agent-skill-garden.mdc`

기존 규칙과 충돌하지 않는 내용만 병합합니다. 핵심 계약은 다음과 같습니다.

1. 일반 탐색 전에 요청에 맞는 스킬을 선택합니다.
2. 요청이 분명하면 안전한 읽기 전용 단계는 바로 시작합니다.
3. 스킬 선택과 외부 변경 권한을 별개로 판단합니다.
4. 허용된 변경 뒤에는 결과 상태를 다시 읽어 검증합니다.

개인 경로, 인증 정보, 회사 규칙, 특정 호스트 문법은 공통 스킬 본문에 넣지
않습니다.

## 6. 탐색과 라우팅 확인하기

설치 후 새 에이전트 세션을 시작합니다. 최소 세 가지 요청을 시험하세요.

1. “이 diff에서 배포를 막아야 할 문제를 리뷰해줘” 같은 명확한 양성 사례
2. 평소 자신이 실제로 쓰는 자연스러운 문장
3. 비슷해 보이지만 해당 스킬을 사용하면 안 되는 음성 사례

`evals/routing.json`의 합성 사례를 참고하고 다음을 기록합니다.

- 예상 스킬과 실제 스킬
- 관련 없는 도구보다 스킬이 먼저 선택됐는지
- 금지된 외부 변경이 수행되지 않았는지
- 확인하지 못한 근거가 무엇인지

symlink가 있으면 설치 근거는 되지만 런타임 탐색 근거는 아닙니다.
`SKILL.md`를 읽었다면 로딩 근거는 되지만 작업 성공 근거는 아닙니다.

## 7. 최근 로컬 사용 감사하기

선택 기능인 감사 도구는 현재 Claude Code와 Codex의 로컬 세션 형식을
읽습니다.

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py --days 7
```

특정 호스트나 JSON 출력도 선택할 수 있습니다.

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py \
  --days 30 \
  --host codex \
  --format json
```

결과에는 집계된 업무 범주와 스킬 근거만 포함되며 프롬프트 원문은 출력하지
않습니다. 이 순환에는 외부 Grafana나 hosted telemetry가 필요하지 않습니다.

결과는 다음과 같이 해석합니다.

- 빈도가 높은 범주는 실제 집중 업무의 신호입니다.
- 반복되지만 스킬 근거가 약한 범주는 생성 또는 trigger 개선 후보입니다.
- 설치됐지만 근거가 없는 스킬은 자동 삭제가 아니라 점검 후보입니다.
- skill-first 수치가 낮으면 trigger 경쟁이나 늦은 라우팅을 살펴봅니다.

업무 범주는 keyword 기반 신호이며 시간 측정이나 생산성 평가가 아닙니다.
파서를 확장하기 전 `docs/audit-and-privacy.md`를 읽어주세요.

## 8. 한 번에 하나씩 가꾸기

반복되지만 구조화되지 않은 업무가 보이면:

1. 자신이 실제로 쓴 문장을 소수만 익명화해서 모읍니다.
2. 새 스킬을 만들지, 기존 description을 개선할지 결정합니다.
3. 안정적인 절차는 `SKILL.md`, 조건부 상세는 `references/`에 둡니다.
4. 양성·음성 합성 사례를 추가합니다.
5. `./scripts/validate.sh`를 실행합니다.
6. 라우팅 smoke test를 반복합니다.
7. 다음 로컬 감사 기간의 변화를 확인합니다.

사용 횟수만으로 스킬을 자동 변경하지 않습니다. 유지, 개선, 병합, 정리는
사람이 검토 가능한 결정으로 남깁니다.

## 9. 안정된 뒤 사용자 범위로 넓히기

먼저 preview합니다.

```bash
./scripts/install.sh \
  --target all \
  --scope user \
  --skill intake \
  --skill critical-review
```

확인 후 `--apply`를 붙여 반복합니다. 사용자 범위 경로는
`~/.claude/skills`와 `~/.agents/skills`입니다. `CLAUDE_HOME`과
`AGENTS_HOME` 환경 변수도 지원합니다.

rollback은 의도적으로 수동입니다. 설치기가 만든 정확한 symbolic link만
삭제하세요. 호스트 설정 디렉터리 전체를 재귀적으로 삭제하면 안 됩니다.

## 플랫폼 범위

스크립트는 macOS와 Ubuntu CI의 Bash/Python에서 검증합니다. Windows
native shell은 아직 검증하지 않았습니다. WSL을 사용하거나 설치기를 수정한
뒤 검증 결과와 함께 기여해 주세요.
