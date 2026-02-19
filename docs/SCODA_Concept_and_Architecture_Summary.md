# SCODA: A Stateful, Historically Explicit Knowledge System
*A synthesis of the SCODA concept, architecture, and research philosophy discussed in this thread*

---

## 1. What is SCODA?

**SCODA** is a concept-centered, stateful knowledge system designed to represent, explore, and operationalize the *historical dynamics of scientific concepts*.  
Rather than treating scientific knowledge as a collection of static definitions or finalized snapshots (e.g., PDFs, charts, vocabularies), SCODA treats knowledge as something that **exists in time**, with identifiable states, usages, and transformations.

At its core, SCODA answers a simple but under-supported question:

> *What did a scientific concept mean, to whom, and at what time?*

This question is especially critical in domains such as stratigraphy, taxonomy, and paleontology, where:
- terms persist while meanings change,
- regional and historical concepts coexist with official standards,
- and past literature remains scientifically relevant.

---

## 2. Motivation: The Limits of Snapshot-Based Knowledge

Traditional scientific knowledge dissemination relies on:
- PDFs and printed charts,
- static or semi-interactive web pages,
- machine-readable but *atemporal* representations (e.g., SKOS/RDF vocabularies).

All of these, regardless of format, ultimately represent **snapshots**:
- a single, frozen view of knowledge,
- usually reflecting the most recent consensus.

This model breaks down when:
- interpreting historical literature,
- comparing competing or superseded concepts,
- understanding why current standards took their present form.

SCODA does not attempt to eliminate snapshots.  
Instead, it **demotes them to exports** derived from a continuously running system.

---

## 3. SCODA vs SKOS and Related Standards

SKOS and similar RDF-based vocabularies excel at:
- expressing hierarchical relations,
- providing machine-readable identifiers,
- enabling interoperability across systems.

However, SKOS primarily answers:
> *What is this concept (now)?*

SCODA addresses a complementary but distinct dimension:
> *How has this concept been used, contested, and transformed over time?*

Key distinctions:

| Aspect | SKOS | SCODA |
|------|------|-------|
| Temporal modeling | Implicit / weak | Explicit, first-class |
| Historical usage | Not native | Core data |
| Competing concepts | Limited | Explicitly modeled |
| Output | Static vocabularies | Executable system + exports |
| Primary question | What is it? | How did it come to be? |

SCODA can export RDF/SKOS representations, but RDF is treated as a **projection**, not the core.

---

## 4. Historical Concepts and “Knowledge in Time”

A central SCODA use case is **historical interpretation**.

Example:
- A 1934 stratigraphic paper refers to “Tommotian”.
- The term is no longer an official ICS unit.
- Its meaning varies by author, region, and decade.

SCODA enables:
- querying a concept *as of a specific year*,
- tracing author-specific usages,
- comparing historical terms to modern standards without retroactively imposing authority.

This makes SCODA particularly suited to:
- stratigraphic correlation charts,
- regional stage names,
- taxonomic concepts (sensu lato / sensu stricto),
- and legacy literature interpretation.

---

## 5. Official vs Historical Units: System-Level Distinction

A critical design principle is that **not all concepts are equal**.

SCODA distinguishes units at the data level:
- official / ratified (e.g., ICS units),
- regional or historical,
- informal or obsolete.

This distinction drives:
- query behavior,
- narrative tone,
- and LLM prompt selection.

The system—not the language model—decides whether a concept may be described authoritatively or must be treated cautiously and historically.

---

## 6. SCODA as a “Knowledge Runtime”

SCODA is best understood not as a dataset, but as a **runtime environment for knowledge**.

- The database stores concept states and evidence.
- The interface allows users to explore and filter those states.
- Snapshots (PDFs, charts, RDF) are *outputs*, not the system itself.

This leads to a key conceptual shift:

> **SCODA distributes a system from which snapshots can be reproducibly derived, rather than distributing snapshots themselves.**

---

## 7. Architecture Overview

### 7.1 Local, API-Driven Design

SCODA is implemented as:
- a local desktop application,
- exposing a REST/JSON API,
- backed by a structured concept database.

Both human-facing UI and machine-facing interfaces use the same deterministic query layer.

### 7.2 MCP (Model Context Protocol) Integration

SCODA’s local API can be wrapped as an **MCP server**.

In this model:
- SCODA exposes a predefined set of read-only query tools,
- LLMs select tools but never access the database directly,
- SCODA executes queries and constructs *Evidence Packs*,
- LLMs convert evidence into human-readable narratives.

This ensures:
- reproducibility,
- safety,
- and strict separation of authority and narration.

---

## 8. Evidence Packs: Evidence-First by Design

LLMs never see raw database output.

Instead, SCODA constructs **Evidence Packs** containing:
- concept metadata,
- chronological usage records,
- relations to other concepts,
- mappings with explicit confidence,
- and bibliographic references.

All generated text must be grounded in these packs, enforcing citation-first behavior.

---

## 9. Role of Language Models

In SCODA:
- LLMs do **not** define concepts,
- do **not** arbitrate validity,
- and do **not** introduce new facts.

They act as:
> *controlled narrative engines that translate structured historical evidence into readable text*.

This design aligns with scholarly expectations and avoids “AI as authority” pitfalls.

---

## 10. UI and Interaction Philosophy

SCODA emphasizes:
- discoverability through search and structured browsing,
- optional historical visualization (e.g., time sliders),
- comparison of competing concepts,
- and multiple views (tables, trees, networks).

Chat-based interaction is treated as:
- an alternative interface to the same query system,
- not a replacement for structured exploration.

---

## 11. “Knowledge Paleontology” and Ontology

Conceptually, SCODA aligns with ideas reminiscent of:
- the archaeology of knowledge,
- historical epistemology,
- and what might be informally called **“knowledge paleontology”**.

The goal is not to essentialize concepts, but to:
- preserve their stratigraphy,
- expose their transformations,
- and make their historical layers explorable.

This is an ontological stance, not merely an epistemic one.

---

## 12. Why SCODA Matters

SCODA enables:
- historically faithful literature research,
- reproducible interpretation of legacy concepts,
- transparent mapping between past and present standards,
- and new forms of interaction between humans, databases, and language models.

It represents a shift from *reading knowledge* to *querying its history*.

---

## 13. One-Sentence Positioning

> **SCODA is a stateful, concept-centered knowledge system that makes the historical dynamics of scientific concepts explicit, queryable, and reproducible.**

---

## 14. Outlook

SCODA is not limited to stratigraphy or paleontology.
Any domain where concepts:
- persist across time,
- change meaning,
- and accumulate historical layers,
can benefit from this approach.

The system is designed to grow incrementally:
from local tools, to shared infrastructures, to community-driven knowledge runtimes.

---
