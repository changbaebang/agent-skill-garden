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

- 개선에 사용하는 calibration 6개: 권한 검사 누락, 수정 확인, 기존 문제와 새
  회귀 구분, 동작이 같은 변경, 근거 부족, 정상적인 예외 처리.
- 마지막 확인에 사용하는 holdout 4개: 파괴적인 데이터 삭제와 수정, 비밀 정보
  노출과 안전한 응답 변경.

첫 비교는 `스킬 없음 → 현재 스킬`, 다음 비교는 `현재 스킬 → 수정한 스킬`입니다.
수정한 스킬에는 같은 디렉터리의 일반 UTF-8 텍스트 파일을 확장자와 관계없이
포함합니다. Markdown뿐 아니라 YAML·JSON·스크립트 원문도 프롬프트와 해시 대상인
스냅샷에 들어갑니다. 스크립트는 텍스트로 제공하며 하네스가 실행하지 않습니다.
심링크·비정규 파일·NUL 바이트·유효하지 않은 UTF-8, 파일당 1,000,000바이트 초과나
전체 4,000,000바이트 초과는 해당 경로를 알리고 실행 전에 거부합니다. 크기는
원본 파일의 바이트 수 기준입니다. 지원하지 않는 자료를 조용히 제외하지 않습니다. 스킬을
명시적으로 공급하므로 자동 선택 성능이나 실제 도구 사용 안전성을 평가하지는
않습니다. 각 사례가 작기 때문에 실제 저장소 탐색 능력 전체를 대표하지 않습니다.

## 사용 순서

저장소 루트에서 실행합니다. 아래 `YOUR_MODEL`과 환경 설명을 실제 값으로 바꾸고,
호스트가 같은 모델과 설정을 쓰는지 확인합니다. `--model`은 기록용 선언이며
모델을 설정하는 것은 마지막 runner 명령입니다. Codex CLI는 아래 옵션을 지원하는
버전을 사용해야 합니다.

```bash
python3 scripts/skill_eval.py run \
  --suite evals/critical-review.json \
  --skill core/skills/critical-review --label current \
  --model YOUR_MODEL --environment 'Codex VERSION; controlled profile SETTINGS' \
  --split calibration --repeat 2 --timeout 180 \
  --out work/eval/current.json \
  -- codex exec --ephemeral --skip-git-repo-check \
     --sandbox read-only --model YOUR_MODEL -

python3 scripts/skill_eval.py assess work/eval/current.json \
  --out work/eval/current-assessment.json
```

실행 파일의 실제 답을 읽고 판정 파일의 `reviewer`, `verdict`, `note`를 채웁니다.
`pass`와 `fail`에는 근거가 필요합니다. 확인하지 못했다면 `unjudged`로 남깁니다.
`review_minutes`는 직접 확인하는 데 쓴 시간이고, 미측정이면 `null`입니다.
수정한 스킬 디렉터리를 `work/candidate`에 준비한 뒤, 다른 출력 파일을 지정해
같은 모델·명령·환경에서 실행하고 판정합니다.

```bash
python3 scripts/skill_eval.py compare \
  work/eval/current.json work/eval/candidate.json \
  --before-assessment work/eval/current-assessment.json \
  --after-assessment work/eval/candidate-assessment.json \
  --out work/eval/comparison.md --fail-on-regression
```

`fail → pass`는 개선, `pass → fail`은 퇴행입니다. 실행 실패·시간 초과·미판정은
판단 불가로 표시합니다. 다른 사례가 좋아졌다고 퇴행을 평균 점수로 지우지 않습니다.
calibration과 holdout 결과, 완료/전체 실행 수, 실패를 포함한 실행 시간, 사람의
검토 시간과 측정 범위를 나눠 보여줍니다. 토큰과 금액은 현재 수집하지 않습니다.
종료 코드 0은 리포트 생성 성공이지 품질 통과가 아닙니다.

모델·환경·평가 사례·runner 및 명시적 실행 파일·반복 수·시간 제한이 다른 실행은
비교하지 않습니다. 실행 결과를 바꾸거나 다른 실행의 판정 파일을 붙이는 실수도
해시로 검사합니다. 이는 위변조 방지나 실제 모델 버전의 원격 검증은 아닙니다.

프롬프트 JSON은 객체 키 순서를 고정하므로 입력 키의 순서만 바뀌어도 runner가
받는 바이트는 같습니다. 각 시도에는 전체 프롬프트의 `prompt_sha256`과 스킬 내용을
제외한 입력의 `input_sha256`을 따로 남깁니다. 실행 기록을 읽을 때 두 해시를 다시
검증하고, 비교할 때는 같은 사례·시도의 입력 해시가 일치하는지 확인합니다.
스킬 내용은 전후 비교를 위해 달라질 수 있습니다.

## 개선 루프의 경계

실제 실패를 발견하면 최소 재현 사례와 판정 기준을 만들고, 스킬을 작게 고친 뒤
기존 버전과 비교합니다. 마지막에는 수정에 쓰지 않은 사례로 확인합니다. 공개된
holdout은 비밀 시험지가 아니므로 이미 그 사례에 맞춰 고쳤다면 새 사례가 필요합니다.
AI가 자기 답에 매긴 점수만으로 개선을 선언하지 말고, 사람이 근거를 확인합니다.

runner는 stdin으로 프롬프트를 읽고 stdout으로 최종 답만 내는 명령입니다.
실행 파일은 `PATH`에서 찾습니다. 이후 파일 인자를 정규화하고 해시에 포함하려면
`./runner.py`나 절대경로처럼 경로 구분자를 명시해야 합니다. `exec` 같은 단어는
같은 이름의 파일이 있어도 바꾸지 않습니다. stderr는 마지막 부분을 보존하며,
응답·로그가 잘리면 기록에 표시합니다. 큰 응답과 실행 실패가 겹쳐도 시간 초과나
비정상 종료 상태가 사라지지 않습니다.

임시 작업 디렉터리는 보안 샌드박스가 아닙니다. 읽기 전용 권한, 외부 서비스 접근,
사용자 설정과 기존 스킬의 개입은 호스트에서 통제해야 합니다. 특히 ‘스킬 없음’
조건에도 사용자 전역 스킬이 개입하면 비교가 오염됩니다. 인증과 설정은 호스트의
것을 사용하며 실제 실행은 API 비용이나 구독 사용량을 소모할 수 있습니다.

결과와 stderr에는 민감한 정보가 있을 수 있으므로 `work/`에 두고, 공개 전에
직접 확인합니다. 실행 전 입력·스냅샷·해시를 검증하고, 기존 파일을 덮어쓰지 않고
출력 파일과 `<출력 경로>.journal.jsonl`을 확보합니다. journal에는 실험 정보와
각 시도의 시작·완료, 전체 완료·실패를 추가할 때마다 디스크에 기록합니다.
뒤의 실행이 실패해도 앞에서 완료한 시도의 응답과 비용 근거가 남습니다.
진행 중에 중단된 시도는 시작 기록만 남을 수 있습니다. 미완료 실험은 최종 출력이
빈 파일로 남을 수 있으며, 판정·비교에는 완료된 실행 파일만 사용할 수 있습니다.
자동 재개는 지원하지 않으므로 새 출력 경로로 다시 실행하고, 중단된 실험도 비용
분석에서 빠뜨리지 않습니다. 기본 테스트와
[비용 없는 smoke 예제](skill-evaluation.md#no-cost-plumbing-smoke-test)는 합성
응답으로 기능만 확인합니다. 이를 실제 AI 성능 개선 결과로 인용하지 않습니다.
