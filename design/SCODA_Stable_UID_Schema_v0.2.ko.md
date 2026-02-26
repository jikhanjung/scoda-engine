# SCODA Stable UID 스키마

버전: v0.2 (초안)

이 문서는 SCODA 기반 시스템을 위한 Stable UID(고유 식별자) 스키마를 정의합니다.
Trilobase와 PaleoCore 간에 공유되는 모든 엔티티 유형을 다루며, UID가 패키지 간
동일성 확인, 참조 해석, 엔티티 생명주기 관리를 어떻게 가능하게 하는지 명시합니다.

Stable UID의 목표:

1.  동일한 실세계 엔티티 → 패키지(Trilobase / PaleoCore)에 관계없이 동일한 UID
2.  UID는 시간이 지나도 안정적이어야 함
3.  UID 생성은 재현 가능해야 함
4.  UID는 로컬 데이터베이스 기본 키에 의존하지 않아야 함

------------------------------------------------------------------------

# 0. 일반 UID 규칙

## 0.1 UID 형식

UID는 URI와 유사한 네임스페이스 형식을 따릅니다:

    scoda:<entity_type>:<method>:<value>

예시:

    scoda:bib:doi:10.1234/abcd.efgh
    scoda:bib:fp:sha256:<64hex>
    scoda:strat:formation:lexicon:USGS:123456
    scoda:strat:formation:fp:sha256:<64hex>

이를 통해 UID는:

-   사람이 읽을 수 있고
-   네임스페이스를 인식하며
-   확장 가능합니다

------------------------------------------------------------------------

## 0.2 정규화 규칙 (해싱 전 필수)

모든 핑거프린트 기반 UID는 정규화된 입력 문자열을 사용해야 합니다.

필수 정규화 항목:

-   앞뒤 공백 제거
-   연속된 공백을 하나로 축소
-   소문자로 변환
-   유니코드 정규화 (NFKC 권장)
-   구두점 제거 또는 표준화 (엔티티별 규칙 참조)

------------------------------------------------------------------------

## 0.3 해싱

핑거프린트 UID는 다음을 사용합니다:

-   SHA256
-   16진수 출력 (64자)

입력은 항상 정규화된 표준 문자열이어야 합니다.

------------------------------------------------------------------------

# 1. 참고문헌 UID 스키마

## 1.1 우선순위

1.  DOI (선호)
2.  기타 글로벌 ID (PMID, ISBN, arXiv 등)
3.  참고문헌 핑거프린트 (fp_v1)

------------------------------------------------------------------------

## 1.2 DOI 기반 UID

UID:

    scoda:bib:doi:<normalized_doi>

정규화 규칙:

-   소문자
-   다음 접두사 제거:
    -   https://doi.org/
    -   doi:
-   공백 제거

예시:

입력: https://doi.org/10.1000/ABC.DEF

UID: scoda:bib:doi:10.1000/abc.def

------------------------------------------------------------------------

## 1.3 참고문헌 핑거프린트 (fp_v1)

DOI를 사용할 수 없을 때 사용합니다.

### 표준 문자열 구성

권장 필드:

-   제1저자 성
-   출판 연도
-   제목 (정규화)
-   수록지 제목 (학술지/도서)
-   권 (가용 시)
-   시작 페이지 (가용 시)

표준 문자열 예시:

    fa=kim|y=1998|t=trilobite systematics revision|c=j paleontology|v=12|p=123

### 정규화 세부사항

제목 및 수록지:

-   소문자
-   구두점 제거 (.,:;()'" 등)
-   하이픈과 슬래시를 공백으로 대체
-   & → and로 변환
-   공백 축소

저자:

-   성만 사용
-   소문자

페이지:

-   시작 페이지만 사용 (권장)

### UID 형식

    scoda:bib:fp_v1:sha256:<hash>

### 충돌 처리

충돌이 감지된 경우:

    scoda:bib:fp_v1:sha256:<hash>-c2

추가 메타데이터 저장:

-   fingerprint_method_version (예: fp_v1)
-   fingerprint_source_fields
-   collision_counter

------------------------------------------------------------------------

# 2. 지층 UID 스키마

지층 엔티티는 지역적 중복과 명칭 재사용으로 인해 더 복잡합니다.

## 2.1 사전(Lexicon) 기반 UID (선호)

공식 층서 사전 ID가 존재하는 경우:

    scoda:strat:formation:lexicon:<authority>:<id>

예시:

    scoda:strat:formation:lexicon:USGS:123456
    scoda:strat:formation:lexicon:BGS:78910

------------------------------------------------------------------------

## 2.2 지층 핑거프린트 (fp_v1)

공식 ID가 없을 때 사용합니다.

### 표준 문자열 구성

권장 필드:

-   formation_name (정규화)
-   rank (formation/member/group)
-   region (국가/주/분지)
-   geologic_age (기 또는 세)
-   stratigraphic context (선택이나 권장)

표준 문자열 예시:

    n=taebaek|r=formation|geo=kr:taebaek|age=cambrian|ctx=under xyz over abc

### 명칭 정규화

-   소문자
-   "Formation", "Fm." 등 제거
-   구두점 제거
-   공백 축소

### 지역 표준화

ISO 기반 구조 권장:

    KR:Taebaek
    US:NV:GreatBasin

### UID 형식

    scoda:strat:formation:fp_v1:sha256:<hash>

------------------------------------------------------------------------

# 3. 국가 UID 스키마

국가는 PaleoCore의 공유 참조 엔티티로, 도메인 패키지(Trilobase 등)에서
`genus_locations.country_id`를 통해 참조됩니다.

## 3.1 우선순위

1.  ISO 3166-1 alpha-2 코드 (선호)
2.  국가명 핑거프린트 (대체)

## 3.2 ISO 기반 UID

UID:

    scoda:geo:country:iso3166-1:<code>

정규화 규칙:

-   alpha-2 코드를 대문자로
-   유효한 ISO 3166-1 alpha-2 코드여야 함

예시:

    scoda:geo:country:iso3166-1:KR       (대한민국)
    scoda:geo:country:iso3166-1:US       (미국)
    scoda:geo:country:iso3166-1:CN       (중국)
    scoda:geo:country:iso3166-1:AU       (호주)

커버리지: PaleoCore `countries` 테이블의 96.5% (137/142)가 유효한 COW 매핑을
보유하며, 대부분 ISO 3166-1 코드에 대응됩니다.

## 3.3 이름 핑거프린트 (대체)

ISO 코드가 없는 국가(예: 역사적이거나 모호한 명칭)의 경우:

UID:

    scoda:geo:country:fp_v1:sha256:<hash>

표준 문자열:

    name=<normalized_country_name>

정규화:

-   소문자
-   NFKC 정규화
-   공백 축소
-   괄호 내 수식어 제거

예시:

    name=czech republic
    → scoda:geo:country:fp_v1:sha256:<hash>

## 3.4 DB 스키마 매핑

| UID 출처 | DB 컬럼 | 커버리지 |
|------------|-----------|----------|
| ISO 3166-1 alpha-2 | `countries.code` | 96.5% |
| 이름 핑거프린트 | `countries.name` | 100% (대체) |

------------------------------------------------------------------------

# 4. 지리적 지역 UID 스키마

지리적 지역은 국가 내의 하위 행정구역(주, 도, 분지)을 나타냅니다.
PaleoCore의 `geographic_regions` 테이블에 저장됩니다.

## 4.1 UID 형식

UID:

    scoda:geo:region:name:<country_iso>:<normalized_name>

지역 UID는 상위 국가의 ISO 코드와 지역의 정규화된 이름을 결합하여
전역 고유성을 보장합니다.

`<normalized_name>` 정규화 규칙:

-   소문자
-   NFKC 정규화
-   공백을 하이픈으로 대체
-   하이픈을 제외한 구두점 제거

예시:

    scoda:geo:region:name:US:nevada            (네바다, 미국)
    scoda:geo:region:name:CN:yunnan            (윈난, 중국)
    scoda:geo:region:name:AU:queensland        (퀸즐랜드, 호주)
    scoda:geo:region:name:KR:taebaek           (태백, 대한민국)

## 4.2 대체: 국가명 변형

상위 국가에 ISO 코드가 없는 경우:

    scoda:geo:region:fp_v1:sha256:<hash>

표준 문자열:

    country=<normalized_country_name>|name=<normalized_region_name>

## 4.3 DB 스키마 매핑

| UID 구성요소 | DB 컬럼 |
|---------------|-----------|
| 국가 ISO | `countries.code` (`geographic_regions.parent_id` 경유) |
| 지역명 | `geographic_regions.name` |

------------------------------------------------------------------------

# 5. ICS 연대층서 UID 스키마

ICS(국제층서위원회) 연대층서 단위는 GTS 2020 차트의 전 세계 참조 데이터입니다.
각 단위에는 ICS가 부여한 공식 SKOS URI가 있습니다.

## 5.1 우선순위

1.  ICS SKOS URI (선호 — 100% 커버리지)
2.  이름 핑거프린트 (불필요; ICS URI가 모든 단위를 포함)

## 5.2 ICS URI 기반 UID

UID:

    scoda:strat:ics:uri:<ics_uri>

`<ics_uri>`는 `ics_chronostrat.ics_uri`에 저장된 전체 ICS SKOS URI입니다.

예시:

    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Cambrian
    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Tremadocian
    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Phanerozoic

정규화 규칙:

-   URI를 그대로 사용 (소문자 변환 없음 — URI는 대소문자 구분)
-   뒤에 슬래시 없음
-   ICS SKOS 표준 어휘와 일치해야 함

## 5.3 커버리지

`ics_chronostrat` 레코드의 100% (178개 단위)가 `ics_uri`를 보유합니다.
대체 방법은 필요하지 않습니다.

## 5.4 DB 스키마 매핑

| UID 출처 | DB 컬럼 | 커버리지 |
|------------|-----------|----------|
| ICS SKOS URI | `ics_chronostrat.ics_uri` | 100% |

------------------------------------------------------------------------

# 6. 시간 범위 UID 스키마

시간 범위는 Jell & Adrain (2002)에서 삼엽충 속의 지질학적 시간대를 나타내기
위해 사용하는 기간 코드입니다. 이들은 도메인 고유 코드(LCAM, MCAM 등)로
PaleoCore의 `temporal_ranges` 테이블에 저장됩니다.

## 6.1 UID 형식

UID:

    scoda:strat:temporal:code:<code>

`<code>`는 `temporal_ranges.code`에 저장된 그대로의 단축 코드입니다.

예시:

    scoda:strat:temporal:code:LCAM       (하부 캄브리아기)
    scoda:strat:temporal:code:MCAM       (중부 캄브리아기)
    scoda:strat:temporal:code:UCAM       (상부 캄브리아기)
    scoda:strat:temporal:code:LORD       (하부 오르도비스기)
    scoda:strat:temporal:code:MISS       (미시시피기)
    scoda:strat:temporal:code:INDET      (미확정)

정규화 규칙:

-   대문자 (코드는 관례적으로 이미 대문자)
-   공백이나 구두점 없음

## 6.2 ICS UID와의 관계

각 시간 범위 코드는 `temporal_ics_mapping`을 통해 하나 이상의 ICS 단위에
매핑됩니다. 이 관계는 문서화되지만 UID 자체에는 인코딩되지 않습니다:

    scoda:strat:temporal:code:LCAM
      → 매핑 (집합):
        scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Terreneuvian
        scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Series2

## 6.3 커버리지

`temporal_ranges` 레코드의 100% (28개 코드)가 고유한 `code`를 보유합니다.

## 6.4 DB 스키마 매핑

| UID 출처 | DB 컬럼 | 커버리지 |
|------------|-----------|----------|
| 코드 | `temporal_ranges.code` | 100% |

------------------------------------------------------------------------

# 7. 분류학 UID 스키마

분류학적 엔티티(속, 과, 목 등)는 Trilobase 같은 패키지의 핵심 도메인
데이터입니다. UID 부여는 ICZN(국제동물명명규약) 원칙을 따릅니다.

## 7.1 UID 형식

UID:

    scoda:taxon:<rank>:<normalized_name>

정규화 규칙:

-   `<rank>`: 소문자 (genus, family, order, suborder, superfamily,
    class)
-   `<normalized_name>`: 원래 대소문자 유지 (분류학적 명칭은 고유명사)

예시:

    scoda:taxon:genus:Paradoxides
    scoda:taxon:genus:Olenellus
    scoda:taxon:family:Paradoxididae
    scoda:taxon:order:Ptychopariida
    scoda:taxon:class:Trilobita

## 7.2 고유성 보장

ICZN 동명 원칙 (제52조): 동물계 내에서 두 속이 동일한 이름을 가질 수 없습니다.
따라서 `genus` + 이름의 조합은 유효한 속에 대해 전역적으로 고유합니다.

상위 분류군(과, 목 등)의 경우에도 관례적으로 같은 계급 내에서 이름이
고유합니다.

## 7.3 무효 및 이명 분류군

무효 속(이명, 선취명)에도 UID가 부여됩니다:

    scoda:taxon:genus:Bathynotus        (유효)
    scoda:taxon:genus:Bathynotellus     (Bathynotus의 신참이명)

이명 관계는 UID 자체가 아닌 `same_as_uid`(8절 참조)를 통해 표현됩니다:

    Bathynotellus.same_as_uid = scoda:taxon:genus:Bathynotus

## 7.4 커버리지

`taxonomic_ranks` 레코드의 100% (5,340건)가 해당 계급 내에서 고유한 이름을
보유합니다.

## 7.5 DB 스키마 매핑

| UID 구성요소 | DB 컬럼 |
|---------------|-----------|
| 계급 | `taxonomic_ranks.rank` |
| 이름 | `taxonomic_ranks.name` |

------------------------------------------------------------------------

# 8. 메타데이터 거버넌스

(v0.1 3절에서 확장)

## 8.1 필수 컬럼

UID에 참여하는 각 엔티티 테이블은 다음을 저장해야 합니다:

| 컬럼 | 타입 | 설명 |
|--------|------|-------------|
| `uid` | TEXT | 계산된 Stable UID |
| `uid_method` | TEXT | 사용된 방법: `doi`, `fp_v1`, `lexicon`, `iso3166-1`, `ics_uri`, `code`, `name` |
| `uid_confidence` | TEXT | 신뢰도 수준 (8.2 참조) |
| `same_as_uid` | TEXT | 다른 엔티티의 UID에 대한 선택적 동등성 링크 |

## 8.2 신뢰도 수준

| 수준 | 기준 | 예시 |
|-------|----------|---------|
| `high` | 외부에서 관리되는 전역적으로 고유한 식별자에 기반 | DOI, ICS URI, ISO 3166-1 코드, ICZN 속명 |
| `medium` | 잘 정의된 필드로 구성된 복합 핑거프린트에 기반 | 참고문헌 핑거프린트, 지층 핑거프린트 |
| `low` | 부분적이거나 모호한 정보에 기반 | 불완전한 인용, 해석 불가능한 국가명 |

## 8.3 `same_as_uid` 방향성

`same_as_uid` 필드는 항상 **덜 권위 있는** 엔티티에서 **더 권위 있는**
엔티티를 가리킵니다:

    덜 권위 있는 → 더 권위 있는

예시:

-   신참이명 → 선참이명:
    `Bathynotellus.same_as_uid → scoda:taxon:genus:Bathynotus`

-   선취명 → 대체명:
    `Ampyx.same_as_uid → scoda:taxon:genus:Lonchodomas`

-   로컬 중복 → 표준 출처:
    `trilobase:bibliography[42].same_as_uid → scoda:bib:doi:10.1234/xyz`

## 8.4 적용 우선순위

UID 적용은 커버리지와 난이도에 따라 엔티티 유형별로 우선순위를 정해야 합니다:

| 우선순위 | 엔티티 | 방법 | 예상 커버리지 |
|----------|--------|--------|-------------------|
| 1 | ICS 연대층서 | ICS URI | 100% |
| 2 | 시간 범위 | 코드 | 100% |
| 3 | 분류학 | 계급 + 이름 | 100% |
| 4 | 국가 | ISO 3166-1 | 96.5% |
| 5 | 지리적 지역 | 국가 + 이름 | ~100% |
| 6 | 참고문헌 | DOI / 핑거프린트 | 미정 |
| 7 | 지층 | 사전 / 핑거프린트 | 미정 |

------------------------------------------------------------------------

# 9. 패키지 간 참조 해석

## 9.1 문제

Trilobase 엔티티가 UID를 참조할 때(예: 속의 국가), 런타임은 해당 UID의
정식 레코드를 어떤 패키지의 데이터베이스에서 가져올지 결정해야 합니다.

예시 시나리오:

-   `Paradoxides` (Trilobase)가 `scoda:geo:country:iso3166-1:CZ`를 참조
-   해당 국가 레코드는 PaleoCore(정식)에 존재하거나 개발 중 로컬 패키지에
    임시로 존재할 수 있음

## 9.2 해석 알고리즘

`resolve_uid()` 함수는 **의존성 순서**대로 데이터베이스를 검색합니다:

```
resolve_uid(conn, entity_type, uid):
    1. 의존성 패키지를 먼저 검색 (manifest.json 순서)
       → 예: pc.countries WHERE uid = :uid
    2. 로컬 패키지 검색
       → 예: main.countries WHERE uid = :uid
    3. 찾지 못하면 NULL 반환
```

## 9.3 스코프 체인

검색 순서는 `manifest.json` 의존성에서 도출됩니다:

```json
{
  "name": "trilobase",
  "dependencies": [
    {"name": "paleocore", "version": ">=0.3.0"}
  ]
}
```

Trilobase의 해석 순서:
1. `pc.*` (PaleoCore — 의존성)
2. `main.*` (Trilobase — 로컬)

다중 의존성이 있는 패키지의 경우:
```json
{
  "dependencies": [
    {"name": "paleocore"},
    {"name": "geodata"}
  ]
}
```

해석 순서:
1. `pc.*` (PaleoCore — 첫 번째 의존성)
2. `geodata.*` (Geodata — 두 번째 의존성)
3. `main.*` (로컬)

## 9.4 우선순위 규칙: 의존성 우선

동일한 UID가 의존성과 로컬 패키지 모두에 존재하는 경우:

-   **의존성이 항상 우선** — 의존성 패키지가 정식 출처
-   로컬 복사본은 오래되었거나 과도기적인 것으로 간주

근거: 의존성은 관리된 공유 인프라입니다(예: PaleoCore는 권위 있는 국가 및
지층 데이터를 제공). 로컬 패키지는 이에 위임해야 합니다.

## 9.5 현재 구현

현재 SCODA Desktop 런타임에서 해석은 SQLite ATTACH를 통해 암시적으로
이루어집니다:

```python
conn = sqlite3.connect('trilobase.db')                    # main
conn.execute("ATTACH 'paleocore.db' AS pc")               # dependency
conn.execute("ATTACH 'trilobase_overlay.db' AS overlay")   # overlay

# 교차 DB JOIN이 쿼리 시점에 참조를 해석
SELECT g.name, c.name AS country
FROM genus_locations gl
JOIN taxonomic_ranks g ON gl.genus_id = g.id
JOIN pc.countries c ON gl.country_id = c.id
```

UID 기반 해석은 정수 FK 기반 JOIN을 대체하는 것이 아닌 보완하는 향후
개선 사항입니다.

------------------------------------------------------------------------

# 10. 엔티티 생명주기 및 마이그레이션

## 10.1 문제

엔티티는 도메인 패키지(예: Trilobase)에서 생성된 후 나중에 핵심 패키지
(예: PaleoCore)에 속하는 공유 인프라로 인식될 수 있습니다. UID는 이
마이그레이션 과정에서 안정적으로 유지되어야 합니다.

예시: 삼엽충 논문에 대한 참고문헌 항목이 Trilobase에만 존재합니다.
이후 완족류 패키지(Brachiobase)에서도 동일한 논문이 필요하게 됩니다.
해당 논문은 PaleoCore로 승격되어야 합니다.

## 10.2 생명주기 단계

| 단계 | 위치 | 설명 |
|-------|----------|-------------|
| **로컬 전용** | 도메인 패키지만 | 엔티티가 하나의 패키지(예: Trilobase)에만 존재. UID가 로컬에서 부여됨. |
| **중복** | 다중 도메인 패키지 | 동일한 실세계 엔티티가 동일한 UID로 2개 이상의 패키지에 나타남. 정식 출처 미확정. |
| **승격** | 핵심 패키지 (정식) + 스텁 | 엔티티가 PaleoCore로 마이그레이션됨. 도메인 패키지는 스텁을 유지. |
| **스텁** | 도메인 패키지 (승격 후) | FK 무결성 보존을 위해 `(id, uid)`만 도메인 패키지에 남음. 데이터는 핵심에서 제공. |

## 10.3 단계 전환

```
로컬 전용 ──→ 중복 ──→ 승격
                         │
                         ▼
                      스텁 (원본 패키지에)
```

### 로컬 전용 → 중복

두 번째 도메인 패키지가 동일한 실세계 엔티티에 대한 레코드를 독립적으로
생성할 때 자연스럽게 발생합니다. 감지에는 패키지 간 UID 비교가 필요합니다.

### 중복 → 승격

**이것은 릴리스 시점 작업이며, 런타임 작업이 아닙니다.**

단계:
1.  도메인 패키지 간 중복 UID 식별
2.  가장 완전한 레코드를 정식 버전으로 선택
3.  정식 레코드를 PaleoCore에 삽입
4.  각 도메인 패키지에서 전체 레코드를 스텁으로 대체

### 승격 → 스텁

승격 후, 도메인 패키지는 최소한의 스텁을 유지합니다:

```sql
-- 승격 전 (Trilobase 참고문헌의 전체 레코드):
INSERT INTO bibliography VALUES (42, 'Kim, J.', 1998, NULL,
    'Trilobite systematics revision', 'J. Paleontology', ...);

-- 승격 후 (Trilobase의 스텁):
-- 레코드가 로컬 DB에서 제거됨.
-- genus_formations/genus_locations의 FK 참조는 이제
-- pc.* 접두사(PaleoCore)를 통해 해석됨.
```

국가 및 지층과 같이 이미 PaleoCore에 있는 엔티티(Phase 34 DROP)의 경우,
승격이 완료되었습니다. 로컬 테이블이 삭제되었고 모든 쿼리가 `pc.*` 접두사를
사용합니다.

## 10.4 UID 안정성 보장

UID는 생명주기 전환 중 **절대 변경되지 않습니다**:

    scoda:bib:doi:10.1234/xyz

이 UID는 레코드가 Trilobase에 있든(로컬 전용), Trilobase와 Brachiobase
모두에 있든(중복), PaleoCore에 있든(승격) 동일합니다.

## 10.5 현재 상태

| 엔티티 | 생명주기 단계 | 비고 |
|--------|----------------|-------|
| 국가 | 승격 | Phase 34부터 PaleoCore에 위치 |
| 지리적 지역 | 승격 | Phase 34부터 PaleoCore에 위치 |
| 지층 | 승격 | Phase 34부터 PaleoCore에 위치 |
| ICS 연대층서 | 승격 | Phase 34부터 PaleoCore에 위치 |
| 시간 범위 | 승격 | Phase 34부터 PaleoCore에 위치 |
| 분류학 | 로컬 전용 | Trilobase만 (다른 도메인 패키지 없음) |
| 참고문헌 | 로컬 전용 | Trilobase만 (공유 시 승격 후보) |
| 이명 | 로컬 전용 | Trilobase만 (도메인 고유) |

------------------------------------------------------------------------

# 11. 구현 가이드

## 11.1 컬럼 추가

UID를 지원하려면 참여하는 각 엔티티 테이블에 4개의 컬럼을 추가합니다:

```sql
ALTER TABLE <table> ADD COLUMN uid TEXT;
ALTER TABLE <table> ADD COLUMN uid_method TEXT;
ALTER TABLE <table> ADD COLUMN uid_confidence TEXT DEFAULT 'medium';
ALTER TABLE <table> ADD COLUMN same_as_uid TEXT;

CREATE UNIQUE INDEX idx_<table>_uid ON <table>(uid);
```

## 11.2 `resolve_uid()` 헬퍼 함수

```python
def resolve_uid(conn, entity_type, uid):
    """
    UID를 데이터베이스 레코드로 해석하며, 의존성을 먼저 검색합니다.

    인자:
        conn: 의존성이 ATTACH된 SQLite 연결
        entity_type: 예: 'country', 'formation', 'bibliography'
        uid: Stable UID 문자열

    반환:
        레코드 데이터와 source_package를 포함한 dict, 또는 None
    """
    TABLE_MAP = {
        'country': 'countries',
        'formation': 'formations',
        'bibliography': 'bibliography',
        'ics_chronostrat': 'ics_chronostrat',
        'temporal_range': 'temporal_ranges',
        'taxon': 'taxonomic_ranks',
        'region': 'geographic_regions',
    }
    table = TABLE_MAP.get(entity_type)
    if not table:
        return None

    # 의존성 패키지를 먼저 검색 (의존성 우선)
    for alias in _get_dependency_aliases(conn):
        row = conn.execute(
            f"SELECT * FROM {alias}.{table} WHERE uid = ?", (uid,)
        ).fetchone()
        if row:
            return {'data': row, 'source_package': alias}

    # 로컬 패키지 검색
    row = conn.execute(
        f"SELECT * FROM {table} WHERE uid = ?", (uid,)
    ).fetchone()
    if row:
        return {'data': row, 'source_package': 'main'}

    return None
```

## 11.3 정수 FK와의 공존

UID는 정수 외래 키를 **대체하지 않습니다**. 두 시스템은 공존합니다:

| 용도 | 메커니즘 |
|---------|-----------|
| 쿼리 성능 | 정수 FK + JOIN (기존) |
| 패키지 간 동일성 | UID (신규) |
| 중복 제거 | UID 비교 |
| 마이그레이션 추적 | UID + 생명주기 단계 |

정수 FK가 주요 쿼리 메커니즘으로 유지됩니다. UID는 동일성 검증, 패키지 간
중복 제거, 엔티티 생명주기 관리에 사용됩니다.

## 11.4 UID 생성 예시

```python
import hashlib

def uid_country(code):
    """ISO 코드가 있는 국가의 UID 생성."""
    if code:
        return f"scoda:geo:country:iso3166-1:{code.upper()}"
    return None

def uid_country_fp(name):
    """ISO 코드가 없는 국가의 핑거프린트 UID 생성."""
    normalized = normalize(name)  # 소문자, NFKC, 공백 축소
    h = hashlib.sha256(f"name={normalized}".encode()).hexdigest()
    return f"scoda:geo:country:fp_v1:sha256:{h}"

def uid_ics(ics_uri):
    """ICS 연대층서 단위의 UID 생성."""
    return f"scoda:strat:ics:uri:{ics_uri}"

def uid_temporal(code):
    """시간 범위 코드의 UID 생성."""
    return f"scoda:strat:temporal:code:{code.upper()}"

def uid_taxon(rank, name):
    """분류학적 엔티티의 UID 생성."""
    return f"scoda:taxon:{rank.lower()}:{name}"

def uid_region(country_iso, region_name):
    """지리적 지역의 UID 생성."""
    normalized = region_name.lower().replace(' ', '-')
    return f"scoda:geo:region:name:{country_iso.upper()}:{normalized}"

def uid_bib_doi(doi):
    """DOI가 있는 참고문헌 항목의 UID 생성."""
    normalized = doi.lower()
    for prefix in ['https://doi.org/', 'http://doi.org/', 'doi:']:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return f"scoda:bib:doi:{normalized}"

def uid_formation_lexicon(authority, lexicon_id):
    """사전 ID가 있는 지층의 UID 생성."""
    return f"scoda:strat:formation:lexicon:{authority}:{lexicon_id}"
```

## 11.5 적용 전략

UID 적용은 점진적으로 구현해야 합니다:

**Phase A — 결정적 UID (모호성 없음):**
-   `ics_chronostrat`: `uid_ics(ics_uri)` → 178개 레코드, 100% 커버리지
-   `temporal_ranges`: `uid_temporal(code)` → 28개 레코드, 100% 커버리지
-   `taxonomic_ranks`: `uid_taxon(rank, name)` → 5,340개 레코드, 100%
    커버리지
-   `countries`: `uid_country(code)` → 137/142 레코드 (96.5%)

**Phase B — 복합 UID:**
-   `geographic_regions`: `uid_region(country_iso, name)` → 562개 레코드
-   `countries` (나머지 5개): `uid_country_fp(name)` → 대체

**Phase C — 외부 조회 필요:**
-   `bibliography`: CrossRef API를 통한 DOI 조회, 이후 핑거프린트 대체
-   `formations`: 사전 조회 (USGS, BGS), 이후 핑거프린트 대체

------------------------------------------------------------------------

# 부록 A: UID 요약 표

| 엔티티 | UID 패턴 | 방법 | 신뢰도 | DB 테이블 |
|--------|-------------|--------|------------|----------|
| 참고문헌 (DOI) | `scoda:bib:doi:<doi>` | `doi` | high | `bibliography` |
| 참고문헌 (FP) | `scoda:bib:fp_v1:sha256:<hash>` | `fp_v1` | medium | `bibliography` |
| 지층 (사전) | `scoda:strat:formation:lexicon:<auth>:<id>` | `lexicon` | high | `formations` |
| 지층 (FP) | `scoda:strat:formation:fp_v1:sha256:<hash>` | `fp_v1` | medium | `formations` |
| 국가 (ISO) | `scoda:geo:country:iso3166-1:<code>` | `iso3166-1` | high | `countries` |
| 국가 (FP) | `scoda:geo:country:fp_v1:sha256:<hash>` | `fp_v1` | medium | `countries` |
| 지역 | `scoda:geo:region:name:<iso>:<name>` | `name` | high | `geographic_regions` |
| 지역 (FP) | `scoda:geo:region:fp_v1:sha256:<hash>` | `fp_v1` | medium | `geographic_regions` |
| ICS 단위 | `scoda:strat:ics:uri:<uri>` | `ics_uri` | high | `ics_chronostrat` |
| 시간 범위 | `scoda:strat:temporal:code:<code>` | `code` | high | `temporal_ranges` |
| 분류군 | `scoda:taxon:<rank>:<name>` | `name` | high | `taxonomic_ranks` |

------------------------------------------------------------------------

# 부록 B: 변경 이력

## v0.2 (초안) — 2026-02-15

-   3절 추가: 국가 UID 스키마
-   4절 추가: 지리적 지역 UID 스키마
-   5절 추가: ICS 연대층서 UID 스키마
-   6절 추가: 시간 범위 UID 스키마
-   7절 추가: 분류학 UID 스키마
-   8절 확장: 메타데이터 거버넌스 (v0.1 3절에서)
    -   `uid_confidence` 수준 정의 추가
    -   `same_as_uid` 방향성 규칙 추가
    -   적용 우선순위 표 추가
-   9절 추가: 패키지 간 참조 해석
    -   manifest.json 의존성에서 도출된 스코프 체인
    -   의존성 우선 규칙
-   10절 추가: 엔티티 생명주기 및 마이그레이션
    -   4단계 생명주기: 로컬 전용 → 중복 → 승격 → 스텁
    -   릴리스 시점 작업으로서의 승격
    -   모든 엔티티 유형의 현재 상태
-   11절 추가: 구현 가이드
    -   컬럼 추가 (`uid`, `uid_method`, `uid_confidence`, `same_as_uid`)
    -   `resolve_uid()` 헬퍼 함수 설계
    -   정수 FK 공존 전략
    -   UID 생성 코드 예시
    -   점진적 적용 전략 (Phase A/B/C)
-   부록 A 추가: UID 요약 표
-   부록 B 추가: 변경 이력

## v0.1 (초안) — 2026-02-13

-   초기 버전
-   0절: 일반 UID 규칙 (형식, 정규화, 해싱)
-   1절: 참고문헌 UID 스키마 (DOI, 핑거프린트)
-   2절: 지층 UID 스키마 (사전, 핑거프린트)
-   3절: UID 거버넌스를 위한 메타데이터
-   4절: 운영 원칙

------------------------------------------------------------------------

문서 끝.
