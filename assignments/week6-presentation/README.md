# 6주차 과제: 최종 발표 자료

bsvibe-app 제품 소개 발표 — 메타코드 부트캠프 학우/강사 대상. 전체 20–25분 (발표 약 14분 + Q&A 6–11분). 데모는 슬라이드에서 뺐고 시간 남으면 즉흥 시연.

> 이전 주차 산출물 (week2~5) 은 포함하지 않습니다. 발표는 **bsvibe 라는 제품 자체** 에 집중.

## 파일

| 파일 | 용도 |
|---|---|
| [`slides.md`](slides.md) | Marp 마크다운 슬라이드 (13장) |
| [`speaker_notes.md`](speaker_notes.md) | 슬라이드별 멘트 + 시간 배분 + Q&A 대응표 + cut/extend 가이드 |
| `assets/` | 발표용 이미지 (스크린샷 등 — 라이브 데모 가는 경우 비워둠) |

## 슬라이드 흐름

1. Cover — BSVibe · "믿음이 아닌, 증명."
2. Problem — 한 사람이 여러 제품을 굴릴 때 진짜 비용
3. Solution — 한 줄 약속
4. How it works — 4단계 + 다이렉트 프리뷰 스크린샷
5. 요약 (작업 중/결정 대기/지난 작업) + brief 스크린샷
6. 전달물 리포트 (5 블록) + delivery-report 스크린샷
7. 결정 (필요할 때만 + AI 가 답안 후보 제안) + decisions 스크린샷
8. 안전 모드 — 승인 후에만 외부 나감
9. 쓰던 LLM 도구를 그대로 — claude code / codex / opencode 결합
10. **안에서 어떻게 굴러가나** — 소프트웨어 구조도 (3층 + 5단계 파이프라인) + 하단 부가 (LLM/커넥터/로그인)
11. **남는 것 — 지식 · 스킬** (두 갈래 자산) + knowledge + skills 스크린샷
12. 어디서든 — 웹 + 대표 커넥터 (GitHub · Slack · Discord · Notion · Email)
13. 감사합니다 · Q&A (시간 남으면 즉흥 데모)

내용은 모두 `bsvibe-app` 의 실제 코드와 정렬 (`backend/api/auth/routes.py`, `backend/api/v1/messages.py`, `backend/executors/worker/{claude_code,codex,opencode}.py`, `apps/pwa/components/{shell/DirectAction,deliverables/DeliveryReport}.tsx`, `apps/pwa/lib/api/brief.ts`). 발표 중 어느 청중이 "이게 실제로 그렇게 동작해요?" 라고 물어도 코드로 검증 가능.

## 렌더 방법

### Marp CLI 로 PDF / PPTX / HTML

```bash
# marp-cli 설치 (한 번)
brew install marp-cli   # 또는 npm i -g @marp-team/marp-cli

# PDF
marp slides.md --pdf -o slides.pdf

# PPTX (Keynote/PowerPoint 열기)
marp slides.md --pptx -o slides.pptx

# HTML (브라우저 발표)
marp slides.md --html -o slides.html

# 발표 모드 (presenter view + live preview)
marp slides.md --preview
```

### VS Code 에서 미리보기

VS Code 의 **Marp for VS Code** 확장 설치 → `slides.md` 열기 → 우상단 "Open Preview" 클릭.

## 발표 시나리오 (요약)

- **총 시간**: 전체 20–25분 (발표 약 16분 + Q&A 5–10분)
- **타이밍**: 슬라이드별 시간 배분은 `speaker_notes.md` 참고
- **데모**: 슬라이드 15 에서 `app.bsvibe.dev` 로 전환 (라이브 또는 사전 녹화 둘 다 가능)
- **Q&A**: 기술/제품/품질/로드맵 4 분류 예상 질문 + 답안 `speaker_notes.md` 표 참고

## 발표 직전 체크리스트

- [ ] `app.bsvibe.dev` 로그인 + 데모 작업 공간 준비 (지식 화면의 그래프에 노드 충분히 학습)
- [ ] 데모용 워크스페이스 분리 (실수로 retract 해도 복구 쉽도록)
- [ ] 마이크 + 화면 공유 사전 점검
- [ ] 비상 plan: 라이브 안 되면 사전 녹화 영상

## 비고

- 슬라이드 톤은 `bsvibe-site` 가 사용하는 카피 컨벤션을 따름 — **주어 생략 자연 한국어**, em-dash 없음, 회사명을 문장 주어로 쓰지 않음
- 기술 용어 (verification_contract · canonicalization · RRF) 는 첫 등장 시 한 줄로 풀어 설명
- 부트캠프 청중이라 너무 깊은 기술 디테일은 Q&A 로 미룸 — 슬라이드는 "왜·무엇" 중심, 기술은 13(스택) 한 슬라이드로 압축
