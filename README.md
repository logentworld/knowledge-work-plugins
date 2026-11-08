# Logent Knowledge Work 플러그인

[anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)의 원본 이력과 파일을 보존하면서, 저장소에 실제 들어 있는 업무 플러그인 전체를 Logent에서 읽고 활용하도록 이식했어요. 이 저장소는 [logentworld의 실제 GitHub fork](https://github.com/logentworld/knowledge-work-plugins)예요. Anthropic이나 파트너가 제공하는 공식 Logent 제품은 아니에요.

> **Logent 변경 고지:** 이 README는 Logent용으로 다시 작성했어요. 고정 원본 커밋 `e050c2ec856373787143d7057663a6ebd1277df3`의 README는 [README.upstream.md](README.upstream.md)에 수정 없이 보존해요. 원본 영어 스킬·문서·주석은 보존하고, 새 Logent 코드·문서·주석은 한국어로 작성해요.

## 포함하는 범위

- 로컬 **22개 도메인**(루트 17개, `partner-built/` 5개)의 원본 파일 1,273개를 패키징해요. 중첩 Zoom 스킬까지 **252개 `SKILL.md`**, 원본 명령 문서 **15개**를 목차에서 찾아볼 수 있어요.
- 생산성·영업·고객지원·제품관리·마케팅·법무·재무·데이터·기업검색·바이오연구·플러그인관리·디자인·엔지니어링·인사·운영·PDF·소상공인 업무와 Apollo·Brand Voice·Common Room·Slack·Zoom을 다뤄요.
- 루트 원본 `LICENSE`와 marketplace 정의도 보존해요. marketplace가 가리키는 **외부 원격 101개**의 소스는 이 저장소에 없어서 가져오거나 이식하지 않아요. 외부 서비스, SDK, 모델, 데이터베이스와 설치되는 의존성도 `.lpg`에 포함하지 않아요.
- 원본 플러그인 디렉터리가 콘텐츠의 **단일 원천**이에요. upstream 스킬이나 엔진을 새 vendored 디렉터리로 복제해 커밋하지 않아요. `build/` 아래 생성 자산·목차·배포물만 빌드 시 만들어요.

라이선스·파트너 고지·재배포 범위는 [NOTICE](NOTICE), 고정 커밋은 [UPSTREAM_COMMIT](UPSTREAM_COMMIT)에 기록해요. 원본 콘텐츠를 보존한다는 뜻이지, Claude 전용 실행 환경이나 외부 서비스를 Logent에 내장한다는 뜻은 아니에요.

## 설치와 업데이트

1. [GitHub Releases](https://github.com/logentworld/knowledge-work-plugins/releases)에서 운영 키로 서명된 `logent-knowledge-work-v<버전>.lpg`와 `SHA256SUMS`를 받아요. 태그 릴리스는 고정 배포이고 `edge`는 커밋별 배포예요. `edge` 파일에는 `<SHA12>-<runID>-<attempt>` 식별자가 붙으므로 같은 식별자의 `.lpg`·체크섬·설치 안내를 골라요.
2. 필요하면 `sha256sum`으로 내려받은 파일을 `SHA256SUMS`와 대조해요. 체크섬은 전송 무결성 확인이고, 발행자 신뢰는 Logent의 서명 검증이 담당해요.
3. Logent의 **설정 → 플러그인과 스킬 → 플러그인 관리**에서 `.lpg`를 설치해요. Plugin API **4.0.0** 호환 앱이 필요해요. 서명을 신뢰할 수 없다는 안내가 나오면 검증을 우회하지 말고 올바른 발행자 서명 파일을 받아요.
4. 다음 대화 라운드에서 `/knowledge`로 목차를 열어요. 업데이트도 같은 key의 새 서명 `.lpg`를 다시 설치해요. 이 저장소는 자동 업데이트 manifest URL을 제공하지 않아요.

파일명이 **`-ci.lpg`**로 끝나면 운영 서명 키 없이 임시 키로 만든 CI 확인용 결과물이에요. **사용자 설치·업데이트용이 아니에요.** 운영 키가 없는 CI에서도 빌드를 확인할 수 있도록 구분하며, 이 파일을 운영 서명 배포물로 소개하지 않아요.

## 사용하기

Logent에는 각 원본 스킬·명령을 무리하게 전역 등록하지 않고, 도메인별 **`kw-<domain>` 스킬**, 읽기 도구 **`knowledge_work`**, 단일 명령 **`/knowledge`**를 제공해요. 도메인 스킬에서 원본 목차와 경로를 찾고 필요한 문서만 읽어요. 다른 플러그인의 스킬까지 포함하는 코어 한도를 이 플러그인이 없애 주는 것은 아니에요.

```text
/knowledge
/knowledge list
/knowledge list sales
/knowledge read sales/skills/account-research/SKILL.md
/knowledge read sales/skills/account-research/SKILL.md 16000
/knowledge connectors sales
```

정확한 경로와 도메인 id는 먼저 `list` 결과에서 확인해요. `/knowledge`는 해당 읽기 동작을 직접 수행하며 원문을 모델 실행 프롬프트로 자동 전송하지 않아요.

| 도구 | 인수와 역할 |
| --- | --- |
| `knowledge_work` | `action: "list"`로 목차를 읽어요. 선택적 `domain`, `offset`, `limit`으로 범위를 좁혀요. |
| `knowledge_work` | `action: "read"`, `path: "저장소/상대/경로"`로 원문을 읽어요. `offset`은 문자 위치이고 `limit`은 1~16,000이에요. |
| `knowledge_work` | `action: "connectors"`와 선택적 `domain`으로 커넥터 원문과 수동 연결 제안을 살펴봐요. `offset`은 문자 위치예요. |
| `knowledge_work_prepare` | `domain: "도메인-id"`, `confirm: true`를 명시해 보조 파일을 작업 환경에 전개해요. **WRITE 권한** 동작이에요. |

`list`의 `offset`은 항목 인덱스이고, `read`와 `connectors`의 `offset`은 문자 위치예요. 모두 0부터 시작해요. 원본 문서는 참조 데이터예요. 문서에 적힌 설치 명령이나 외부 요청이 사용자 승인이나 호스트 권한보다 우선하지 않아요. 법률·재무·의료 등 전문 판단과 외부 전송·변경은 원본의 승인·검토 요건도 지켜요.

### 보조 파일과 Termux

보조 Python·셸 스크립트나 참조 파일이 필요할 때만 `knowledge_work_prepare`를 명시적으로 호출해요. 호스트가 검증한 아카이브에서 해당 도메인의 허용 파일을 Termux의 `$HOME/.logent/knowledge-work/` 아래로 전개해요. 기존 파일을 덮어쓰거나 심볼릭 링크를 따라가지 않아요. **전개는 실행이나 의존성 설치가 아니에요.**

원본에는 데스크톱 Python, 과학 계산 라이브러리, Java/Nextflow, Docker/Singularity, GPU/CUDA, Linux x86_64·Qt·Zoom SDK를 전제로 한 안내가 있어요. Android/Termux의 ABI·라이브러리·프로세스·컨테이너 제약 때문에 그대로 실행되지 않을 수 있어요. 호환성이나 전체 워크플로 실행 성공을 보장하지 않아요. 필요하면 검토한 별도 Linux/서버 환경에서 사용하고, 필요한 의존성과 라이선스는 직접 확인해요. 자동 `npx`, 패키지 설치, `sudo`, 권한 상승은 수행하지 않아요.

### MCP 연결

커넥터는 **HTTPS MCP 수동 연결 제안**으로만 제공해요. 제공된 URL과 서비스 계정·OAuth·데이터 접근 범위를 확인한 뒤 Logent 코어의 수동 MCP 설정에 직접 추가해요. 외부 서비스 약관과 접근 권한은 별도로 필요해요.

원본 `.mcp.json`의 stdio 서버, PDF용 `npx`, Claude/Cowork 전용 installer·마켓플레이스 명령은 실행하지 않아요. 원본의 `~~connector` 표기나 Claude 전용 도구·sub-agent 설명을 그대로 지원한다고 간주하지 말고, 실제 연결한 Logent 도구에 맞춰 작업해요.

## 개발과 커밋 배포

- 모듈: `logent-plugin/`, 엔트리: `com.sleepysoong.logent.knowledgework.KnowledgeWorkPlugin`
- id: `com.sleepysoong.logent.knowledge-work`, key: `logentworld:knowledge_work`
- API 고정: `plugin-api.lock`의 **4.0.0**과 API 소스 커밋 `e6fbb6c53b88245242f521b96ca958418bf83c6c`를 사용해요.
- `.lpg` 자산 prefix: `assets/plugins/knowledge-work/`
- 빌드·서명·CI·릴리스 절차: [logent/README.md](logent/README.md)

`main`·`logent` 브랜치의 각 push와 `v*` 태그 CI에서 테스트·lint·빌드를 수행하고 `edge` 또는 태그 릴리스를 게시해요. 운영 서명 secret이 설정돼 있어야 설치 가능한 `.lpg`가 나와요. 로컬 릴리스 스크립트는 루트 `VERSION`의 patch를 올리고 커밋하는 흐름을 사용해요. 원본 `.github/` 도구와 Logent용 `logent/` 도구를 혼동하지 않아요.

원본 `bump-plugin-shas` 워크플로도 보존하지만, 예약·수동 실행은 GitHub 기본 브랜치를 기준으로 동작해요. `logent`에 push했다고 upstream 변경이 자동으로 병합되지는 않아요. upstream 갱신 때는 원본 변경·라이선스·목차를 검토하고 `UPSTREAM_COMMIT`과 이식 문서를 함께 갱신해요.

## 출처와 라이선스

원본 [LICENSE](LICENSE)는 후미의 원본 텍스트까지 수정 없이 유지해요. 대부분의 도메인은 Apache-2.0이고, Apollo·Brand Voice·Slack·Zoom은 각 MIT 라이선스를 유지해요. 전체를 하나의 새 라이선스로 덮어쓰지 않아요. 외부 링크·제품명은 출처 설명용이며 원저작자나 파트너의 후원·인증을 뜻하지 않아요. 자세한 경로별 근거와 포함·제외 기준은 [NOTICE](NOTICE)를 읽어 주세요.
