# 스킬을 고친 뒤 판단도 좋아졌는지 비교하기

[English / CLI 전체 계약](skill-evaluation.md)

Garden Eval은 **이 스킬 변경을 유지할 근거가 있는가**를 확인하는 작은 실행·비교
도구입니다. 사용량이나 산출량으로 생산성을 점수화하지 않습니다. 같은 조건에서
실제 응답을 남기고, 사람이 근거를 확인한 판정을 비교합니다.

기존 `validate_evals.py`는 라우팅 사례의 형식만 검사합니다. 에이전트가 스킬을
선택하거나 올바르게 행동했다는 의미가 아닙니다. 새 `scripts/skill_eval.py`는
실행·판정 기록·변경 전후 비교를 담당합니다. Python 3.9+와 POSIX 환경에서
동작하며, 저장소 검증에서는 유료 모델을 호출하지 않습니다.

## 첫 실험: critical-review

처음부터 공개용으로 작성한 합성 코드 사례 10개를 제공합니다.
검증된 벤치마크가 아닌 작은 예제 모음입니다. 입력에는 코드와 외부 계약을
제공하고, 기대하는 판정은 사람이 읽는 평가 기준에만 둡니다.

- 개선에 사용하는 calibration 6개: 권한 검사 누락, 수정 확인, 기존 문제와 새
  회귀 구분, 동작이 같은 변경, 근거 부족, 정상적인 예외 처리.
- 마지막 확인에 사용하는 holdout 4개: 파괴적인 데이터 삭제와 수정, 비밀 정보
  노출과 안전한 응답 변경.

저장소 검증은 `evals/suites/` 아래의 모든 JSON을 중첩 디렉터리까지 찾아
행동 평가 스위트로 검사하며, 잘못된 정의는 실패 처리합니다. `evals/` 최상위에는
`routing.json`만 허용하고, 다른 JSON이 있으면 이동할 위치를 안내하며 실패합니다.
다른 정의 형식은 `evals/schemas/`처럼 이름이 있는 디렉터리에 두고 각자의
검증기를 사용합니다. 응답 원문과 판정 파일은 공개 정의에 섞지 않고 gitignore
대상인 `work/`에 둡니다.

첫 비교는 `스킬 없음 → 현재 스킬`, 다음 비교는 `현재 스킬 → 수정한 스킬`입니다.
수정한 스킬에는 같은 디렉터리의 숨김 항목을 제외한 일반 UTF-8 텍스트 파일을
확장자와 관계없이 포함합니다. 이름이 `.`으로 시작하는 경로 요소는 탐색하거나
읽기 전에 제외하므로 `.env`, `.git/`, `references/.private/`는 스냅샷·프롬프트·
스킬 해시에 포함되지 않습니다. 이는 경로에 따른 경계이며 일반적인 비밀 정보
탐지 기능은 아닙니다. 보이는 참조 파일에 있는 민감한 값은 직접 제거해야 합니다.
Markdown뿐 아니라 YAML·JSON·스크립트 원문도 프롬프트와 해시 대상인
스냅샷에 들어갑니다. 스크립트는 텍스트로 제공하며 하네스가 실행하지 않습니다.
심링크·비정규 파일·NUL 바이트·유효하지 않은 UTF-8, 파일당 1,000,000바이트 초과나
전체 4,000,000바이트 초과는 해당 경로를 알리고 실행 전에 거부합니다. 크기는
원본 파일의 바이트 수 기준입니다. 숨김 항목 외의 지원하지 않는 자료를 조용히
제외하지 않습니다. 스킬을 명시적으로 공급하므로 자동 선택 성능이나 실제 도구
사용 안전성을 평가하지는 않습니다. 각 사례가 작기 때문에 실제 저장소 탐색
능력 전체를 대표하지 않습니다.

## 사용 순서

저장소 루트에서 실행합니다. 아래 `YOUR_MODEL`과 환경 설명을 실제 값으로 바꾸고,
호스트가 같은 모델과 설정을 쓰는지 확인합니다. `--model`은 기록용 선언이며
모델을 설정하는 것은 마지막 runner 명령입니다. Codex CLI는 아래 옵션을 지원하는
버전을 사용해야 합니다.

```bash
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json \
  --skill none --label baseline \
  --model YOUR_MODEL --environment 'Codex VERSION; controlled profile SETTINGS' \
  --split calibration --repeat 2 --timeout 180 \
  --out work/eval/baseline.json \
  -- codex exec --ephemeral --skip-git-repo-check \
     --sandbox read-only --model YOUR_MODEL -
```

같은 모델·명령·환경으로 현재 스킬을 실행하되 다음 인자만 바꿉니다.

```text
--skill core/skills/critical-review --label current --out work/eval/current.json
```

수정 후보는 스킬 디렉터리와 참조 파일을 `work/candidate`에 복사해 필요한
부분만 고친 뒤 다음 인자로 실행합니다.

```text
--skill work/candidate --label candidate --out work/eval/candidate.json
```

각 실행 파일에 대해 판정 템플릿을 생성합니다. 현재 스킬의 예시는 다음과 같습니다.

```bash
python3 scripts/skill_eval.py assess work/eval/current.json \
  --out work/eval/current-assessment.json
```

실행 파일의 실제 답을 읽고 판정 파일의 `reviewer`, `verdict`, `note`를 채웁니다.
`pass`와 `fail`에는 근거가 필요합니다. 확인하지 못했다면 `unjudged`로 남깁니다.
`review_minutes`는 직접 확인하는 데 쓴 시간이고, 미측정이면 `null`입니다.
baseline과 candidate에도 같은 방식으로 판정 파일을 만듭니다. 실행 파일이나
판정 파일의 기준은 직접 수정하지 않습니다. 판정 파일은 해당 실행의 해시에 연결됩니다.

스위트·실행 기록·판정 파일은 형식 버전을 따로 관리하며, 현재 각각 1·2·1입니다.
이전 버전 1 실행 기록도 저장된 필드의 검증을 통과하면 이전 형식이라는 안내와
함께 읽고 판정할 수 있습니다. 선택한 사례의 해시가 없다면 기록에 포함된
스위트로부터 메모리에서 계산하며, 원본 파일·필드·해시는 바꾸지 않습니다.
버전 1끼리는 하네스와 다른 조건이 같을 때 비교할 수 있습니다. 실행 형식이나
하네스 버전이 다른 기록은 섞어 비교하지 않으며, 새 실험에는 양쪽 조건의 기록을
새로 만듭니다.

```bash
python3 scripts/skill_eval.py compare \
  work/eval/current.json work/eval/candidate.json \
  --before-assessment work/eval/current-assessment.json \
  --after-assessment work/eval/candidate-assessment.json \
  --out work/eval/comparison.md --fail-on-regression
```

스킬 없음과 현재 스킬도 같은 방식으로 비교해 추가한 지침의 효용을 확인합니다.
스킬을 바꾼 비교에서 `fail → pass`는 개선, `pass → fail`은 퇴행입니다.
같은 스킬의 독립적인 실행을 비교하면 **SAME-SKILL VARIABILITY** 모드로
`fail_to_pass`·`pass_to_fail` 전환을 표시하며, 스킬 개선으로 부르지 않습니다.
어느 모드든 `pass → pass`는
`unchanged_pass`, `fail → fail`은 `unchanged_fail`로 나누어, 남은 실패가
단순한 ‘변화 없음’에 가려지지 않게 합니다. 실행 실패·시간 초과·미판정은
판단 불가로 표시합니다. 다른 사례가 좋아졌다고 퇴행을 평균 점수로 지우지 않습니다.
calibration과 holdout 결과, 완료/전체 실행 수, 실패를 포함한 실행 시간, 사람의
검토 시간과 측정 범위를 나눠 보여줍니다. 토큰과 금액은 현재 수집하지 않습니다.
종료 코드는 `0`이면 명령 완료, `1`이면 `--fail-on-regression`을 사용한
비교에서 판정된 pass-to-fail 전환 발견입니다. 같은 스킬의 편차 보고서에도
적용됩니다. `2`이면 잘못된 입력·비교 불가능한 실행·출력 경로
충돌입니다. 모든 판정이 `unjudged`인 리포트도 0으로 완료하지만 판단 불가로
명시하며, 품질 통과나 병합 허가를 뜻하지 않습니다.

하네스·실행 형식·모델·환경·선택한 평가 사례와 기준·runner 및 명시적 실행 파일·split·
반복 수·시간 제한·합성 여부가 다른 실행은 비교하지 않습니다. 전체 스위트는
감사를 위해 스냅샷과 해시를 남기지만, 선택하지 않은 holdout 사례를 추가해도
기존 calibration 실행의 비교를 막지 않습니다. 선택한 사례의 입력이나 판정
기준을 바꾸었다면 양쪽 조건을 새로 실행해야 합니다.
버전 2 실행은 선택한 사례를 ID 순으로 정렬해 실제 호출 순서와 비교 해시를
함께 고정합니다. 사례의 순서만 바꾸어도 같은 조건으로 비교할 수 있으며,
전체 스위트 스냅샷에는 원래 순서를 보존합니다.

두 실행의 해시는 달라야 하며, 한 실행을 자기 자신과 비교하면 거부합니다.
실행과 판정의 일반적인 편차를 보려면 같은 스킬을 독립적으로 다시 실행합니다.
예를 들어 현재 스킬을 `work/eval/current-repeat.json`에 새로 실행·판정한 뒤
`work/eval/current.json`과 각각의 판정 파일을 연결해 비교합니다. 추가 옵션 없이
같은 스킬의 편차 보고서로 표시됩니다. 디렉터리 이름만 바꾸어도 파일 내용이
같으면 같은 스킬로 봅니다.

한 응답에 대한 상반된 판정은 판정자 간 이견으로 사람이 따로 확인해야 합니다.
같은 실행을 두 번 전달해 처리하지 않습니다. 어느 비교 모드도 인과관계를
입증하지는 않으므로, 스킬 변경의 차이가 일반적인 편차보다 큰지 판단하려면
반복 실행과 사람의 검토가 필요합니다.

실행 결과를 바꾸거나 다른 실행의 판정 파일을 붙이는 실수도
해시로 검사합니다. 이는 위변조 방지나 실제 모델 버전의 원격 검증은 아닙니다.

프롬프트 JSON은 객체 키 순서를 고정하므로 입력 키의 순서만 바뀌어도 runner가
받는 바이트는 같습니다. 각 시도에는 전체 프롬프트의 `prompt_sha256`과 스킬 내용을
제외한 입력의 `input_sha256`을 따로 남깁니다. 실행 기록을 읽을 때 두 해시를 다시
검증하고, 비교할 때는 같은 사례·시도의 입력 해시가 일치하는지 확인합니다.
스킬 파일 내용에 따라 변경 효과와 동일 스킬 편차 중 보고서 모드가 정해집니다.

## 개선 루프의 경계

실제 실패를 발견하면 최소 재현 사례와 판정 기준을 만들고, 스킬을 작게 고친 뒤
기존 버전과 비교합니다. 일반적인 편차를 확인할 필요가 있으면 같은 조건을 다시
실행합니다. 마지막에는 수정에 쓰지 않은 사례로 확인합니다. 공개된
holdout은 비밀 시험지가 아니므로 이미 그 사례에 맞춰 고쳤다면 새 사례가 필요합니다.
AI가 자기 답에 매긴 점수만으로 개선을 선언하지 말고, 사람이 근거를 확인합니다.

runner는 stdin으로 프롬프트를 읽고 stdout으로 최종 답만 내는 명령입니다.
실행 파일은 `PATH`에서 찾습니다. 이후 파일 인자를 정규화하고 해시에 포함하려면
`./runner.py`나 절대경로처럼 경로 구분자를 명시해야 합니다. `exec` 같은 단어는
같은 이름의 파일이 있어도 바꾸지 않습니다. stderr는 마지막 부분을 보존하며,
응답·로그가 잘리면 기록에 표시합니다. 큰 응답과 실행 실패가 겹쳐도 시간 초과나
비정상 종료 상태가 사라지지 않습니다.

실행 파일과 명시적 파일 인자는 실험 시작 전과 종료 후에 한 번씩 해시를
검사합니다. 각 시도 전에는 장치·inode·크기·수정 시간·변경 시간·모드의 변화를
확인해 일반적인 중간 변경을 막습니다. 매번 큰 실행 파일을 다시 해시하지는 않으며,
악의적인 위변조나 adapter가 불러오는 모든 의존성을 검증하는 기능도 아닙니다.

시간 제한은 자식 프로세스가 상속한 출력 파이프에도 적용합니다. 같은 프로세스
그룹에 supervisor를 살려 두고 전용 파이프로 실제 runner의 종료 상태를 받습니다.
성공·오류·시간 초과·중단 경로 모두 그룹을 종료한 뒤 supervisor를 회수하므로,
표준 입출력만 닫고 남아 있는 후손 프로세스도 정리합니다. 기록의 `exit_code`는
실제 runner의 값이며, 종료 전에 관측하지 못했다면 `null`입니다. supervisor를
강제 종료한 코드를 runner의 결과로 대신 기록하지 않습니다. runner의 종료 코드를
먼저 관측했다면 상속된 출력 파이프가 나중에 시간 초과돼도 그 코드는 유지합니다.
예상하지 못한 supervisor 종료나 정리 실패는 오류로 처리합니다. `setsid`·`setpgid`로
그룹을 벗어나거나 권한을 바꾼 프로세스까지 통제하는 보안 샌드박스는 아니므로,
그 경계가 필요하면 runner의 격리 환경에서 통제해야 합니다.

임시 작업 디렉터리는 보안 샌드박스가 아닙니다. 읽기 전용 권한, 외부 서비스 접근,
사용자 설정과 기존 스킬의 개입은 호스트에서 통제해야 합니다. 특히 ‘스킬 없음’
조건에도 사용자 전역 스킬이 개입하면 비교가 오염됩니다. 인증과 설정은 호스트의
것을 사용하며 실제 실행은 API 비용이나 구독 사용량을 소모할 수 있습니다.

결과와 stderr에는 민감한 정보가 있을 수 있으므로 `work/`에 두고, 공개 전에
직접 확인합니다. 실행 전 입력·스냅샷·해시를 검증하고, 기존 파일을 덮어쓰지 않고
출력 파일과 `<출력 경로>.journal.jsonl`을 확보합니다. journal에는 실험 정보와
각 시도의 시작·완료, 전체 완료·실패를 추가할 때마다 디스크에 기록합니다.
출력 경로는 해당 실험만 사용해야 하며, 실행 중 다른 프로세스가 이름을 바꾸거나
교체하는 상황은 지원하지 않습니다. journal 확보 중 충돌하면 runner를 호출하지
않고, 빈 출력의 inode를 확인한 뒤 자신이 만든 예약 파일의 정리를 시도합니다.
이 확인과 삭제는 원자적이지 않으므로 동시에 경로가 교체되는 상황까지 보호하지는
못합니다.
뒤의 실행이 실패해도 앞에서 완료한 시도의 응답과 비용 근거가 남습니다.
진행 중에 중단된 시도는 시작 기록만 남을 수 있습니다. 미완료 실험은 최종 출력이
빈 파일로 남을 수 있으며, 판정·비교에는 완료된 실행 파일만 사용할 수 있습니다.
자동 재개는 지원하지 않으므로 새 출력 경로로 다시 실행하고, 중단된 실험도 비용
분석에서 빠뜨리지 않습니다.

## 비용 없는 smoke 실행

스크립트나 mock runner에는 반드시 `--synthetic`을 붙입니다. 아래 명령은 같은
고정 응답을 반환하며 실제 모델의 품질을 검증하지 않습니다. 스킬 없음과 현재
스킬을 각각 새로 실행해 두 판정 파일을 연결하는 기능만 확인합니다.

```bash
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json --skill none --label smoke-baseline \
  --model scripted --environment smoke --repeat 1 --synthetic \
  --out work/eval/smoke-baseline.json \
  -- python3 -c 'import sys; sys.stdin.read(); print("Scripted answer, not model evidence.")'
python3 scripts/skill_eval.py run \
  --suite evals/suites/critical-review.json \
  --skill core/skills/critical-review --label smoke-current \
  --model scripted --environment smoke --repeat 1 --synthetic \
  --out work/eval/smoke-current.json \
  -- python3 -c 'import sys; sys.stdin.read(); print("Scripted answer, not model evidence.")'
python3 scripts/skill_eval.py assess work/eval/smoke-baseline.json \
  --out work/eval/smoke-baseline-assessment.json
python3 scripts/skill_eval.py assess work/eval/smoke-current.json \
  --out work/eval/smoke-current-assessment.json
python3 scripts/skill_eval.py compare \
  work/eval/smoke-baseline.json work/eval/smoke-current.json \
  --before-assessment work/eval/smoke-baseline-assessment.json \
  --after-assessment work/eval/smoke-current-assessment.json \
  --out work/eval/smoke-comparison.md
```

보고서에는 **SYNTHETIC**이 표시되고, 판정 전에는 모두 판단 불가로 남습니다.
이를 실제 AI 성능 개선 결과로 인용하지 않습니다. 임의의 adapter가 실제 모델을
호출했는지는 하네스가 독립적으로 알 수 없으므로 실행자는 출처를 정확히 선언해야
합니다.
