# Agent Skill Garden

[English](README.md) | [한국어](README.ko.md)

> Cursor, Claude Code, Codex의 실제 업무 흐름에서 자라난 검증 가능한 개인
> 스킬 가든

개발자가 AI 에이전트와 반복하는 업무 방식을 소수의 재사용 가능한 Agent
Skills로 만들고, 여러 도구에서 같은 원칙을 유지하며, 선택·실행·검증의 경계를
관리하는 방법을 공개한 저장소입니다.

새로운 에이전트 프레임워크를 주장하거나 비공개 설정을 그대로 덤프한 저장소가
아닙니다. 복제한 뒤 자기 업무에 맞는 부분만 남기고, 자신의 사용 근거로
계속 가꾸는 출발점입니다.

## 핵심 아이디어

우리는 이름을 붙이지 않았을 뿐, 이미 AI 에이전트에게 반복해서 맡기는 일과
선호하는 처리 방식이 있습니다. 이 저장소는 그 패턴을 발견하고 정리하게
돕습니다.

```text
실제 업무
  -> 반복 요청과 판단 발견
  -> 재사용 가능한 절차로 추출
  -> 검증하고 설치
  -> 로컬 사용 근거 관찰
  -> 집중 업무 신호 파악
  -> 유지, 개선, 병합, 정리
```

즉, 나도 모르게 자주 사용하고 있던 업무 방식을 정리할 수 있고, 그 결과를
통해 내가 실제로 집중하고 있는 업무가 무엇인지도 살펴볼 수 있습니다.

단, 이는 시간 측정이나 생산성 평가가 아닙니다. 어떤 업무 범주가 반복되는지,
어떤 스킬의 사용 근거가 있는지, 아직 구조화되지 않은 반복 업무가 무엇인지를
보여주는 개인 워크플로 관리 도구입니다.

## 복제해서 쓸 수 있는 것

- intake, 실행, 리뷰, 저장소 라이프사이클, closeout, 스킬 유지보수를 다루는 12개의 범용 스킬
- skill-first 라우팅, 변경 권한 분리, 변경 후 read-back 검증 정책
- 하나의 스킬 원본을 공유하는 Cursor, Claude Code, Codex adapter
- 기존 파일을 덮어쓰지 않고 먼저 계획을 보여주는 설치 스크립트
- 공개 안전성, 구조, context budget, unit, synthetic eval 검증
- 원문 프롬프트를 출력하지 않는 로컬 사용 감사
- 비공개 저장소를 사후 치환하는 대신 범용 지식을 처음부터 공개판으로
  작성하는 promotion 절차

## 포트폴리오로 보여주는 것

이 저장소의 경쟁력은 프롬프트 개수가 아니라 운영 판단에 있습니다.

- 반복되는 실제 업무에서 안정적인 절차를 뽑는 방법
- 범용 정책과 도구별 연결부를 분리하는 방법
- GitHub, 티켓, 메시지, 배포의 외부 변경 권한을 다루는 방법
- 완료 주장이 아니라 증거로 검증하는 방법
- 근거 없는 토큰 절감률 대신 context 증가량을 관리하는 방법
- 비공개 업무 지식을 노출하지 않으면서 재현 가능한 구성을 공개하는 방법

이 워크플로는 Cursor, Claude Code, Codex 사용 경험을 거쳐 발전했습니다.
현재 주 사용 환경은 Claude Code와 Codex이며, Cursor 경험은 발전 과정과
호환 adapter에 남아 있습니다. 정확한 범위는
[`docs/evolution.md`](docs/evolution.md)를 참고하세요.

## 저장소 구조

```text
core/
  policies/       도구와 무관한 운영 원칙
  skills/         Agent Skills 원본
adapters/
  cursor/         Cursor 규칙 및 탐색 경로 안내
  claude/         Claude Code 탐색 안내
  codex/          Codex 탐색 안내
evals/            합성 라우팅 및 안전성 사례
scripts/          설치, 감사, 검증 명령
tests/            개인정보 경계 및 이벤트 파서 테스트
docs/             구조, 적용, 개인정보, 프로젝트 결정
```

## 빈 프로젝트에서 먼저 실행하기

요구 사항은 Bash, Python 3.9+, Git, ripgrep(`rg`)입니다.

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden
./scripts/validate.sh

mkdir -p work/demo-project
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project

# 출력된 설치 계획을 확인한 뒤 적용합니다.
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --apply
```

프로젝트 설치 경로는 다음과 같습니다.

| 대상 | 프로젝트 경로 | 사용자 경로 |
| --- | --- | --- |
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Codex | `.agents/skills` | `~/.agents/skills` |
| Cursor | `.agents/skills` | `~/.agents/skills` |

Cursor와 Codex는 의도적으로 `.agents/skills`를 공유합니다. 현재
[Cursor Agent Skills 문서](https://cursor.com/docs/skills)가 이 경로를
탐색 대상으로 안내하므로 `.cursor/skills` 복제본은 만들지 않습니다.
동일한 이름의 기존 경로가 있으면 충돌로 알리고 덮어쓰지 않습니다.

설치기는 스킬 링크만 만듭니다. `adapters/`의 선택 규칙은 직접 검토해서
기존 `CLAUDE.md`, `AGENTS.md`, Cursor rules에 병합해야 합니다. 이 파일들을
자동으로 수정하지 않습니다.

기존 개인 환경에 적용하기 전에는
[상세 적용 가이드](docs/adoption.ko.md)를 먼저 읽어주세요.

## 내가 반복하는 업무 발견하기

Claude Code와 Codex의 최근 로컬 기록을 원문 외부 전송 없이 집계할 수
있습니다.

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py --days 7
```

결과를 다음 질문에 활용합니다.

- 상위 업무 범주가 내가 생각한 집중 업무와 일치하는가?
- 반복 업무에 대응하는 스킬 사용 근거가 있는가?
- 관련 없는 도구 탐색보다 스킬이 먼저 선택됐는가?
- 반복되지만 스킬 근거가 약한 업무를 새 스킬로 만들 것인가?
- 사용 근거가 없는 스킬을 개선, 병합, 정리할 것인가?

`사용 근거 없음`은 `사용한 적 없음`을 뜻하지 않습니다. 호스트별 로그가
다르고, Codex는 명시적 호출이나 `SKILL.md` 읽기를 근거로 추론합니다.
자세한 개인정보 경계는
[`docs/audit-and-privacy.md`](docs/audit-and-privacy.md)를 참고하세요.

## 토큰 절감은 측정 후 말하기

호스트와 모델마다 tokenizer가 다르므로 근거 없는 절감률을 제시하지 않습니다.
대신 이 저장소가 통제할 수 있는 catalog metadata와 필요할 때만 읽는
스킬 본문의 크기를 측정합니다.

```bash
python3 scripts/context_report.py
```

실제 토큰 수는 제공자 사용량이나 통제된 전후 비교로 확인해야 합니다. 목표는
가장 짧은 프롬프트가 아니라, 성공적으로 완료한 업무당 context 비용을 낮추는
것입니다.

## 개인정보 없이 평가하기

`evals/routing.json`에는 예상 스킬과 금지된 부작용이 적힌 합성 요청이
있습니다. 정적 검증, unit test, 합성 사례, 로컬 집계를 기본 순환으로
사용합니다. 특정 라우팅 실패가 다른 근거로 설명되지 않을 때만 제한된 원문을
익명화해서 확인합니다.

## 설계 원칙

- 공개할 수 있는 내용을 원본부터 작성하며 검색·치환으로 공개하지 않습니다.
- 공통 `SKILL.md`는 이식 가능하게, 호스트 동작은 adapter에 둡니다.
- metadata는 짧게 유지하고 상세 내용은 필요할 때만 읽습니다.
- 분석, 초안, 로컬 변경, 외부 변경의 권한을 구분합니다.
- 검증할 수 없으면 통과가 아니라 제한 사항으로 기록합니다.
- 반복 절차나 중요한 함정이 있을 때만 스킬을 추가합니다.
- 사용 근거에 따라 스킬을 개선, 병합, 정리합니다.

## 범위

이 저장소는 마켓플레이스, 범용 관측 플랫폼, 비공개 설정의 미러가 아닙니다.
또한 metadata만으로 모든 호스트가 항상 올바른 스킬을 선택한다고 보장하지
않습니다. 작고 근거 중심적인 자기 워크플로 라이브러리를 만들기 위한 복제
가능한 레퍼런스입니다.

관련 프로젝트와 이름 결정은
[`docs/positioning-and-name.md`](docs/positioning-and-name.md)를 참고하세요.

## 라이선스

MIT
