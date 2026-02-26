# SCODA Engine

**Runtime for Self-Contained Data Artifacts**

---

SCODA Engine is a generic viewer and server for `.scoda` data packages. It provides a manifest-driven web UI, REST API, and MCP (Model Context Protocol) server — all without any domain-specific code.

## What is SCODA?

**SCODA (Self-Contained Open Data Artifact)** is a packaging format for distributing scientific data as immutable, versioned artifacts. A `.scoda` file bundles data, schema, metadata, and UI definitions into a single self-contained ZIP archive.

> **A SCODA package is not a database you connect to — it is a knowledge object you open.**

## Key Features

- **Zero Domain Code** — All domain logic comes from `.scoda` packages
- **Manifest-Driven UI** — Views, tables, trees, and detail modals auto-generated from package manifest
- **Named Queries** — SQL stored inside the package, executed by name
- **3-DB Architecture** — Canonical (immutable) + Overlay (user annotations) + Dependency (shared data)
- **MCP Server** — LLM integration via Model Context Protocol (stdio/SSE)
- **SCODA Hub** — Static package registry for discovery and download
- **Standalone Build** — PyInstaller EXE for Windows, no installation required

## Quick Start

### Installation

```bash
git clone https://github.com/jikhanjung/scoda-engine.git
cd scoda-engine
pip install -e ./core
pip install -e ".[dev]"
```

### Run the Server

```bash
# Web server
python -m scoda_engine.serve

# With a specific .scoda package
python -m scoda_engine.serve --scoda-path /path/to/data.scoda

# GUI control panel
python launcher_gui.py
```

### Run Tests

```bash
pytest tests/
```

## Documentation

### Concepts

- [SCODA Concept](SCODA_CONCEPT.md) — What SCODA is and how Trilobase exemplifies it
- [Architecture Summary](SCODA_Concept_and_Architecture_Summary.md) — SCODA as a stateful knowledge system
- [Whitepaper](SCODA_WHITEPAPER.md) — Full specification: package format, manifest, viewer, MCP
- [Stable UID Schema](SCODA_Stable_UID_Schema_v0.2.md) — Cross-package entity identification

### Guides

- [API Reference](API_REFERENCE.md) — REST API endpoints and usage
- [MCP Guide](MCP_GUIDE.md) — MCP server setup and tool reference
- [Hub Manifest Spec](HUB_MANIFEST_SPEC.md) — Hub registry schema and workflow
- [Release Guide](RELEASE_GUIDE.md) — Build, package, and release process

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              SCODA Desktop                   │
│                                              │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │   GUI    │ │  FastAPI  │ │ MCP Server  │  │
│  │(tkinter) │ │  Server   │ │ (stdio/SSE) │  │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘  │
│       └──────┬──────┘──────────────┘         │
│              ↓                                │
│     ┌────────────────┐                        │
│     │ scoda_package   │  PackageRegistry      │
│     └───────┬────────┘                        │
│             ↓                                 │
│  ┌──────────────────────────────────┐         │
│  │    SQLite (3-DB ATTACH)          │         │
│  │  main: data.db (canonical, R/O) │         │
│  │  overlay: overlay.db (user, R/W)│         │
│  │  dep: dependency.db (infra, R/O)│         │
│  └──────────────────────────────────┘         │
└─────────────────────────────────────────────┘
```

## License

SCODA Engine is open source. See the [GitHub repository](https://github.com/jikhanjung/scoda-engine) for details.
