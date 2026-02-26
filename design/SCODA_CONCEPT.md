# Trilobase as a SCODA
## Reframing Trilobase as a Self-Contained Data Artifact

---

## Purpose of This Document

This document describes **Trilobase** through the lens of **SCODA (Self-Contained Data Artifact)**.

It does **not** replace the technical README or database schema documentation.
Instead, it clarifies:

- What Trilobase *is* as a distributed knowledge object
- What responsibilities it takes (and deliberately avoids)
- How it should be used, extended, and cited

---

## What Trilobase Is (as a SCODA)

**Trilobase is a versioned, authoritative snapshot of trilobite genus-level taxonomy,
distributed as a self-contained data artifact.**

In SCODA terms:

- Trilobase is **not a service**
- Trilobase is **not a continuously synchronized database**
- Trilobase *is* a **reference artifact** representing the state of taxonomic knowledge at a given time

---

## Core Mapping: Trilobase → SCODA

| SCODA Component | Trilobase Implementation |
|----------------|--------------------------|
| Data | SQLite database containing taxonomic tables |
| Identity | Project name + semantic version |
| Semantics | Database schema, rank hierarchy, synonym relations |
| Provenance | Source literature (Jell & Adrain 2002; Adrain 2011) |
| Integrity | Immutable release artifacts; versioned updates |

---

## Immutability and Versioning

Each released version of Trilobase:

- Is treated as **read-only**
- Represents a *curated snapshot* of taxonomic interpretation
- Can be cited, archived, and reproduced

Any modification to the canonical data results in:

- A **new version**
- A **new SCODA artifact**
- An explicit update in provenance

This mirrors how taxonomic opinions evolve through publication,
not through silent mutation.

---

## Local Use and Extension

When a user opens Trilobase locally:

- The base artifact remains immutable
- Local changes are limited to:
  - Notes
  - Annotations
  - Alternative interpretations
  - Links to additional literature

These local extensions:

- Do **not** overwrite canonical taxonomy
- Are not automatically synchronized
- Exist as personal overlays

---

## Multiple Interpretations and "Sensu" Concepts

Taxonomic disagreement is an expected condition.

Trilobase supports this by allowing:

- Multiple taxonomic **concepts** to coexist
- Each concept to be explicitly labeled (e.g., *sensu Adrain, 2011*)
- Each assertion to be traceable to a source reference

The default distributed artifact may select one
**recommended concept set**, while preserving alternatives.

---

## Upgrades and Data Evolution

Updates to Trilobase occur through:

1. Curation and review
2. Generation of a new SCODA artifact
3. Explicit distribution of the new version

Users may choose when (or whether) to upgrade.

There is no implicit synchronization across installations.

---

## What Trilobase Explicitly Does Not Do

As a SCODA, Trilobase intentionally avoids:

- Real-time collaborative editing
- Automatic merge of conflicting interpretations
- Centralized live APIs as the primary interface
- Silent modification of historical data

These are features of *services*, not *artifacts*.

---

## Why This Matters

Treating Trilobase as a SCODA ensures:

- Scientific accountability
- Reproducibility of analyses
- Transparent evolution of taxonomic knowledge
- Clear separation between authoritative data and personal reasoning

In short:

> **Trilobase is not a database you connect to.  
> It is a knowledge object you open.**

---

## SCODA Engine: The Runtime Ecosystem

A .scoda package is a data artifact. The software that **opens, explores, and serves** this artifact is the **SCODA Engine**.

### Definition

> **SCODA Engine is a runtime that loads .scoda packages and provides data through a Web UI, REST API, and MCP endpoints.**

The Engine does not create data. Its role is to **read, query, and visualize** the data inside a package.

### Product Structure

| Product | Audience | Description |
|---------|----------|-------------|
| **SCODA Desktop** | Individual users | Local execution, tkinter GUI, single package, overlay support |
| **SCODA Server** | Institutions / public services | Multi-user, authentication, scaling (future) |

Both products share the same Engine core:

- .scoda package loader (`scoda_package.py`)
- Generic Viewer (automatic rendering based on manifest)
- REST API (`/api/query/`, `/api/composite/`)
- MCP server (stdio/SSE)

The difference between Desktop and Server is **deployment form and access control**; the data processing logic is identical.

### Related Concepts

| Name | Role |
|------|------|
| **.scoda** | Package format (SQLite DB + manifest + overlay) |
| **SCODA Engine** | Runtime that serves .scoda packages (Desktop / Server) |
| **SCODA Hub** | Package registry / repository (future concept) |

### SCODA Is an Artifact; Engine Is a Tool

The core principle of the SCODA concept is the **separation of data and software**:

- A .scoda package exists independently as a SQLite file, even without the Engine
- The Engine is merely a **tool** for conveniently exploring packages — it is not part of the data
- The same .scoda package yields identical data whether opened in Desktop or served via Server

---

## Status

This document defines the **conceptual role** of Trilobase within the SCODA framework.

The SCODA Engine ecosystem — including Desktop, Server, and Hub — is described
as part of the broader runtime architecture that serves SCODA artifacts.

Implementation details, runtime behavior, and contribution workflows
are defined in separate technical documents.
