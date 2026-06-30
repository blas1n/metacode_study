---
marp: true
theme: default
size: 16:9
paginate: true
header: 'BSVibe — 믿음이 아닌, 증명.'
footer: '메타코드 부트캠프 · 최종 발표'
style: |
  section {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    padding: 52px 64px 84px;
  }
  section.cover {
    background: linear-gradient(135deg, #0a0e1a 0%, #1a2942 100%);
    color: #ffffff;
    text-align: center;
    padding-top: 140px;
  }
  section.cover h1 {
    font-size: 4.6rem;
    letter-spacing: -0.04em;
    font-weight: 800;
    margin-bottom: 24px;
  }
  section.cover .tag {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 999px;
    background: rgba(120, 180, 255, 0.18);
    color: #a9c8ff;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 24px;
  }
  section.cover .sub {
    color: #cbd5e1;
    font-size: 1.35rem;
    margin-top: 8px;
  }
  section.cover .meta {
    color: #94a3b8;
    margin-top: 56px;
    font-size: 0.95rem;
  }
  h1, h2 { letter-spacing: -0.03em; }
  h2 { font-size: 1.95rem; margin: 0 0 16px; }
  h3 { color: #1f3a8a; margin-top: 0; }
  blockquote {
    border-left: 4px solid #3b82f6;
    padding: 6px 16px;
    color: #334155;
    font-size: 1.05rem;
    background: #f1f5f9;
  }
  table { font-size: 0.88rem; border-collapse: collapse; width: 100%; }
  table th { background: #f1f5f9; }
  table th, table td { padding: 7px 10px; }
  code { background: #f1f5f9; padding: 1px 6px; border-radius: 4px; font-size: 0.85em; }
  ul, ol { margin: 8px 0; }
  li { margin: 4px 0; line-height: 1.55; }
  .lead { font-size: 1.15rem; color: #334155; line-height: 1.65; }
  .accent { color: #1d4ed8; font-weight: 700; }
  .muted { color: #64748b; font-size: 0.88rem; }
  .pillrow { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
  .pill { padding: 5px 12px; border-radius: 999px; background: #eef2ff; color: #1e3a8a; font-size: 0.85rem; font-weight: 600; }
---

<!-- _class: cover -->

<span class="tag">AI가 만들고, 검증까지</span>

# BSVibe

<p class="sub">믿음이 아닌, 증명.</p>

<p class="meta">메타코드 부트캠프 · 최종 발표<br/>김동휘 · qazasa123@gmail.com</p>

---

## 한 사람이, 여러 제품을

<div class="lead">

여러 제품을 동시에 굴리면 작업 자체보다 **컨텍스트 관리** 가 더 무거워집니다.

</div>

- 같은 결정을 두 번, 세 번 다시 내림 — 이전에 어떻게 결정했는지 흩어져 있음
- AI 가 만든 결과를 **사람이 처음부터 다시 검증** 해야 함 — "끝났다" 를 못 믿음
- 잡일이 진짜 일을 가림 — 메일 분류, 이슈 트리아지, 진행 현황 정리

> **"AI 가 일을 더 시키긴 하는데, 결과를 믿을 수 있어야 시간이 진짜 줄어든다."**

---

## BSVibe 가 답하는 한 줄

<div class="lead">

**한 줄 던지면 AI 가 일하고, 스스로 검증하고, 사람이 읽을 수 있는 증거와 함께 돌려줍니다. 한 번 바로잡으면 같은 실수는 두 번 없습니다.**

</div>

<div class="pillrow">
<span class="pill">검증된 결과</span>
<span class="pill">같은 실수는 한 번만</span>
<span class="pill">혼자서, 여러 제품</span>
</div>

<p class="muted" style="margin-top:24px">app.bsvibe.dev · 1인 founder OS</p>

---

## 어떻게 작동하나요

| 단계 | 무엇이 일어나나 |
|---|---|
| **① 던지세요** | 어디서든 ⌘K 또는 `+ Direct` 한 줄. 이메일·GitHub 이슈가 들어오면 자리에 없어도 시작 |
| **② AI 가 일합니다** | 계획·실행·검증을 스스로 반복. 갈림길에선 물어보고, 답을 받으면 그 자리에서 이어감 |
| **③ 증거를 냅니다** | "끝났다" 를 그냥 믿지 않음. 검증 계약(`verification_contract`)에 박힌 검사를 실제로 돌려 결과로 답함 |
| **④ 기억합니다** | 한 번 바로잡은 것이 쌓임. 다음부터 같은 실수는 알아서 피함 |

> 감독할 일이 시간이 지날수록 **줄어듭니다.**

---

## Brief — 작업 한눈에

운영 콘솔이 아니라, **사람이 말하듯 설명하는 현황판**. 세 lane 으로 정리:

- **진행 중 (working)** — 지금 돌고 있는 run
- **결정 대기 (needs you)** — 갈림길에서 올라온 proposal + Safe Mode 의 외부 승인 대기
- **작업 이력 (stream)** — 끝난 work + deliverable 전체 시간순

> 처리 안 된 것이 모두 한 화면에 모입니다. JIRA · ticket 이 아니라 평범한 한국말로.

---

## Delivery Report — 유리상자처럼 투명한 결과

모든 결과는 한 장 짜리 **Delivery Report** 로 도착 (한 surface 에 5블록):

| 블록 | 의미 |
|---|---|
| Masthead | 제목 + type 칩 + verdict 칩 + 날짜 |
| Your request | founder 가 던진 그 한 줄 (Direction 그대로) |
| What was built | 실제 산출물 — 파일 CONTENT 가 곧장 인라인 표시 |
| How BSVibe checked | verification contract 에 박힌 check 와 그 실행 결과 |
| Diff link | 변경된 코드로 바로 이동 |

> **검증 없이 verified 라고 못 박는 길이 코드 자체에서 막혀 있음** (`verification_contract` 가 데이터 모델로 강제).

---

## Decide — 결정이 필요할 때만 부릅니다

<div class="lead">

취향·범위·방향 같은 **혼자 정하면 안 되는 갈림길** 만 founder 에게 올라옵니다.

</div>

- 일반적인 작업은 답 안 받고 끝까지 진행
- 답하는 순간 그 자리에서 작업이 이어짐 — context switch 없음
- 그 선택은 **resolved decision** 으로 기억돼 다음 비슷한 케이스에 자동 재사용

> _"매번 같은 걸 다시 묻지 않는다"_ — Decide 의 기술적 실체.

---

## Safe Mode — 밖으로 나가는 건, 승인 후에

<div class="lead">

푸시 · 머지 · 메일 발송 · 외부 API 호출 같은 **되돌리기 어려운 작업** 은 founder 승인 전엔 밖으로 나가지 않습니다.

</div>

- 워크스페이스 정책으로 작업 분류 — 안전한 것은 자동, 위험한 것은 보류
- 보류된 작업은 Brief 의 **결정 대기** lane 에 모임
- approve / reject / approve with edit 세 선택지

> Founder 가 진짜 신경 써야 할 결정에만 시간을 쓰도록 설계 — 사고를 막는 안전망.

---

## 쓰던 LLM 도구를 그대로 — Executor Worker

<div class="lead">

bsvibe 가 LLM 을 강요하지 않습니다. **founder 머신에 이미 로그인된 CLI 도구** 를 그대로 결합:

</div>

<div class="pillrow">
<span class="pill">claude code</span>
<span class="pill">codex</span>
<span class="pill">opencode</span>
</div>

- `python -m backend.executors.worker` 한 줄로 worker 가 backend 와 연결
- 받은 작업을 founder 머신의 CLI 로 stream 실행 (NDJSON 파싱 · 타임아웃 · rate limit 재시도 처리)
- founder 의 기존 구독·세팅(`CLAUDE.md`, `settings.json`)이 그대로 살아있음 — bsvibe 가 LLM 비용을 따로 받지 않음

> bsvibe = dispatcher + verifier + memory. **LLM 선택은 founder 의 몫.**

---

## Under the hood

<style scoped>
.grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:12px; }
.card { border:1px solid #cbd5e1; border-radius:10px; padding:13px 16px; background:#f8fafc; }
.card h3 { color:#1e3a8a; font-size:1.0rem; margin:0 0 6px; }
.card p { color:#334155; font-size:0.9rem; margin:0; line-height:1.5; }
</style>

<div class="grid">
<div class="card"><h3>실행 엔진</h3><p>plan-act-verify loop. 갈림길에서 끊고, 답을 받으면 이어감.</p></div>
<div class="card"><h3>비용 최적 라우팅</h3><p>모델·executor 매트릭스에서 작업에 맞는 조합을 자동 선택.</p></div>
<div class="card"><h3>안전 가드레일</h3><p>Safe Mode · verification contract · workspace 권한 분리.</p></div>
<div class="card"><h3>기억 · 개인화</h3><p>모든 결정·관찰을 vault 에 저장 → knowledge graph 로 연결.</p></div>
</div>

---

## 기억의 구조 — Knowledge Graph

<div class="lead">

founder 가 한 모든 결정과 AI 의 모든 관찰이 **하나의 지식 그래프** 로 쌓입니다.

</div>

- **Garden notes** (날 것의 관찰) → 일정 횟수 반복되면 → **Canonical concept** 으로 승격
- **Resolved decisions** — 갈림길에서 내린 답이 future runs 에서 자동 검색
- **Negative patterns** — 거절한 접근이 다음에 같은 실수를 막음
- **Hybrid retrieval** (Vector + BM25 + Graph) 로 즉시 인용

> `Inside` 화면에서 학습한 그래프를 force-directed 로 직접 봅니다. 잘못 학습한 노드는 한 클릭 retract → 30 초 undo.

---

## 어디서든, 무엇과도

<div class="lead">

웹 기반 — **설치 없이 브라우저** 만 있으면 데스크톱·모바일 같은 경험.

</div>

쓰던 도구 그대로 연결 (실제 ship 된 plugin):

<div class="pillrow">
<span class="pill">GitHub</span>
<span class="pill">Slack</span>
<span class="pill">Notion</span>
<span class="pill">Linear</span>
<span class="pill">Discord</span>
<span class="pill">Sentry</span>
<span class="pill">Telegram</span>
<span class="pill">Trello</span>
<span class="pill">Email</span>
<span class="pill">Audit</span>
</div>

<p class="muted" style="margin-top:18px">대부분 OAuth 한 번 — 그 다음은 워크스페이스가 알아서 폴링·웹훅 처리.</p>

---

## 기술 스택 (간단)

- **Frontend**: Next.js 14 PWA (Vercel · app.bsvibe.dev)
- **Backend**: FastAPI · SQLModel · asyncpg (self-host)
- **Vector DB**: PostgreSQL + pgvector (`vector(1024)`)
- **Knowledge Graph**: NetworkX + canonicalization engine
- **Embedding**: `bge-m3` (1024d 멀티링구얼) via Ollama
- **Generation**: founder 머신의 `claude code` / `codex` / `opencode` worker
- **Retrieval**: Vector + BM25 + Graph **RRF 결합**
- **Auth**: Supabase GoTrue (Google/GitHub OAuth · ES256)
- **Authz**: bsvibe-app `shared/authz` (workspace/role 기반)
- **Infra**: 모노레포 · uv + pnpm · Docker Compose · Mac Mini self-host

---

## 라이브 데모

<div class="lead" style="text-align:center; margin-top:36px;">

**app.bsvibe.dev**

</div>

<div style="text-align:center; margin-top:24px;">

데모 흐름

1. **Brief** — 진행 중 / 결정 대기 / 작업 이력 한 화면
2. **Direct compose** — ⌘K 로 한 줄 던지기
3. **Delivery Report** — Your request → What was built → How checked → diff
4. **Inside** — 학습된 지식 그래프
5. **Retract** — 잘못된 노드 한 클릭 retract → 30 초 undo toast

</div>

---

## 한 줄 약속

<div class="lead" style="font-size:1.4rem; text-align:center; margin-top:60px;">

**감독할 일이 시간이 지날수록 줄어듭니다.**

이것이 단 하나의 약속입니다.

</div>

<p class="muted" style="text-align:center; margin-top:48px;">감사합니다 · Q&A</p>
