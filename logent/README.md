# Logent 빌드·릴리스 안내

이 디렉터리는 원본 Knowledge Work 콘텐츠를 Logent 패키지로 만드는 전용 도구예요. 원본 Claude/Cowork installer를 실행하는 도구가 아니에요. 사용자 설치·도구 사용법과 Termux 제한은 [루트 README](../README.md), 경로별 라이선스는 [NOTICE](../NOTICE)를 확인해요.

## 고정 계약과 단일 원천

- 모듈은 `logent-plugin/`, namespace는 `com.sleepysoong.logent.knowledgework`, 엔트리는 `KnowledgeWorkPlugin`이에요.
- `logent-plugin.json`이 id `com.sleepysoong.logent.knowledge-work`, key `logentworld:knowledge_work`, 엔트리와 API 범위를 정의해요.
- `plugin-api.lock`은 API **4.0.0**, Maven 좌표 `com.sleepysoong.logent:logent-plugin-api`, API 소스 커밋 **`e6fbb6c53b88245242f521b96ca958418bf83c6c`**를 고정해요. 해당 고정 커밋에서 발행한 로컬 Maven API를 사용하려면 `-PlogentPluginApiMavenLocal=true`를 전달해요. API 소스를 이 저장소에 vendoring하지 않아요.
- 루트 `VERSION`은 Logent 릴리스 버전이에요. 최초 기준은 `0.0.0`이고 첫 patch 릴리스는 `0.0.1`이에요. 원본 도메인 manifest의 버전과는 별개예요.
- 원본 루트·`partner-built/` 도메인이 콘텐츠의 유일한 소스예요. `stage-assets.py`가 빌드 시 목차·자산을 만들고, AAR에서 `.lpg`의 **`assets/plugins/knowledge-work/`** 아래로 전달해요. 생성 자산과 원본 자산 ZIP은 `build/` 아래의 ignored 결과물이에요. 별도 upstream 스킬·엔진 사본을 커밋하지 않아요.
- 원본 로컬 22개 도메인의 1,273개 파일, 중첩 포함 252개 스킬·15개 명령 문서가 범위예요. marketplace 외부 원격 101개의 소스는 가져오지 않아요. 원본 라이선스·고지는 자산과 원본 ZIP에 포함해요.
- Android 자산 병합에서 숨김 디렉터리가 빠지지 않도록 점으로 시작하는 경로 조각은 패키지 안에서 `dot-` 접두어로 매핑해요. 목차는 원본 `path`와 실제 `asset`을 구분하고, 도구의 읽기·전개 경로는 원본 이름을 유지해요.

도메인별 `kw-<domain>` 스킬은 원본 목차와 경로 읽기를 안내해요. `knowledge_work`의 `list`·`read`·`connectors`, `/knowledge`로 원본에 접근해요. 보조 파일은 `knowledge_work_prepare`에 `domain`과 `confirm: true`를 명시한 WRITE 동작에서만 전개해요. 빌드·설치·읽기만으로 자동 `npx`·의존성 설치·stdio 서버·권한 상승을 수행하지 않아요. HTTPS MCP 제안은 사용자가 Logent 코어에 수동 연결해야 해요.

## 준비하기

Linux 빌드 환경에서 JDK 21, Python 3.11 이상, Android SDK와 필요한 Build Tools, Gradle wrapper 다운로드 접근이 필요해요. CI는 JDK 21·Python 3.12와 Android 플랫폼 `android-37.0`·Build Tools `37.0.0`을 준비해요. 로컬에서는 `JAVA_HOME`, Android SDK 경로와 API Maven 인증을 환경에 맞게 설정해요.

API Maven은 `https://maven.pkg.github.com/logentworld/plugin`을 사용해요. 접근 권한이 필요한 환경에서는 적절한 계정과 `GITHUB_TOKEN`을 준비하거나, 잠금 API 커밋에서 `:plugin-api:publishToMavenLocal`을 수행한 환경을 사용해요. 잠금 API와 다른 임의 버전으로 대체하지 않아요. 릴리스 게시에는 `git`, `gh`, GitHub 인증과 저장소 쓰기 권한도 필요해요.

원본 과학 계산·SDK 보조 스크립트의 실행 환경과 플러그인 빌드 환경은 달라요. `.lpg`를 만들거나 파일을 전개했다고 Android/Termux에서 Docker·CUDA·데스크톱 Python 패키지·Zoom SDK를 실행할 수 있게 되는 것은 아니에요.

## 테스트와 빌드

저장소 루트에서 실행해요.

```bash
# Python 테스트, JVM 단위 테스트와 Android lint를 실행해요.
./logent/test.sh -PlogentPluginApiMavenLocal=true

./logent/build.sh -PlogentPluginApiMavenLocal=true
```

`-PlogentPluginApiMavenLocal=true`는 고정 API가 로컬 Maven에 준비된 경우에만 사용해요. 원격 Maven을 사용할 때는 이 인자를 생략해요. 빌드는 AAR을 만든 뒤 D8 변환과 `.lpg` 패키징을 수행해요. 이 문서는 테스트나 빌드가 실제 통과했다고 주장하지 않아요. 실행 결과는 해당 CI 실행이나 로컬 로그에서 확인해요.

`build/dist/` 산출물은 다음과 같아요.

| 파일 | 용도 |
| --- | --- |
| `logent-knowledge-work-v<버전>.lpg` | Logent 설치 파일이에요. |

`.lpg`는 서명하지 않아요. AAR·원본 자산 ZIP·체크섬·설치 안내는 만들지 않아요.

## 커밋마다 CI 배포

`.github/workflows/plugin-edge.yml`은 `main`·`logent` push, `v*` 태그 push, 수동 실행을 처리해요.

1. 전체 이력을 checkout하고 `plugin-api.lock`의 소스 커밋을 읽어요.
2. 해당 API 커밋을 별도 CI 작업 디렉터리에 checkout하고 일치 여부를 확인한 뒤 로컬 Maven에 발행해요. 이 체크아웃은 원본 스킬이나 엔진의 커밋된 vendored 사본이 아니에요.
3. 테스트·lint 뒤 `.lpg` 하나를 만들어요.
4. 브랜치 실행은 `edge`, 태그 실행은 해당 `v*` 릴리스에 올려요. 대기 커밋의 취소를 피하기 위해 워크플로 concurrency 취소 설정을 두지 않아요.

저장소 Actions secrets는 다음과 같이 준비해요.

| secret | 역할 |
| --- | --- |
| `LOGENT_PLUGIN_API_TOKEN` | 고정 API 저장소·패키지를 읽는 토큰이에요. 없으면 기본 `github.token`을 사용하지만 접근 가능한지는 권한에 달려 있어요. |

워크플로에는 릴리스 게시용 `contents: write`, 패키지 읽기용 `packages: read` 권한이 필요해요. 릴리스 자산 이름은 `logent-knowledge-work-v<버전>.lpg` 그대로이고 커밋·실행 접미사나 체크섬 파일을 붙이지 않아요.

## 로컬 릴리스와 버전 올리기

```bash
./logent/release.sh 'Port knowledge work to Logent' \
  '원본 업무 콘텐츠를 Logent에서 사용할 수 있도록 이식했어요.' \
  -PlogentPluginApiMavenLocal=true
```

이 명령은 단순 빌드가 아니에요. `main` 또는 `logent`에서 원격과 동기화됐는지 확인하고 `VERSION` patch를 올린 뒤 테스트·lint·빌드, 커밋, 주석 태그, 브랜치/태그 atomic push, GitHub 릴리스 게시까지 수행해요. **`git add -A`로 현재 변경 전체를 포함하므로** 관련 없는 변경·비밀 파일을 먼저 분리해요. 첫 인수는 한 줄 영어 제목, 둘째는 한국어 해요체 본문이어야 해요. `gh` 인증이 없으면 릴리스하지 않아요. 실패 단계에 따라 원격 push나 게시 상태를 확인하고, 이미 만든 버전·태그를 무작정 다시 만들지 않아요.

이미 만든 `build/dist/`를 게시하는 도구는 `./logent/publish-release.sh '한국어 릴리스 안내예요.'`예요. 기본 대상은 `logentworld/knowledge-work-plugins`의 `v<VERSION>`이고 CI에서는 `LOGENT_RELEASE_TAG=edge`를 사용해요. 별도 자동 업데이트 manifest URL은 정의하지 않아요. 사용자는 GitHub Releases에서 새 `.lpg`를 내려받아 Logent 설정의 플러그인 목록에서 같은 key로 다시 설치해요.

## upstream 동기화와 보존 의무

upstream을 갱신할 때는 실제 원본 커밋을 확인하고 루트 `UPSTREAM_COMMIT`, 원본 README 보존본, NOTICE와 필요한 수치·문서를 함께 갱신해요. 원본 LICENSE·파트너 MIT 허가문·바이오 스킬별 LICENSE.txt를 누락하지 않아요. 이력과 도메인 원본은 유지하고 `build/` 생성 자산을 소스처럼 커밋하지 않아요.

원본 `bump-plugin-shas` 등 `.github/` 워크플로는 보존돼요. 예약·수동 실행의 GitHub 기본 브랜치 규칙 때문에 `logent` 브랜치 push가 upstream 콘텐츠를 자동으로 동기화한다고 보장하지 않아요. 외부 marketplace 항목과 SDK·서비스를 새로 내려받아 패키지에 넣으려면 별도 라이선스·재배포 조건을 먼저 확인해요.
