# SCODA Stable UID Schema

Version: v0.2 (Draft)

This document defines the Stable UID (Unique Identifier) schema for
SCODA-based systems. It covers all entity types shared between Trilobase
and PaleoCore, and specifies how UIDs enable cross-package identity,
reference resolution, and entity lifecycle management.

The goals of Stable UID are:

1.  Same real-world entity → same UID, regardless of package (Trilobase
    / Paleocore)
2.  UID should remain stable over time
3.  UID generation must be reproducible
4.  UID must not depend on local database primary keys

------------------------------------------------------------------------

# 0. General UID Rules

## 0.1 UID Format

UIDs follow a URI-like namespace format:

    scoda:<entity_type>:<method>:<value>

Examples:

    scoda:bib:doi:10.1234/abcd.efgh
    scoda:bib:fp:sha256:<64hex>
    scoda:strat:formation:lexicon:USGS:123456
    scoda:strat:formation:fp:sha256:<64hex>

This makes the UID:

-   Human-readable
-   Namespace-aware
-   Extendable

------------------------------------------------------------------------

## 0.2 Normalization Rules (Required Before Hashing)

All fingerprint-based UIDs must use normalized input strings.

Required normalization:

-   Trim leading/trailing whitespace
-   Collapse multiple spaces into one
-   Convert to lowercase
-   Unicode normalization (NFKC recommended)
-   Remove or standardize punctuation (see entity-specific rules)

------------------------------------------------------------------------

## 0.3 Hashing

Fingerprint UIDs use:

-   SHA256
-   Hex output (64 characters)

Input must always be the canonical normalized string.

------------------------------------------------------------------------

# 1. Bibliography UID Schema

## 1.1 Priority Order

1.  DOI (preferred)
2.  Other global IDs (PMID, ISBN, arXiv, etc.)
3.  Bibliographic fingerprint (fp_v1)

------------------------------------------------------------------------

## 1.2 DOI-Based UID

UID:

    scoda:bib:doi:<normalized_doi>

Normalization rules:

-   Lowercase
-   Remove prefixes such as:
    -   https://doi.org/
    -   doi:
-   Remove whitespace

Example:

Input: https://doi.org/10.1000/ABC.DEF

UID: scoda:bib:doi:10.1000/abc.def

------------------------------------------------------------------------

## 1.3 Bibliographic Fingerprint (fp_v1)

Used when DOI is unavailable.

### Canonical String Construction

Recommended fields:

-   First author family name
-   Year
-   Title (normalized)
-   Container title (journal/book)
-   Volume (if available)
-   First page (if available)

Canonical string example:

    fa=kim|y=1998|t=trilobite systematics revision|c=j paleontology|v=12|p=123

### Normalization Details

Title and container:

-   Lowercase
-   Remove punctuation (.,:;()'" etc.)
-   Replace hyphen and slash with space
-   Convert & → and
-   Collapse whitespace

Author:

-   Use family name only
-   Lowercase

Page:

-   Use starting page only (recommended)

### UID Format

    scoda:bib:fp_v1:sha256:<hash>

### Collision Handling

If collision is detected:

    scoda:bib:fp_v1:sha256:<hash>-c2

Store additional metadata:

-   fingerprint_method_version (e.g., fp_v1)
-   fingerprint_source_fields
-   collision_counter

------------------------------------------------------------------------

# 2. Formation UID Schema

Formation entities are more complex due to regional duplication and
naming reuse.

## 2.1 Lexicon-Based UID (Preferred)

If official stratigraphic lexicon ID exists:

    scoda:strat:formation:lexicon:<authority>:<id>

Examples:

    scoda:strat:formation:lexicon:USGS:123456
    scoda:strat:formation:lexicon:BGS:78910

------------------------------------------------------------------------

## 2.2 Formation Fingerprint (fp_v1)

Used when no official ID exists.

### Canonical String Construction

Recommended fields:

-   formation_name (normalized)
-   rank (formation/member/group)
-   region (country/state/basin)
-   geologic_age (period or epoch)
-   stratigraphic context (optional but recommended)

Example canonical string:

    n=taebaek|r=formation|geo=kr:taebaek|age=cambrian|ctx=under xyz over abc

### Name Normalization

-   Lowercase
-   Remove "Formation", "Fm.", etc.
-   Remove punctuation
-   Collapse whitespace

### Region Standardization

Prefer ISO-based structure:

    KR:Taebaek
    US:NV:GreatBasin

### UID Format

    scoda:strat:formation:fp_v1:sha256:<hash>

------------------------------------------------------------------------

# 3. Country UID Schema

Countries are shared reference entities in PaleoCore, referenced by
domain packages (Trilobase, etc.) via `genus_locations.country_id`.

## 3.1 Priority Order

1.  ISO 3166-1 alpha-2 code (preferred)
2.  Country name fingerprint (fallback)

## 3.2 ISO-Based UID

UID:

    scoda:geo:country:iso3166-1:<code>

Normalization rules:

-   Uppercase the alpha-2 code
-   Must be a valid ISO 3166-1 alpha-2 code

Examples:

    scoda:geo:country:iso3166-1:KR       (South Korea)
    scoda:geo:country:iso3166-1:US       (United States)
    scoda:geo:country:iso3166-1:CN       (China)
    scoda:geo:country:iso3166-1:AU       (Australia)

Coverage: 96.5% of PaleoCore `countries` table (137/142) have a valid
COW mapping, and most of those correspond to ISO 3166-1 codes.

## 3.3 Name Fingerprint (Fallback)

For countries without an ISO code (e.g., historical or ambiguous
names):

UID:

    scoda:geo:country:fp_v1:sha256:<hash>

Canonical string:

    name=<normalized_country_name>

Normalization:

-   Lowercase
-   NFKC normalization
-   Collapse whitespace
-   Remove parenthetical qualifiers

Example:

    name=czech republic
    → scoda:geo:country:fp_v1:sha256:<hash>

## 3.4 Mapping to DB Schema

| UID Source | DB Column | Coverage |
|------------|-----------|----------|
| ISO 3166-1 alpha-2 | `countries.code` | 96.5% |
| Name fingerprint | `countries.name` | 100% (fallback) |

------------------------------------------------------------------------

# 4. Geographic Region UID Schema

Geographic regions represent sub-national divisions (states, provinces,
basins) within a country. They are stored in the PaleoCore
`geographic_regions` table.

## 4.1 UID Format

UID:

    scoda:geo:region:name:<country_iso>:<normalized_name>

The region UID combines the parent country's ISO code with the region's
normalized name to ensure global uniqueness.

Normalization rules for `<normalized_name>`:

-   Lowercase
-   NFKC normalization
-   Replace spaces with hyphens
-   Remove punctuation except hyphens

Examples:

    scoda:geo:region:name:US:nevada            (Nevada, USA)
    scoda:geo:region:name:CN:yunnan            (Yunnan, China)
    scoda:geo:region:name:AU:queensland        (Queensland, Australia)
    scoda:geo:region:name:KR:taebaek           (Taebaek, South Korea)

## 4.2 Fallback: Country Name Variant

When the parent country lacks an ISO code:

    scoda:geo:region:fp_v1:sha256:<hash>

Canonical string:

    country=<normalized_country_name>|name=<normalized_region_name>

## 4.3 Mapping to DB Schema

| UID Component | DB Column |
|---------------|-----------|
| Country ISO | `countries.code` (via `geographic_regions.parent_id`) |
| Region name | `geographic_regions.name` |

------------------------------------------------------------------------

# 5. ICS Chronostratigraphy UID Schema

ICS (International Commission on Stratigraphy) chronostratigraphic units
are global reference data from the GTS 2020 chart. Each unit has an
official SKOS URI assigned by the ICS.

## 5.1 Priority Order

1.  ICS SKOS URI (preferred — 100% coverage)
2.  Name fingerprint (not needed; ICS URI covers all units)

## 5.2 ICS URI-Based UID

UID:

    scoda:strat:ics:uri:<ics_uri>

The `<ics_uri>` is the full ICS SKOS URI as stored in
`ics_chronostrat.ics_uri`.

Examples:

    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Cambrian
    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Tremadocian
    scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Phanerozoic

Normalization rules:

-   Use the URI as-is (no lowercasing — URIs are case-sensitive)
-   No trailing slashes
-   Must match the canonical ICS SKOS vocabulary

## 5.3 Coverage

100% of `ics_chronostrat` records (178 units) have an `ics_uri`.
No fallback is needed.

## 5.4 Mapping to DB Schema

| UID Source | DB Column | Coverage |
|------------|-----------|----------|
| ICS SKOS URI | `ics_chronostrat.ics_uri` | 100% |

------------------------------------------------------------------------

# 6. Temporal Range UID Schema

Temporal ranges are the period codes used in Jell & Adrain (2002) to
denote geological time spans for trilobite genera. These are
domain-specific codes (LCAM, MCAM, etc.) stored in PaleoCore's
`temporal_ranges` table.

## 6.1 UID Format

UID:

    scoda:strat:temporal:code:<code>

The `<code>` is the short code exactly as stored in
`temporal_ranges.code`.

Examples:

    scoda:strat:temporal:code:LCAM       (Lower Cambrian)
    scoda:strat:temporal:code:MCAM       (Middle Cambrian)
    scoda:strat:temporal:code:UCAM       (Upper Cambrian)
    scoda:strat:temporal:code:LORD       (Lower Ordovician)
    scoda:strat:temporal:code:MISS       (Mississippian)
    scoda:strat:temporal:code:INDET      (Indeterminate)

Normalization rules:

-   Uppercase (codes are already uppercase by convention)
-   No spaces or punctuation

## 6.2 Relationship to ICS UIDs

Each temporal range code maps to one or more ICS units via
`temporal_ics_mapping`. The relationship is documented but not encoded
in the UID itself:

    scoda:strat:temporal:code:LCAM
      → maps to (aggregate):
        scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Terreneuvian
        scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Series2

## 6.3 Coverage

100% of `temporal_ranges` records (28 codes) have a unique `code`.

## 6.4 Mapping to DB Schema

| UID Source | DB Column | Coverage |
|------------|-----------|----------|
| Code | `temporal_ranges.code` | 100% |

------------------------------------------------------------------------

# 7. Taxonomy UID Schema

Taxonomic entities (genera, families, orders, etc.) are the core domain
data of packages like Trilobase. UID assignment follows ICZN
(International Code of Zoological Nomenclature) principles.

## 7.1 UID Format

UID:

    scoda:taxon:<rank>:<normalized_name>

Normalization rules:

-   `<rank>`: lowercase (genus, family, order, suborder, superfamily,
    class)
-   `<normalized_name>`: original capitalization preserved (taxonomic
    names are proper nouns)

Examples:

    scoda:taxon:genus:Paradoxides
    scoda:taxon:genus:Olenellus
    scoda:taxon:family:Paradoxididae
    scoda:taxon:order:Ptychopariida
    scoda:taxon:class:Trilobita

## 7.2 Uniqueness Guarantee

ICZN Principle of Homonymy (Article 52): within the animal kingdom, no
two genera may bear the same name. Therefore, the combination of
`genus` + name is globally unique for valid genera.

For higher ranks (family, order, etc.), names are also unique within
their rank by convention.

## 7.3 Invalid and Synonym Taxa

Invalid genera (synonyms, preoccupied names) still receive UIDs:

    scoda:taxon:genus:Bathynotus        (valid)
    scoda:taxon:genus:Bathynotellus     (j.s.s. of Bathynotus)

The synonym relationship is expressed via `same_as_uid` (see Section 8),
not in the UID itself:

    Bathynotellus.same_as_uid = scoda:taxon:genus:Bathynotus

## 7.4 Coverage

100% of `taxonomic_ranks` records (5,340) have a unique name within
their rank.

## 7.5 Mapping to DB Schema

| UID Component | DB Column |
|---------------|-----------|
| Rank | `taxonomic_ranks.rank` |
| Name | `taxonomic_ranks.name` |

------------------------------------------------------------------------

# 8. Metadata Governance

(Expanded from v0.1 Section 3)

## 8.1 Required Columns

Each entity table that participates in UID should store:

| Column | Type | Description |
|--------|------|-------------|
| `uid` | TEXT | The computed Stable UID |
| `uid_method` | TEXT | Method used: `doi`, `fp_v1`, `lexicon`, `iso3166-1`, `ics_uri`, `code`, `name` |
| `uid_confidence` | TEXT | Confidence level (see 8.2) |
| `same_as_uid` | TEXT | Optional equivalence link to another entity's UID |

## 8.2 Confidence Levels

| Level | Criteria | Examples |
|-------|----------|---------|
| `high` | Based on an externally governed, globally unique identifier | DOI, ICS URI, ISO 3166-1 code, ICZN genus name |
| `medium` | Based on a composite fingerprint with well-defined fields | Bibliographic fingerprint, formation fingerprint |
| `low` | Based on partial or ambiguous information | Incomplete citations, unresolvable country names |

## 8.3 `same_as_uid` Directionality

The `same_as_uid` field always points from the **less authoritative**
entity to the **more authoritative** one:

    less authoritative → more authoritative

Examples:

-   Junior synonym → senior synonym:
    `Bathynotellus.same_as_uid → scoda:taxon:genus:Bathynotus`

-   Preoccupied name → replacement name:
    `Ampyx.same_as_uid → scoda:taxon:genus:Lonchodomas`

-   Local duplicate → canonical source:
    `trilobase:bibliography[42].same_as_uid → scoda:bib:doi:10.1234/xyz`

## 8.4 Population Priority

UID population should be prioritized by entity type, based on coverage
and difficulty:

| Priority | Entity | Method | Expected Coverage |
|----------|--------|--------|-------------------|
| 1 | ICS Chronostratigraphy | ICS URI | 100% |
| 2 | Temporal Ranges | Code | 100% |
| 3 | Taxonomy | Rank + Name | 100% |
| 4 | Countries | ISO 3166-1 | 96.5% |
| 5 | Geographic Regions | Country + Name | ~100% |
| 6 | Bibliography | DOI / fingerprint | TBD |
| 7 | Formations | Lexicon / fingerprint | TBD |

------------------------------------------------------------------------

# 9. Cross-Package Reference Resolution

## 9.1 Problem

When a Trilobase entity references a UID (e.g., a genus's country), the
runtime must determine which package's database contains the canonical
record for that UID.

Example scenario:

-   `Paradoxides` (Trilobase) references `scoda:geo:country:iso3166-1:CZ`
-   That country record may exist in PaleoCore (canonical) or could
    temporarily exist in a local package during development

## 9.2 Resolution Algorithm

The `resolve_uid()` function searches databases in **dependency order**:

```
resolve_uid(conn, entity_type, uid):
    1. Search dependency packages first (in manifest.json order)
       → e.g., pc.countries WHERE uid = :uid
    2. Search local package
       → e.g., main.countries WHERE uid = :uid
    3. Return NULL if not found
```

## 9.3 Scope Chain

The search order is derived from `manifest.json` dependencies:

```json
{
  "name": "trilobase",
  "dependencies": [
    {"name": "paleocore", "version": ">=0.3.0"}
  ]
}
```

Resolution order for Trilobase:
1. `pc.*` (PaleoCore — dependency)
2. `main.*` (Trilobase — local)

For packages with multiple dependencies:
```json
{
  "dependencies": [
    {"name": "paleocore"},
    {"name": "geodata"}
  ]
}
```

Resolution order:
1. `pc.*` (PaleoCore — first dependency)
2. `geodata.*` (Geodata — second dependency)
3. `main.*` (local)

## 9.4 Precedence Rule: Dependency Wins

When the same UID exists in both a dependency and the local package:

-   **Dependency always wins** — the dependency package is the canonical
    source
-   Local copies are considered stale or transitional

Rationale: Dependencies are curated shared infrastructure (e.g.,
PaleoCore provides authoritative country and formation data). Local
packages should defer to them.

## 9.5 Current Implementation

In the current SCODA Desktop runtime, resolution is implicit via SQLite
ATTACH:

```python
conn = sqlite3.connect('trilobase.db')                    # main
conn.execute("ATTACH 'paleocore.db' AS pc")               # dependency
conn.execute("ATTACH 'trilobase_overlay.db' AS overlay")   # overlay

# Cross-DB JOIN resolves references at query time
SELECT g.name, c.name AS country
FROM genus_locations gl
JOIN taxonomic_ranks g ON gl.genus_id = g.id
JOIN pc.countries c ON gl.country_id = c.id
```

UID-based resolution is a future enhancement that operates alongside
(not replacing) the integer FK-based JOINs.

------------------------------------------------------------------------

# 10. Entity Lifecycle and Migration

## 10.1 Problem

Entities can originate in a domain package (e.g., Trilobase) and later
be recognized as shared infrastructure that belongs in a core package
(e.g., PaleoCore). The UID must remain stable throughout this
migration.

Example: A bibliography entry for a trilobite paper exists only in
Trilobase. Later, a brachiopod package (Brachiobase) also needs the
same paper. The paper should be promoted to PaleoCore.

## 10.2 Lifecycle Stages

| Stage | Location | Description |
|-------|----------|-------------|
| **Local-only** | Domain package only | Entity exists in one package (e.g., Trilobase). UID assigned locally. |
| **Duplicated** | Multiple domain packages | Same real-world entity appears in 2+ packages with the same UID. No canonical source yet. |
| **Promoted** | Core package (canonical) + stubs | Entity migrated to PaleoCore. Domain packages retain stubs. |
| **Stub** | Domain package (post-promotion) | Only `(id, uid)` remain in the domain package to preserve FK integrity. Data served from core. |

## 10.3 Stage Transitions

```
Local-only ──→ Duplicated ──→ Promoted
                                 │
                                 ▼
                              Stub (in source packages)
```

### Local-only → Duplicated

Occurs naturally when a second domain package independently creates a
record for the same real-world entity. Detection requires UID
comparison across packages.

### Duplicated → Promoted

**This is a release-time operation, not a runtime operation.**

Steps:
1.  Identify duplicated UIDs across domain packages
2.  Choose the most complete record as the canonical version
3.  Insert the canonical record into PaleoCore
4.  In each domain package, replace the full record with a stub

### Promoted → Stub

After promotion, the domain package retains a minimal stub:

```sql
-- Before promotion (full record in Trilobase bibliography):
INSERT INTO bibliography VALUES (42, 'Kim, J.', 1998, NULL,
    'Trilobite systematics revision', 'J. Paleontology', ...);

-- After promotion (stub in Trilobase):
-- The record is removed from local DB.
-- genus_formations/genus_locations FK references now resolve
-- via pc.* prefix (PaleoCore).
```

For entities like countries and formations that are already in PaleoCore
(Phase 34 DROP), the promotion is complete. The local tables were
dropped and all queries use `pc.*` prefix.

## 10.4 UID Stability Guarantee

The UID **never changes** during lifecycle transitions:

    scoda:bib:doi:10.1234/xyz

This UID is identical whether the record is in Trilobase (local-only),
in both Trilobase and Brachiobase (duplicated), or in PaleoCore
(promoted).

## 10.5 Current Status

| Entity | Lifecycle Stage | Notes |
|--------|----------------|-------|
| Countries | Promoted | In PaleoCore since Phase 34 |
| Geographic Regions | Promoted | In PaleoCore since Phase 34 |
| Formations | Promoted | In PaleoCore since Phase 34 |
| ICS Chronostratigraphy | Promoted | In PaleoCore since Phase 34 |
| Temporal Ranges | Promoted | In PaleoCore since Phase 34 |
| Taxonomy | Local-only | Trilobase only (no other domain package yet) |
| Bibliography | Local-only | Trilobase only (promotion candidate when shared) |
| Synonyms | Local-only | Trilobase only (domain-specific) |

------------------------------------------------------------------------

# 11. Implementation Guidance

## 11.1 Column Additions

To support UIDs, add 4 columns to each participating entity table:

```sql
ALTER TABLE <table> ADD COLUMN uid TEXT;
ALTER TABLE <table> ADD COLUMN uid_method TEXT;
ALTER TABLE <table> ADD COLUMN uid_confidence TEXT DEFAULT 'medium';
ALTER TABLE <table> ADD COLUMN same_as_uid TEXT;

CREATE UNIQUE INDEX idx_<table>_uid ON <table>(uid);
```

## 11.2 `resolve_uid()` Helper Function

```python
def resolve_uid(conn, entity_type, uid):
    """
    Resolve a UID to a database record, searching dependencies first.

    Args:
        conn: SQLite connection with dependencies ATTACHed
        entity_type: e.g., 'country', 'formation', 'bibliography'
        uid: the Stable UID string

    Returns:
        dict with record data and source_package, or None
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

    # Search dependency packages first (dependency wins)
    for alias in _get_dependency_aliases(conn):
        row = conn.execute(
            f"SELECT * FROM {alias}.{table} WHERE uid = ?", (uid,)
        ).fetchone()
        if row:
            return {'data': row, 'source_package': alias}

    # Search local package
    row = conn.execute(
        f"SELECT * FROM {table} WHERE uid = ?", (uid,)
    ).fetchone()
    if row:
        return {'data': row, 'source_package': 'main'}

    return None
```

## 11.3 Coexistence with Integer FKs

UIDs do **not replace** integer foreign keys. The two systems coexist:

| Concern | Mechanism |
|---------|-----------|
| Query performance | Integer FK + JOIN (existing) |
| Cross-package identity | UID (new) |
| Deduplication | UID comparison |
| Migration tracking | UID + lifecycle stage |

Integer FKs remain the primary query mechanism. UIDs are used for
identity verification, cross-package deduplication, and entity
lifecycle management.

## 11.4 UID Generation Examples

```python
import hashlib

def uid_country(code):
    """Generate UID for a country with ISO code."""
    if code:
        return f"scoda:geo:country:iso3166-1:{code.upper()}"
    return None

def uid_country_fp(name):
    """Generate fingerprint UID for a country without ISO code."""
    normalized = normalize(name)  # lowercase, NFKC, collapse spaces
    h = hashlib.sha256(f"name={normalized}".encode()).hexdigest()
    return f"scoda:geo:country:fp_v1:sha256:{h}"

def uid_ics(ics_uri):
    """Generate UID for an ICS chronostratigraphic unit."""
    return f"scoda:strat:ics:uri:{ics_uri}"

def uid_temporal(code):
    """Generate UID for a temporal range code."""
    return f"scoda:strat:temporal:code:{code.upper()}"

def uid_taxon(rank, name):
    """Generate UID for a taxonomic entity."""
    return f"scoda:taxon:{rank.lower()}:{name}"

def uid_region(country_iso, region_name):
    """Generate UID for a geographic region."""
    normalized = region_name.lower().replace(' ', '-')
    return f"scoda:geo:region:name:{country_iso.upper()}:{normalized}"

def uid_bib_doi(doi):
    """Generate UID for a bibliography entry with DOI."""
    normalized = doi.lower()
    for prefix in ['https://doi.org/', 'http://doi.org/', 'doi:']:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return f"scoda:bib:doi:{normalized}"

def uid_formation_lexicon(authority, lexicon_id):
    """Generate UID for a formation with lexicon ID."""
    return f"scoda:strat:formation:lexicon:{authority}:{lexicon_id}"
```

## 11.5 Population Strategy

UID population should be implemented incrementally:

**Phase A — Deterministic UIDs (no ambiguity):**
-   `ics_chronostrat`: `uid_ics(ics_uri)` → 178 records, 100% coverage
-   `temporal_ranges`: `uid_temporal(code)` → 28 records, 100% coverage
-   `taxonomic_ranks`: `uid_taxon(rank, name)` → 5,340 records, 100%
    coverage
-   `countries`: `uid_country(code)` → 137/142 records (96.5%)

**Phase B — Composite UIDs:**
-   `geographic_regions`: `uid_region(country_iso, name)` → 562 records
-   `countries` (remaining 5): `uid_country_fp(name)` → fallback

**Phase C — External lookup required:**
-   `bibliography`: DOI lookup via CrossRef API, then fingerprint fallback
-   `formations`: Lexicon lookup (USGS, BGS), then fingerprint fallback

------------------------------------------------------------------------

# Appendix A: UID Summary Table

| Entity | UID Pattern | Method | Confidence | DB Table |
|--------|-------------|--------|------------|----------|
| Bibliography (DOI) | `scoda:bib:doi:<doi>` | `doi` | high | `bibliography` |
| Bibliography (FP) | `scoda:bib:fp_v1:sha256:<hash>` | `fp_v1` | medium | `bibliography` |
| Formation (Lexicon) | `scoda:strat:formation:lexicon:<auth>:<id>` | `lexicon` | high | `formations` |
| Formation (FP) | `scoda:strat:formation:fp_v1:sha256:<hash>` | `fp_v1` | medium | `formations` |
| Country (ISO) | `scoda:geo:country:iso3166-1:<code>` | `iso3166-1` | high | `countries` |
| Country (FP) | `scoda:geo:country:fp_v1:sha256:<hash>` | `fp_v1` | medium | `countries` |
| Region | `scoda:geo:region:name:<iso>:<name>` | `name` | high | `geographic_regions` |
| Region (FP) | `scoda:geo:region:fp_v1:sha256:<hash>` | `fp_v1` | medium | `geographic_regions` |
| ICS Unit | `scoda:strat:ics:uri:<uri>` | `ics_uri` | high | `ics_chronostrat` |
| Temporal Range | `scoda:strat:temporal:code:<code>` | `code` | high | `temporal_ranges` |
| Taxon | `scoda:taxon:<rank>:<name>` | `name` | high | `taxonomic_ranks` |

------------------------------------------------------------------------

# Appendix B: Changelog

## v0.2 (Draft) — 2026-02-15

-   Added Section 3: Country UID Schema
-   Added Section 4: Geographic Region UID Schema
-   Added Section 5: ICS Chronostratigraphy UID Schema
-   Added Section 6: Temporal Range UID Schema
-   Added Section 7: Taxonomy UID Schema
-   Expanded Section 8: Metadata Governance (from v0.1 Section 3)
    -   Added `uid_confidence` level definitions
    -   Added `same_as_uid` directionality rules
    -   Added population priority table
-   Added Section 9: Cross-Package Reference Resolution
    -   Scope chain derived from manifest.json dependencies
    -   Dependency-wins precedence rule
-   Added Section 10: Entity Lifecycle and Migration
    -   4-stage lifecycle: Local-only → Duplicated → Promoted → Stub
    -   Promotion as release-time operation
    -   Current status of all entity types
-   Added Section 11: Implementation Guidance
    -   Column additions (`uid`, `uid_method`, `uid_confidence`, `same_as_uid`)
    -   `resolve_uid()` helper function design
    -   Integer FK coexistence strategy
    -   UID generation code examples
    -   Incremental population strategy (Phase A/B/C)
-   Added Appendix A: UID Summary Table
-   Added Appendix B: Changelog

## v0.1 (Draft) — 2026-02-13

-   Initial version
-   Section 0: General UID Rules (format, normalization, hashing)
-   Section 1: Bibliography UID Schema (DOI, fingerprint)
-   Section 2: Formation UID Schema (lexicon, fingerprint)
-   Section 3: Metadata for UID Governance
-   Section 4: Operational Principle

------------------------------------------------------------------------

End of document.
