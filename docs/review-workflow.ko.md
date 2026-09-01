# 라우팅 기반 프론트엔드 리뷰 워크플로

리뷰 팩은 하나의 거대한 프롬프트에 섞이기 쉬운 세 가지 책임을 분리합니다.

1. `pull-request-review`는 현재 상태 확인, 리뷰 패스 선택, 기존 스레드
   재분류, 최종 판단, 게시 권한을 담당합니다.
2. `critical-review`와 `side-effect-check`는 릴리즈 차단과 영향 범위를
   가로질러 확인합니다.
3. React, TypeScript, Next.js, hygiene 스킬은 각 기술 영역을 집중적으로
   검토합니다.

이 구조는 규칙을 촘촘하게 유지하면서도 모든 PR에서 모든 체크리스트를
컨텍스트에 올리지 않게 합니다.

오케스트레이터가 필요한 패스를 모두 위임할 수 있도록 리뷰 팩은 함께
설치합니다.

```bash
./scripts/install.sh --target all --scope project --root path/to/project \
  --skill pull-request-review \
  --skill critical-review \
  --skill side-effect-check \
  --skill react-review \
  --skill typescript-review \
  --skill nextjs-review \
  --skill hygiene-review
```

dry run을 확인한 뒤 같은 명령에 `--apply`를 붙입니다.

## 선택 흐름

```text
현재 PR 상태와 diff
  -> 저장소 및 경로별 지침 확인
  -> critical-review는 항상 수행
  -> 변경 동작에 맞는 전문 패스 선택
  -> 주변 맥락과 소비처 추적
  -> 근거가 있는 finding 통합
  -> 재리뷰라면 기존 스레드 재분류
  -> 기본은 게시하지 않고 판단만 반환
```

오케스트레이터는 선택한 패스와 제외한 패스를 모두 설명합니다. 이 과정은
리뷰 범위 누락을 드러내고, 단순히 `.tsx` 파일이나 프레임워크 이름이 있다는
이유만으로 모든 규칙이 켜지는 것을 막습니다.

## 조사 근거

공개 워크플로는 반복해서 사용한 로컬 리뷰 경험을 범용적으로 다시 쓰고,
다음 1차 자료와 비교해 구성했습니다.

- [Google Engineering Practices](https://google.github.io/eng-practices/review/reviewer/looking-for.html):
  설계, 기능, 테스트, 전체 맥락, 맡은 범위의 완전한 검토, 사람 대신 코드에
  대한 코멘트
- [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review):
  저장소 공통 지침과 경로별 지침의 분리, 재리뷰에서 같은 코멘트가 반복될 수
  있다는 제약
- [PR-Agent 공개 리뷰 프롬프트](https://github.com/The-PR-Agent/pr-agent/blob/main/pr_agent/settings/pr_reviewer_prompts.toml):
  변경에서 생긴 문제, 구체적인 시나리오, 실행 가능한 제안, 불확실성 조절
- [CodeRabbit path instructions](https://docs.coderabbit.ai/configuration/path-instructions):
  경로별 집중 규칙과 generated, lock, binary, build 결과 제외
- React, TypeScript, Next.js 공식 문서: 프레임워크별 판단 근거

프롬프트 원문을 복사하지 않았습니다. 현재 diff를 기준으로 범위를 잡고,
판단 전 맥락을 조사하며, 실패 경로를 요구하고, 근거에 따라 전문 리뷰를
선택하며, 수정 결과를 실제로 검증한다는 공통 판단만 남겼습니다.

## 작성자 쪽

`review-response-loop`은 같은 대화의 나머지 절반입니다. 리뷰 워크플로가 지적을
만든다면, 이 루프는 그 지적을 닫습니다. 현재 파일을 기준으로 지적을 판정하고,
받아들인 수정은 검증하고, 반영 커밋을 명시해 답한 뒤 스레드를 닫고, 리뷰를 다시
요청하고, 감시를 다시 겁니다.

이 루프가 멈추지 않게 하는 판정이 둘 있습니다. **승인은 종료가 아닙니다** —
다시 요청한 리뷰어가 아직 답하지 않았다면 그렇습니다. 요청 목록 밖의 리뷰어는
코멘트를 열어둔 채로도 결정이 이미 승인으로 읽힐 수 있기 때문입니다. 그리고
**여러 라운드에 걸쳐 같은 지점이 오면 왕복이고, 한 라운드 안에서 여러 리뷰어가
같은 지점을 짚으면 수렴입니다.** 둘 다 스레드마다 나눠 답하지 않고 주제 전체를
덮는 코멘트 하나로 답합니다.

## 공개판과 로컬 정책의 경계

공개 스킬에는 회사 채널, 티켓 접두사, 브랜치 이름, 봇 이름, 개인 경로,
조직 전용 승인 정책을 넣지 않습니다. 프로젝트별 차이는 저장소 지침이나
경로별 로컬 프로필로 추가할 수 있습니다. GitHub 리뷰 게시도 별도의 명시적
승인이 필요한 외부 변경으로 유지합니다.
