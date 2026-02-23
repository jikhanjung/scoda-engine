# Trilobase Tree Snapshot Design (v1 Draft)

**Date:** 2026-02-22T12:14:01.069916

------------------------------------------------------------------------

## 1. Problem Definition

In Trilobase, multiple taxonomic opinions coexist within a single SCODA
package. A researcher must be able to:

-   Explicitly define which taxonomic structure (tree) they accept.
-   Preserve that structure as a reproducible snapshot.
-   Cite the snapshot in publications.
-   Ensure reproducibility even if Trilobase evolves over time.

A Trilobase package version alone does not uniquely define a taxonomic
tree. Therefore, a separate **Tree Snapshot mechanism** is required.

------------------------------------------------------------------------

## 2. Conceptual Model

A tree snapshot is not just a resolved tree result. It is defined as:

> A combination of **selection rules + explicit overrides**, evaluated
> against a specific Trilobase package version.

This ensures: - Reproducibility - Explainability - Future extensibility

------------------------------------------------------------------------

## 3. Snapshot Core Principles

### 3.1 Immutability

-   Once created, a snapshot cannot be modified.
-   Any modification generates a new snapshot.
-   Snapshots are content-addressed (hash-based identity).

### 3.2 Package Binding

Each snapshot is tied to:

    package_uid

Snapshots are valid only relative to the referenced Trilobase package
version.

### 3.3 Content-Based UID

1.  Canonicalize snapshot JSON
2.  Compute SHA-256 hash
3.  Generate:

```{=html}
<!-- -->
```
    scoda:view:trilobase:<package_uid>:<snapshot_hash>

This guarantees integrity and citation stability.

------------------------------------------------------------------------

## 4. Snapshot JSON Schema (v1)

``` json
{
  "schema": "scoda.view_snapshot.v1",
  "package_uid": "scoda:pkg:trilobase:2026.2.0",
  "created_at": "2026-02-22T10:30:00+09:00",
  "label": "Taebaek-LateCambrian-View",
  "description": "Default Adrain 2011 with local overrides.",
  "rules": [
    {"type": "prefer_opinion", "opinion_id": "op:adrain2011", "priority": 100}
  ],
  "overrides": [
    {"taxon_id": "tx:Q_elongatus", "set_parent": "tx:SomeGenus"},
    {"taxon_id": "tx:A_subglobosa", "treat_as_valid": true}
  ],
  "options": {
    "conflict_policy": "override_wins",
    "synonym_policy": "collapse",
    "rank_policy": "strict"
  }
}
```

------------------------------------------------------------------------

## 5. Internal Data Model (Engine Side)

Core conceptual tables:

-   opinion
-   assertion
-   view_snapshot
-   view_rule
-   view_override

Optional: - view_result_cache (resolved tree caching)

------------------------------------------------------------------------

## 6. ViewResolver Component

The Scoda Engine includes:

    ViewResolver(snapshot, package_db) -> ResolvedTree

Resolution process:

1.  Apply rule-based priority
2.  Score candidate assertions
3.  Apply overrides (force decisions)
4.  Detect conflicts (multiple parents, cycles)
5.  Produce resolved tree
6.  Attach explanation metadata per edge

Each parent-child edge should store: - selected assertion - reason for
selection - alternative candidates

------------------------------------------------------------------------

## 7. UI Workflow

### Step 1: View Builder

-   Select base opinion
-   Configure policies

### Step 2: Conflict Inspector

-   Display ambiguous taxa
-   Allow explicit override selection

### Step 3: Tree Explorer

-   Browse resolved tree
-   Inspect justification per node

### Step 4: Snapshot Manager

-   Save snapshot
-   Export JSON
-   Copy citation UID

------------------------------------------------------------------------

## 8. Implementation Roadmap

### Phase 1 (Minimal Functional)

-   Single base opinion
-   Parent override support
-   Export/Import snapshot
-   UID hash generation

### Phase 2 (Extended)

-   Conditional rule priorities
-   Synonym/rank policies
-   Snapshot diff comparison
-   Result caching

------------------------------------------------------------------------

## 9. Server Strategy (Deferred)

Tree snapshot system must function offline first.

Server responsibilities (future): - Store immutable snapshot JSON -
Provide retrieval by hash - Offer metadata index

Minimal viable server: - Object storage + index file

------------------------------------------------------------------------

## 10. Design Philosophy

-   Snapshot = reproducible scientific claim
-   Package = curated taxonomic knowledge base
-   Engine = resolver + explainer

The snapshot system formalizes: \> "This is the taxonomic tree I adopt."

This enables citation, reproducibility, and long-term archival
stability.
