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

여러 제품을 동시에 굴리면 작업 자체보다 **머릿속을 정리하는 일** 이 더 무거워집니다.

</div>

- 같은 결정을 두 번, 세 번 다시 내림 — 이전에 어떻게 정했는지 흩어져 있음
- AI 가 만든 결과를 **사람이 처음부터 다시 확인** 해야 함 — "끝났다" 를 못 믿음
- 잡일이 진짜 일을 가림 — 메일 분류, 이슈 정리, 진행 현황 모으기

> **"AI 가 일을 더 시키긴 하는데, 결과를 믿을 수 있어야 시간이 진짜 줄어든다."**

---

## BSVibe 가 답하는 한 줄

<div class="lead">

**한 줄 던지면 AI 가 일하고, 스스로 확인하고, 사람이 읽을 수 있는 근거와 함께 돌려줍니다. 한 번 바로잡으면 같은 실수는 두 번 없습니다.**

</div>

<div class="pillrow">
<span class="pill">검증된 결과</span>
<span class="pill">같은 실수는 한 번만</span>
<span class="pill">혼자서, 여러 제품</span>
</div>

<p class="muted" style="margin-top:24px">app.bsvibe.dev</p>

---

## 어떻게 작동하나요

| 단계 | 무엇이 일어나나 |
|---|---|
| **① 던지세요** | **다이렉트** 버튼으로 한 줄. 메일·GitHub 이슈가 들어오면 자리에 없어도 시작 |
| **② AI 가 일합니다** | 계획·실행·확인을 스스로 반복. 갈림길에선 물어보고, 답을 받으면 그 자리에서 이어감 |
| **③ 근거를 냅니다** | "끝났다" 를 그냥 믿지 않음. 어떤 방법으로 어떻게 확인했는지 결과까지 함께 |
| **④ 기억합니다** | 한 번 바로잡은 것이 쌓임. 다음부터 같은 실수는 알아서 피함 |

> 감독할 일이 시간이 지날수록 **줄어듭니다.**

---

## 요약 — 작업 한눈에

운영 콘솔이 아니라, **사람이 말하듯 설명하는 현황판**. 세 줄로 정리:

- **지금 작업 중** — 돌고 있는 일
- **결정 대기** — 갈림길에서 올라온 안건, 그리고 밖으로 내보내기 전 승인 대기
- **지난 작업** — 끝난 일과 전달물이 시간 순서대로

> 처리 안 된 것이 모두 한 화면에 모입니다. 티켓 같은 게 아니라 평범한 한국말로.

---

## 전달물 리포트 — 유리상자처럼 투명한 결과

모든 결과는 한 장 짜리 **전달물 리포트** 로 도착 (다섯 블록):

| 블록 | 의미 |
|---|---|
| 헤더 | 제목 · 유형 · 판정(통과/실패) · 날짜 |
| 요청 | 내가 던졌던 그 한 줄 그대로 |
| 만든 것 | 실제로 만든 파일 내용이 곧장 화면에 |
| 어떻게 확인했나 | 어떤 검사를 약속했고 그 검사를 돌린 결과 |
| 변경 코드 | 코드 변경 내역으로 바로 이동 |

> **확인 없이 "통과" 라고 못 박는 길이 코드 자체에서 막혀 있음** — "이 작업은 이렇게 확인하겠다" 가 데이터로 강제됩니다.

---

## 결정 — 필요할 때만 부릅니다

<div class="lead">

취향·범위·방향 같은 **혼자 정하면 안 되는 갈림길** 만 사용자에게 올라옵니다. AI 가 단순히 묻기만 하는 게 아니라 **답안 후보까지 같이 제안** 합니다.

</div>

- AI 가 갈림길을 발견하면 후보 답안을 만들어 제시 — "이렇게 하면 어떨까요?"
- 사용자는 후보 중 하나를 고르거나 **직접 입력** 으로 답
- 답하는 순간 그 자리에서 작업이 이어짐 — 다른 화면으로 옮길 필요 없음
- 그 선택은 **결정 답안** 으로 기억돼 다음 비슷한 케이스에 자동 재사용

> _"매번 같은 걸 다시 묻지 않는다"_ — 결정 화면의 기술적 실체.

---

## 안전 모드 — 밖으로 나가는 건, 승인 후에

<div class="lead">

푸시 · 머지 · 메일 발송 · 외부 호출 같은 **되돌리기 어려운 작업** 은 사용자 승인 전엔 밖으로 나가지 않습니다.

</div>

- 작업 공간마다 정책으로 분류 — 안전한 것은 자동, 위험한 것은 보류
- 보류된 작업은 요약 화면의 **결정 대기** 줄에 모임
- 통과 / 거절 / 수정 후 통과 세 선택지

> 사용자가 진짜 신경 써야 할 결정에만 시간을 쓰도록 — 사고를 막는 안전망.

---

## 쓰던 LLM 도구를 그대로

<div class="lead">

bsvibe 가 LLM 을 강요하지 않습니다. **사용자가 이미 깔아 쓰는 도구** 를 그대로 결합:

</div>

<div class="pillrow">
<span class="pill">claude code</span>
<span class="pill">codex</span>
<span class="pill">opencode</span>
</div>

- 한 줄 명령으로 내 컴퓨터에 작은 도우미(worker) 를 띄우면 bsvibe 와 연결
- 받은 작업을 내 컴퓨터의 도구로 실행해 결과를 stream 으로 돌려보냄 — 시간 초과·횟수 제한 다 처리
- 내가 이미 쓰던 구독·세팅이 그대로 살아있음 — **bsvibe 가 LLM 비용을 따로 받지 않음**

> bsvibe = 작업 배분 + 결과 확인 + 기억. **LLM 선택은 사용자의 몫.**

---

## 안에서 어떻게 굴러가나

<style scoped>
.arch { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-top:2px; }
.arch .col { border:1px solid #cbd5e1; border-radius:10px; padding:10px 14px; background:#f8fafc; }
.arch .col h3 { color:#1e3a8a; font-size:0.92rem; margin:0 0 5px; }
.arch .col p { color:#334155; font-size:0.82rem; margin:1px 0; line-height:1.4; }
.flow { border-top:1px dashed #cbd5e1; padding-top:10px; margin-top:12px; }
.flow p { color:#334155; font-size:0.85rem; line-height:1.5; margin:2px 0; }
.step { display:inline-block; background:#eef2ff; color:#1e3a8a; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:999px; margin-right:5px; }
</style>

<div class="arch">
<div class="col">
<h3>프론트 (화면)</h3>
<p>Next.js PWA — 모바일 우선</p>
<p>요약 · 결정 · 지식 · 리포트</p>
</div>
<div class="col">
<h3>백엔드 (파이프라인)</h3>
<p>FastAPI + 백그라운드 워커</p>
<p>인테이크 → 프레이밍 → 실행 → 검증 → 전달</p>
</div>
<div class="col">
<h3>저장소 (기억)</h3>
<p>PostgreSQL — 사실·상태·감사</p>
<p>pgvector — 의미 검색</p>
<p>NetworkX — 지식 그래프</p>
</div>
</div>

<div class="flow">
<p><span class="step">1</span> <b>다이렉트</b> 로 한 줄 → 인테이크</p>
<p><span class="step">2</span> 백엔드 <b>프레이밍</b> → 지식 답변 vs 실행 분기 · 작업에 맞는 도구 라우팅</p>
<p><span class="step">3</span> <b>워커</b> 가 계획·실행·확인 반복 → 갈림길에서 <b>결정</b>·<b>안전 모드</b> 로 사용자 승인 요청</p>
<p><span class="step">4</span> <b>검증 약속</b> 을 실제 돌려 관측 → 관측 = 판정</p>
<p><span class="step">5</span> <b>전달물 리포트</b> 생성 · 결정/관찰이 <b>지식 그래프</b> 에 반영 → 다음 요청 재사용</p>
</div>

---

## 한 요청의 여정 — 실제 화면

<style scoped>
.flow5 { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; margin-top:6px; }
.frame { border:1px solid #cbd5e1; border-radius:8px; padding:6px; background:#f8fafc; text-align:center; }
.frame img { width:100%; height:150px; object-fit:cover; object-position:top; border-radius:4px; display:block; }
.frame .n { display:inline-block; background:#eef2ff; color:#1e3a8a; font-size:0.72rem; font-weight:700; padding:1px 8px; border-radius:999px; margin:6px 0 3px; }
.frame .cap { color:#334155; font-size:0.82rem; font-weight:600; line-height:1.35; margin:0 0 3px; }
.frame .sub { color:#64748b; font-size:0.72rem; line-height:1.3; margin:0; }
</style>

<div class="flow5">
<div class="frame">
<img src="assets/01_compose.png" alt="다이렉트 입력">
<div class="n">1</div>
<p class="cap">다이렉트</p>
<p class="sub">한 줄 던지기</p>
</div>
<div class="frame">
<img src="assets/02_brief.png" alt="요약">
<div class="n">2</div>
<p class="cap">요약</p>
<p class="sub">작업 중에 반영</p>
</div>
<div class="frame">
<img src="assets/03_decisions.png" alt="결정">
<div class="n">3</div>
<p class="cap">결정</p>
<p class="sub">답안 후보 · 승인</p>
</div>
<div class="frame">
<img src="assets/04_delivery_report.png" alt="전달물 리포트">
<div class="n">4</div>
<p class="cap">전달물 리포트</p>
<p class="sub">근거와 결과</p>
</div>
<div class="frame">
<img src="assets/05_knowledge.png" alt="지식">
<div class="n">5</div>
<p class="cap">지식</p>
<p class="sub">그래프에 반영</p>
</div>
</div>

<p class="muted" style="margin-top:14px; text-align:center;">한 줄 던지고 → 리포트 받고 → 지식으로 남는 다섯 화면. 라이브 데모에서 그대로 봅니다.</p>

---

## 기억의 구조 — 지식 그래프

<div class="lead">

사용자가 한 모든 결정과 AI 의 모든 관찰이 **하나의 지식 그래프** 로 쌓입니다.

</div>

- **관찰 메모** (날 것의 기록) → 일정 횟수 반복되면 → **표준 개념** 으로 승격
- **결정 답안** — 갈림길에서 내린 답이 다음 작업에서 자동 검색
- **거절 패턴** — 거절한 접근이 다음에 같은 실수를 막음
- **세 갈래 검색 결합** (의미 검색 + 키워드 검색 + 그래프 이웃) 으로 즉시 인용

> **지식** 화면에서 학습한 그래프를 직접 봅니다. 잘못 학습한 노드는 한 클릭으로 **철회** — 30 초 안에 **되돌리기** 가능.

---

## 어디서든, 무엇과도

<div class="lead">

웹 기반 — **설치 없이 브라우저** 만 있으면 데스크톱·모바일 같은 경험.

</div>

쓰던 도구를 그대로 연결. 예를 들면:

<div class="pillrow">
<span class="pill">GitHub</span>
<span class="pill">Slack</span>
<span class="pill">Discord</span>
<span class="pill">Notion</span>
<span class="pill">Email</span>
</div>

<p class="muted" style="margin-top:18px">대부분 한 번 로그인 — 그 다음은 작업 공간이 알아서 폴링·웹훅 처리.</p>

---

## 기술 스택 (간단)

<style scoped>
ul { margin: 6px 0; }
li { margin: 3px 0; line-height: 1.45; font-size: 0.95rem; }
li li { font-size: 0.9rem; }
</style>

- **웹 스택**: Next.js 14 PWA (Vercel) + FastAPI + PostgreSQL
- **저장 · 검색**: pgvector · NetworkX · 세 갈래 랭킹 (의미 + 키워드 + 그래프)
- **답변 생성**: 추상화된 인터페이스 — 사용자가 선택
  - API 키 등록형 — openai · anthropic · ollama (LiteLLM)
  - 내 컴퓨터의 CLI 워커 — claude code · codex · opencode
- **임베딩**: 마찬가지로 사용자가 등록
- **로그인**: Supabase

---

## 라이브 데모

<div class="lead" style="text-align:center; margin-top:36px;">

**app.bsvibe.dev**

</div>

<div style="text-align:center; margin-top:24px;">

데모 흐름

1. **요약** — 작업 중 / 결정 대기 / 지난 작업 한 화면
2. **다이렉트** — 입력창에 한 줄
3. **전달물 리포트** — 요청 → 만든 것 → 어떻게 확인했나 → 변경 코드
4. **지식** — 학습된 지식 그래프 시각화
5. **철회** — 잘못 학습한 노드 한 클릭 → 30 초 되돌리기 토스트

</div>

---

<div style="text-align:center; margin-top:180px;">

# 감사합니다

<p class="lead" style="font-size:1.4rem; margin-top:32px;">Q&A</p>

</div>
