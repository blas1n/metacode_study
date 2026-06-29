# 발표자 노트 (BSVibe · 7주차 최종 발표)

청중: 메타코드 부트캠프 — 학우 + 강사. 친근하지만 정확한 톤. 전문 용어는 한 번씩 풀어 설명.

**총 시간**: 발표 약 10–12분 + Q&A 5분 별도. 슬라이드 15장.

내용은 모두 `bsvibe-app` 의 실제 코드와 정렬 (`backend/api/auth/routes.py`, `backend/api/v1/messages.py`, `backend/executors/worker/{claude_code,codex,opencode}.py`, `apps/pwa/components/{shell/DirectAction,deliverables/DeliveryReport}.tsx`, `apps/pwa/lib/api/brief.ts`).

---

## 시간 배분 한눈에

| # | 슬라이드 | 시간 | 누계 |
|---|---|---:|---:|
| 1 | Cover | 0:15 | 0:15 |
| 2 | 한 사람이, 여러 제품을 | 1:00 | 1:15 |
| 3 | BSVibe 가 답하는 한 줄 | 0:45 | 2:00 |
| 4 | 어떻게 작동하나요 | 1:15 | 3:15 |
| 5 | Brief | 0:45 | 4:00 |
| 6 | Delivery Report | 1:00 | 5:00 |
| 7 | Decide | 0:40 | 5:40 |
| 8 | Safe Mode | 0:40 | 6:20 |
| 9 | Executor Worker (LLM 결합) | 1:00 | 7:20 |
| 10 | Under the hood | 0:35 | 7:55 |
| 11 | Knowledge Graph | 0:55 | 8:50 |
| 12 | 어디서든 (plugins) | 0:30 | 9:20 |
| 13 | 기술 스택 | 0:45 | 10:05 |
| 14 | 라이브 데모 cue | 1:30 | 11:35 |
| 15 | 한 줄 약속 (Closing) | 0:25 | 12:00 |

> 데모를 슬라이드 14 에서 진짜 띄울지(라이브) / 녹화로 대체할지에 따라 ±2분.

---

## 슬라이드별 멘트

### 1. Cover

> 안녕하세요. **BSVibe** 의 김동휘입니다. 한 줄 태그라인이 곧 발표 메시지예요 — "믿음이 아닌, 증명."

(짧게. 청중에 바로 다음 슬라이드로.)

### 2. 한 사람이, 여러 제품을 (Problem)

> 1인 회사를 운영하면서 제가 겪은 진짜 비용은 작업 자체보다 **컨텍스트 관리** 였어요.
> - 같은 결정을 두 번, 세 번 다시 내리고
> - AI 가 만든 결과를 처음부터 다시 검증해야 하고
> - 잡일이 진짜 일을 가립니다.
>
> 그래서 "AI 가 결과를 믿을 수 있게 돌려주기만 해도 시간이 진짜 줄어든다" 가 출발점이었어요.

### 3. BSVibe 가 답하는 한 줄 (Solution)

> 그 문제에 대한 답이 이 한 줄입니다.
> **한 줄 던지면 AI 가 일하고, 스스로 검증하고, 사람이 읽을 수 있는 증거와 함께 돌려준다. 한 번 바로잡으면 같은 실수는 두 번 없다.**
>
> 핵심 차별점 세 가지 — 검증된 결과 / 같은 실수는 한 번만 / 혼자서 여러 제품.

### 4. 어떻게 작동하나요

> 네 단계예요.
>
> 1. **던지세요** — 어디에 있든 ⌘K 나 + Direct 버튼으로 한 줄. 이메일이나 GitHub 이슈가 들어와도 자리에 없는 동안 시작돼요.
> 2. **AI 가 일합니다** — plan-act-verify 루프. 진짜 갈림길에서만 물어보고, 답을 받으면 그 자리에서 이어갑니다.
> 3. **증거를 냅니다** — "끝났다" 는 그냥 받아들이지 않아요. `verification_contract` 라는 데이터 모델에 박혀 있어서, AI 가 검사 없이 통과 처리 못 합니다.
> 4. **기억합니다** — 한 번 바로잡은 것이 쌓여서, 다음부터 같은 실수는 알아서 피해요.

### 5. Brief — 작업 한눈에

> 첫 화면이 Brief 예요. **운영 콘솔이 아니라 사람이 말하듯 설명하는 현황판**.
>
> 세 lane 으로 정리됩니다 — 진행 중인 run, 결정 대기 (갈림길 + Safe Mode 의 외부 승인 대기), 작업 이력 (끝난 work + deliverable 시간순).
>
> 처리 안 된 것이 모두 한 화면에 모이는 게 핵심. JIRA · ticket 같은 게 아니라 평범한 한국말로.

### 6. Delivery Report — 유리상자

> 결과는 한 장 짜리 Delivery Report 로 옵니다. 5블록 — masthead / Your request / What was built / How BSVibe checked / diff link.
>
> 강조 포인트: **"What was built"** 가 진짜 산출물 — 만든 파일의 CONTENT 가 곧장 인라인 표시됩니다. 그리고 **"How BSVibe checked"** 가 핵심 — `verification_contract` 에 어떤 check 가 선언됐고 그게 실제 어떻게 돌았는지 결과까지. 검증 없이 verified 라고 못 박는 길이 코드 자체에서 막혀 있어요.

### 7. Decide

> 갈림길은 두 종류예요.
> - 답이 정해진 갈림길 — AI 가 알아서 끝까지 진행
> - 취향·범위·방향 같은 founder 만 정할 수 있는 갈림길 — 그때만 올라옵니다
>
> 답하는 순간 그 자리에서 이어가요 — context switch 비용 0. 그리고 그 선택은 **resolved decision** 으로 기억돼서 다음 비슷한 케이스에 자동 재사용됩니다.

### 8. Safe Mode

> 푸시 · 머지 · 메일 발송 같은 **되돌리기 어려운 작업** 은 승인 전엔 밖으로 나가지 않아요.
> 안전한 작업은 자동, 위험한 것만 보류 — Brief 의 결정 대기 lane 에 모입니다. founder 가 진짜 신경 써야 할 결정에만 시간을 쓰도록 설계.

### 9. Executor Worker — 쓰던 LLM 그대로

> 흥미로운 부분 하나. bsvibe 는 LLM 을 자체 제공하지 않고, **founder 가 이미 쓰고 있는 CLI 도구** 를 그대로 결합합니다.
>
> 지원 도구 — Claude Code, OpenAI Codex, OpenCode. founder 머신에서 `python -m backend.executors.worker` 한 줄 띄우면 worker 가 backend 와 연결되고, 받은 작업을 founder 머신의 CLI 로 실행해요.
>
> 효과:
> - founder 의 기존 LLM 구독·세팅 (`CLAUDE.md` 같은 것) 이 그대로 살아있음
> - bsvibe 는 LLM 비용을 따로 받지 않음 (founder 가 이미 내고 있는 거니까)
> - 도구마다 강점이 다르면 작업 종류별로 워커를 다르게 띄울 수 있음
>
> 한 줄로 정리하면 — **bsvibe = dispatcher + verifier + memory. LLM 선택은 founder 의 몫.**

### 10. Under the hood

> 보이지 않는 곳에서 돌아가는 네 가지 — 실행 엔진(plan-act-verify), 비용 최적 라우팅, 안전 가드레일, 기억·개인화. 결과만 보이고 나머지는 안에서 돌아갑니다.

### 11. Knowledge Graph

> "기억합니다" 의 기술적 실체. founder 의 모든 결정과 AI 의 모든 관찰이 **하나의 지식 그래프** 로 쌓입니다.
> - 날 것의 관찰 (garden notes) 이 일정 횟수 반복되면 canonical concept 으로 승격
> - 결정과 거절된 접근이 따로 인덱싱돼 다음 작업에 자동 인용
> - **Hybrid retrieval** — vector 의미 검색 + BM25 키워드 + graph 1-hop 이웃을 RRF 로 결합
>
> 잘못 학습한 노드는 Inside 화면에서 한 클릭 retract — 30 초 안에 undo 가능.

### 12. 어디서든, 무엇과도

> 웹 기반이라 설치 없이 브라우저만 있으면 데스크톱·모바일 같은 경험.
> 실제 ship 된 plugin — GitHub, Slack, Notion, Linear, Discord, Sentry, Telegram, Trello, Email, Audit. 대부분 OAuth 한 번이면 됩니다.

### 13. 기술 스택

> 부트캠프 청중이라 빠르게: Next.js PWA + FastAPI + pgvector + NetworkX. 임베딩은 멀티링구얼 bge-m3, 생성 LLM 은 사용자 머신의 claude/codex/opencode worker (앞에서 본 그 패턴).
>
> 강조: **Hybrid retrieval (Vector + BM25 + Graph RRF)** + **verification_contract** 가 핵심 기술 자산. 인증은 Supabase GoTrue 직접 연동 (Google · GitHub OAuth). 인가는 bsvibe-app 자체 `shared/authz` 가 workspace · role 기반.

### 14. 라이브 데모 cue

> (app.bsvibe.dev 로 전환 — 가능하면 라이브, 어려우면 녹화)
>
> 다섯 흐름 보여드릴게요.
> 1. **Brief** — 진행/결정 대기/이력 한 화면
> 2. **Direct compose** — ⌘K 로 한 줄 입력 → "sent — working on it"
> 3. **Delivery Report** — Your request → What was built (파일 inline) → How BSVibe checked → diff
> 4. **Inside** — 학습된 지식 그래프 force-directed
> 5. **Retract** — 잘못 학습한 노드 한 클릭 retract → 30 초 undo toast
>
> (한 흐름당 15–25 초. 너무 길게 끌지 말 것.)

### 15. Closing — 한 줄 약속

> 다시 한 줄로 돌아가면 — **감독할 일이 시간이 지날수록 줄어듭니다.** 그게 BSVibe 의 단 하나의 약속이에요.
>
> 감사합니다. 질문 받겠습니다.

---

## Q&A 대응표

| 질문 유형 | 예상 질문 | 답안 핵심 |
|---|---|---|
| **기술** | 왜 streamlit 안 쓰고 Next.js 직접? | 모바일 PWA + i18n + 인증 모두 필요. streamlit 으로는 운영 product 불가 |
| **기술** | LLM 모델·executor 는 어떻게 골라요? | 워크스페이스가 `(executor, model)` 매트릭스 정책을 가짐 — 작업 종류 + 비용 가중치로 자동, 사용자가 덮어쓰기 가능 |
| **기술** | claude code / codex / opencode 동시에 띄울 수 있나요? | 네. founder 머신에서 worker 여러 개 띄우면 backend 가 capability 별로 dispatch — 같은 작업이 여러 워커에 동시 race 도 가능 |
| **기술** | Hybrid retrieval 의 RRF 가 뭔가요? | Reciprocal Rank Fusion — 여러 검색의 rank 를 `1/(60+rank)` 점수로 합산. 표준 RRF 논문(k=60). 세 갈래 결합 |
| **기술** | bge-m3 왜? | 한국어 질문 ↔ 영문 코드 cross-lingual 갭 줄이려고. 100+ 언어 multilingual 임베딩, 같은 의미 KO/EN 의 sim 갭이 절반 |
| **기술** | 인증은? | 백엔드가 Supabase GoTrue 직접 호출. PWA 의 `/api/auth/login` 또는 PKCE OAuth (Google/GitHub) → ES256 access token. v1 API 는 `shared/authz` 가 워크스페이스/role 기반으로 인가 |
| **제품** | 다른 founder OS (Notion AI · Granola · Reflect) 와 뭐가 달라요? | 메모/노트 도구가 아니라 **agent 가 실제 작업을 하고 그 결과에 증거가 붙는** 도구. Delivery Report 가 핵심 |
| **제품** | 진짜 1인이서 만든 거예요? 운영 비용은? | 네. Mac Mini self-host + Vercel free + Supabase free + worker 가 founder 머신의 LLM 쓰니까 LLM 비용도 별도 없음 → 월 ~10달러 (도메인 + 일부 fallback) |
| **제품** | 사용자 데이터는요? | Workspace-scoped vault — 워크스페이스 단위로 격리. 모든 vault note 와 그래프는 founder 본인 데이터. 다른 워크스페이스 접근 불가 |
| **품질** | "검증" 이 LLM-as-judge 면 그것도 환각 가능하지 않나요? | 맞아요. 그래서 verification_contract 가 **실행 가능한 검증** 을 강제 — `pytest` exit code · `ruff` 통과 · 외부 API 응답 같은 결정적 신호. LLM judge 는 보조용 |
| **품질** | 잘못된 학습 retract 하면 이전 답변은? | 새 retrieval 부터 그 노드 제외. 이전 Delivery Report 들은 그대로 (audit trail) — "이때는 이렇게 답했다" 가 보존. tombstone 만 추가 |
| **로드맵** | 출시는 언제? | 현재 self-host beta, 한 달 안에 close beta 단위로 외부 founder 5명 모집 예정 |
| **로드맵** | 가격은? | 보류 — 1인이 여러 제품 굴리는 데 맞는 단순한 가격 다듬는 중. 지금은 무료 |

---

## 시간이 모자라면 (cut order)

1. **슬라이드 12 (어디서든)** — 데모에서 보여줄 수 있음 → 30초 절약
2. **슬라이드 13 (기술 스택)** — Q&A 에서 받으면 풀기 → 45초 절약
3. **슬라이드 8 (Safe Mode)** 의 멘트 단축 — 한 줄로 "되돌리기 어려운 작업은 승인 전엔 안 나갑니다"

세 개 cut 하면 약 2분 절약 — 12분 → 10분.

## 시간이 남으면 (extend order)

1. **슬라이드 6 (Delivery Report)** 에서 실제 화면 띄워 블록 하나씩 짚기 → +30초
2. **슬라이드 9 (Executor Worker)** 에서 worker 띄우는 명령 라이브 시연 → +1분
3. **슬라이드 14 데모** 흐름 5개 → 6–7개 (한국어 질문 → 영문 코드 검색 같은 cross-lingual 사례)

---

## 발표 직전 체크리스트

- [ ] `app.bsvibe.dev` 로그인 + 데모 워크스페이스 준비 (Inside 그래프에 노드 충분히 학습)
- [ ] 데모용 워크스페이스 분리 (실수로 retract 해도 복구 쉬움)
- [ ] worker 사전 기동 (Direct submission 결과가 시연 중 도착하게)
- [ ] 마이크 + 화면 공유 사전 점검
- [ ] 비상 plan: 라이브 안 되면 사전 녹화 영상
