"""
Shared test fixtures for Trilobase test suite.
"""

import json
import sqlite3
import os
import sys

import pytest

import scoda_engine.scoda_package as scoda_package
from scoda_engine.app import app
from scoda_engine.scoda_package import get_db, ScodaPackage

# Import overlay DB init (used by test_db fixture)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))
from init_overlay_db import create_overlay_db


@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def test_db(tmp_path):
    """Create temporary test databases (canonical + overlay) with sample data."""
    canonical_db_path = str(tmp_path / "test_trilobase.db")
    overlay_db_path = str(tmp_path / "test_overlay.db")

    # Create CANONICAL database
    conn = sqlite3.connect(canonical_db_path)
    cursor = conn.cursor()

    # Create tables (canonical only - NO user_annotations)
    cursor.executescript("""
        CREATE TABLE taxonomic_ranks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rank TEXT NOT NULL,
            parent_id INTEGER,
            author TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            genera_count INTEGER DEFAULT 0,
            year TEXT,
            year_suffix TEXT,
            type_species TEXT,
            type_species_author TEXT,
            formation TEXT,
            location TEXT,
            temporal_code TEXT,
            is_valid INTEGER DEFAULT 1,
            raw_entry TEXT,
            family TEXT,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            is_placeholder INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
        );
        CREATE UNIQUE INDEX idx_taxonomic_ranks_uid ON taxonomic_ranks(uid);

        CREATE TABLE synonyms (
            id INTEGER PRIMARY KEY,
            junior_taxon_id INTEGER,
            senior_taxon_name TEXT,
            synonym_type TEXT,
            fide_author TEXT,
            fide_year TEXT,
            notes TEXT,
            senior_taxon_id INTEGER,
            FOREIGN KEY (junior_taxon_id) REFERENCES taxonomic_ranks(id)
        );

        CREATE TABLE genus_formations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genus_id INTEGER NOT NULL,
            formation_id INTEGER NOT NULL,
            is_type_locality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
            UNIQUE(genus_id, formation_id)
        );

        CREATE TABLE genus_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genus_id INTEGER NOT NULL,
            country_id INTEGER NOT NULL,
            region TEXT,
            region_id INTEGER,
            is_type_locality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
            UNIQUE(genus_id, country_id, region)
        );

        CREATE VIEW taxa AS
        SELECT * FROM taxonomic_ranks WHERE rank = 'Genus';

        -- Taxonomic Opinions (B-1)
        CREATE TABLE taxonomic_opinions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            taxon_id            INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
            opinion_type        TEXT NOT NULL
                                CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF')),
            related_taxon_id    INTEGER REFERENCES taxonomic_ranks(id),
            proposed_valid      INTEGER,
            bibliography_id     INTEGER REFERENCES bibliography(id),
            assertion_status    TEXT DEFAULT 'asserted'
                                CHECK(assertion_status IN (
                                    'asserted', 'incertae_sedis', 'questionable', 'indet'
                                )),
            curation_confidence TEXT DEFAULT 'high'
                                CHECK(curation_confidence IN ('high', 'medium', 'low')),
            is_accepted         INTEGER DEFAULT 0,
            notes               TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
        CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);
        CREATE UNIQUE INDEX idx_unique_accepted_opinion
            ON taxonomic_opinions(taxon_id, opinion_type)
            WHERE is_accepted = 1;

        -- BEFORE INSERT: deactivate existing accepted (before unique index check)
        CREATE TRIGGER trg_deactivate_before_insert
        BEFORE INSERT ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
        BEGIN
            UPDATE taxonomic_opinions
            SET is_accepted = 0
            WHERE taxon_id = NEW.taxon_id
              AND opinion_type = 'PLACED_IN'
              AND is_accepted = 1;
        END;

        -- AFTER INSERT: sync parent_id
        CREATE TRIGGER trg_sync_parent_insert
        AFTER INSERT ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
        BEGIN
            UPDATE taxonomic_ranks
            SET parent_id = NEW.related_taxon_id
            WHERE id = NEW.taxon_id;
        END;

        -- BEFORE UPDATE: deactivate other accepted (before unique index check)
        CREATE TRIGGER trg_deactivate_before_update
        BEFORE UPDATE OF is_accepted ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
        BEGIN
            UPDATE taxonomic_opinions
            SET is_accepted = 0
            WHERE taxon_id = NEW.taxon_id
              AND opinion_type = 'PLACED_IN'
              AND is_accepted = 1
              AND id != NEW.id;
        END;

        -- AFTER UPDATE: sync parent_id
        CREATE TRIGGER trg_sync_parent_update
        AFTER UPDATE OF is_accepted ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
        BEGIN
            UPDATE taxonomic_ranks
            SET parent_id = NEW.related_taxon_id
            WHERE id = NEW.taxon_id;
        END;

        -- SCODA-Core tables
        CREATE TABLE artifact_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE provenance (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            url TEXT
        );

        CREATE TABLE schema_descriptions (
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );

        -- SCODA UI tables (Phase 14)
        CREATE TABLE ui_display_intent (
            id INTEGER PRIMARY KEY,
            entity TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description TEXT,
            source_query TEXT,
            priority INTEGER DEFAULT 0
        );

        CREATE TABLE ui_queries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT,
            created_at TEXT NOT NULL
        );
    """)

    # Insert sample data: Class -> Order -> Family -> Genus hierarchy
    cursor.executescript("""
        -- Class
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Trilobita', 'Class', NULL, 'WALCH, 1771', 5113, 'scoda:taxon:class:Trilobita', 'name', 'high');

        -- Orders
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Phacopida', 'Order', 1, 'SALTER, 1864', 500, 'scoda:taxon:order:Phacopida', 'name', 'high');

        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count, uid, uid_method, uid_confidence)
        VALUES (3, 'Ptychopariida', 'Order', 1, 'SWINNERTON, 1915', 1200, 'scoda:taxon:order:Ptychopariida', 'name', 'high');

        -- Family under Phacopida
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count, uid, uid_method, uid_confidence)
        VALUES (10, 'Phacopidae', 'Family', 2, 'HAWLE & CORDA, 1847', 30, 'scoda:taxon:family:Phacopidae', 'name', 'high');

        -- Family under Ptychopariida
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count, uid, uid_method, uid_confidence)
        VALUES (11, 'Olenidae', 'Family', 3, 'BURMEISTER, 1843', 50, 'scoda:taxon:family:Olenidae', 'name', 'high');

        -- Genera under Phacopidae
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family,
            uid, uid_method, uid_confidence)
        VALUES (100, 'Phacops', 'Genus', 10, 'EMMRICH', '1839', NULL,
            'Calymene macrophthalma BRONGNIART, 1822', 'Various', 'Worldwide',
            'LDEV-UDEV', 1, 'Phacops EMMRICH, 1839. ...', 'Phacopidae',
            'scoda:taxon:genus:Phacops', 'name', 'high');

        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family,
            uid, uid_method, uid_confidence)
        VALUES (101, 'Acuticryphops', 'Genus', 10, 'RICHTER & RICHTER', '1926', NULL,
            'Phacops acuticeps KAYSER, 1889', 'Büdesheimer Sh', 'Germany',
            'UDEV', 1, 'Acuticryphops RICHTER & RICHTER, 1926. ...', 'Phacopidae',
            'scoda:taxon:genus:Acuticryphops', 'name', 'high');

        -- An invalid genus (synonym)
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family,
            uid, uid_method, uid_confidence)
        VALUES (102, 'Cryphops', 'Genus', 10, 'RICHTER', '1856', NULL,
            NULL, NULL, 'Germany', 'UDEV', 0,
            'Cryphops RICHTER, 1856 [j.s.s. of Acuticryphops]', 'Phacopidae',
            'scoda:taxon:genus:Cryphops', 'name', 'high');

        -- Genus under Olenidae
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family,
            uid, uid_method, uid_confidence)
        VALUES (200, 'Olenus', 'Genus', 11, 'DALMAN', '1827', NULL,
            'Entomostracites gibbosus WAHLENBERG, 1818', 'Alum Sh', 'Sweden',
            'UCAM', 1, 'Olenus DALMAN, 1827. ...', 'Olenidae',
            'scoda:taxon:genus:Olenus', 'name', 'high');
    """)

    # Synonyms
    cursor.execute("""
        INSERT INTO synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
            synonym_type, fide_author, fide_year)
        VALUES (1, 102, 'Acuticryphops', 101, 'j.s.s.', 'CLARKSON', '1969')
    """)

    # Genus-Formation relations
    cursor.executescript("""
        INSERT INTO genus_formations (genus_id, formation_id) VALUES (101, 1);
        INSERT INTO genus_formations (genus_id, formation_id) VALUES (200, 2);
    """)

    # Genus-Location relations (with region_id)
    cursor.executescript("""
        INSERT INTO genus_locations (genus_id, country_id, region, region_id) VALUES (101, 1, 'Eifel', 3);
        INSERT INTO genus_locations (genus_id, country_id, region, region_id) VALUES (200, 2, 'Scania', 4);
    """)

    # Taxonomic opinions test data
    cursor.executescript("""
        -- Accepted: Phacopida placed in Trilobita (current)
        INSERT INTO taxonomic_opinions (id, taxon_id, opinion_type, related_taxon_id, bibliography_id,
            assertion_status, curation_confidence, is_accepted)
        VALUES (1, 2, 'PLACED_IN', 1, NULL, 'asserted', 'high', 1);

        -- Alternative: Phacopida placed in Ptychopariida (hypothetical)
        INSERT INTO taxonomic_opinions (id, taxon_id, opinion_type, related_taxon_id, bibliography_id,
            assertion_status, curation_confidence, is_accepted, notes)
        VALUES (2, 2, 'PLACED_IN', 3, NULL, 'asserted', 'medium', 0, 'Hypothetical alternative for testing');
    """)

    # Bibliography (for metadata statistics)
    cursor.execute("""
        CREATE TABLE bibliography (
            id INTEGER PRIMARY KEY,
            authors TEXT NOT NULL,
            year INTEGER,
            year_suffix TEXT,
            title TEXT,
            journal TEXT,
            volume TEXT,
            pages TEXT,
            publisher TEXT,
            city TEXT,
            editors TEXT,
            book_title TEXT,
            reference_type TEXT DEFAULT 'article',
            raw_entry TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX idx_bibliography_uid ON bibliography(uid)
    """)
    cursor.execute("""
        INSERT INTO bibliography (id, authors, year, title, journal, volume, pages, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (1, 'Jell, P.A. & Adrain, J.M.', 2002, 'Available generic names for trilobites',
                'Memoirs of the Queensland Museum', '48', '331-553', 'article',
                'Jell, P.A. & Adrain, J.M. (2002) Available generic names for trilobites.',
                'scoda:bib:fp_v1:sha256:test_jell_2002', 'fp_v1', 'medium')
    """)
    cursor.execute("""
        INSERT INTO bibliography (id, authors, year, title, journal, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (2, 'CHIEN see QIAN.', NULL, NULL, NULL, 'cross_ref',
                'CHIEN see QIAN.',
                'scoda:bib:fp_v1:sha256:test_chien_crossref', 'fp_v1', 'low')
    """)
    cursor.execute("""
        INSERT INTO bibliography (id, authors, year, title, journal, volume, pages, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (3, 'Lieberman, B.S.', 1994, 'Evolution of the trilobite subfamily Proetinae',
                'Bulletin of the AMNH', '223', '1-56', 'article',
                'Lieberman, B.S. (1994) Evolution of the trilobite subfamily Proetinae.',
                'scoda:bib:doi:10.1234/test-lieberman-1994', 'doi', 'high')
    """)

    # SCODA metadata
    cursor.executescript("""
        INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'trilobase');
        INSERT INTO artifact_metadata (key, value) VALUES ('name', 'Trilobase');
        INSERT INTO artifact_metadata (key, value) VALUES ('version', '1.0.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('schema_version', '1.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Trilobite genus-level taxonomy database');
        INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');
    """)

    # SCODA provenance
    cursor.executescript("""
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (1, 'primary', 'Jell & Adrain (2002)', 'Primary source for genus-level taxonomy', 2002);
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (2, 'supplementary', 'Adrain (2011)', 'Suprafamilial classification', 2011);
    """)

    # SCODA schema descriptions (sample)
    cursor.executescript("""
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('taxonomic_ranks', NULL, 'Unified taxonomic hierarchy from Class to Genus');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('taxonomic_ranks', 'rank', 'Taxonomic rank: Class, Order, Suborder, Superfamily, Family, or Genus');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('synonyms', NULL, 'Taxonomic synonym relationships');
    """)

    # SCODA display intents (Phase 14)
    cursor.executescript("""
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (1, 'genera', 'tree', 'Taxonomic hierarchy is primary structure', 'taxonomy_tree', 0);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (2, 'genera', 'table', 'Flat listing for search/filtering', 'genera_list', 1);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (3, 'references', 'table', 'Literature references sorted by year', 'bibliography_list', 0);
    """)

    # SCODA saved queries (Phase 14)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genera_list', 'Flat list of all genera',
                'SELECT id, name, author, year, family, is_valid FROM taxonomic_ranks WHERE rank = ''Genus'' ORDER BY name',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('family_genera', 'Genera in a specific family',
                'SELECT id, name, author, year, is_valid FROM taxonomic_ranks WHERE parent_id = :family_id AND rank = ''Genus'' ORDER BY name',
                '{"family_id": "integer"}', '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('taxonomy_tree', 'Tree from Class to Family',
                'SELECT id, name, rank, parent_id, author FROM taxonomic_ranks WHERE rank != ''Genus'' ORDER BY name',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('bibliography_list', 'All literature references',
                'SELECT id, authors, year, title, journal, reference_type FROM bibliography ORDER BY authors',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_detail', 'Full detail for a single genus',
                'SELECT tr.*, parent.name as family_name FROM taxonomic_ranks tr LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id WHERE tr.id = :genus_id AND tr.rank = ''Genus''',
                '{"genus_id": "integer"}', '2026-02-07T00:00:00')
    """)

    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('countries_list', 'All countries with taxa counts',
                'SELECT c.id, c.name, c.cow_ccode as code, COUNT(DISTINCT gl.genus_id) as taxa_count FROM pc.geographic_regions c LEFT JOIN genus_locations gl ON gl.country_id = c.id WHERE c.parent_id IS NULL GROUP BY c.id ORDER BY c.name',
                NULL, '2026-02-12T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('formations_list', 'All formations with taxa counts',
                'SELECT f.id, f.name, f.formation_type, f.period, COUNT(DISTINCT gf.genus_id) as taxa_count FROM pc.formations f LEFT JOIN genus_formations gf ON gf.formation_id = f.id GROUP BY f.id ORDER BY f.name',
                NULL, '2026-02-12T00:00:00')
    """)

    # ICS chronostrat list query (uses pc.* prefix for PaleoCore table)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('ics_chronostrat_list', 'ICS International Chronostratigraphic Chart',
                'SELECT id, name, rank, parent_id, start_mya, end_mya, color, display_order FROM pc.ics_chronostrat ORDER BY display_order',
                NULL, '2026-02-12T00:00:00')
    """)

    # --- Queries needed for composite detail endpoint (Phase 46) ---

    # Existing production queries added to test fixture
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('rank_detail', 'Detail for any taxonomic rank with parent info',
                'SELECT tr.*, parent.name as parent_name, parent.rank as parent_rank FROM taxonomic_ranks tr LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id WHERE tr.id = :rank_id',
                '{"rank_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_synonyms', 'Synonyms for a specific genus',
                'SELECT s.id, s.senior_taxon_id, COALESCE(senior.name, s.senior_taxon_name) as senior_name, s.synonym_type, s.fide_author, s.fide_year FROM synonyms s LEFT JOIN taxonomic_ranks senior ON s.senior_taxon_id = senior.id WHERE s.junior_taxon_id = :genus_id',
                '{"genus_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_formations', 'Formations where a genus was found',
                'SELECT f.id, f.name, f.formation_type as type, f.country, f.period FROM genus_formations gf JOIN pc.formations f ON gf.formation_id = f.id WHERE gf.genus_id = :genus_id',
                '{"genus_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_locations', 'Countries/regions where a genus was found',
                'SELECT CASE WHEN gr.level = ''region'' THEN gr.id END as region_id, CASE WHEN gr.level = ''region'' THEN gr.name END as region_name, CASE WHEN gr.level = ''country'' THEN gr.id ELSE parent.id END as country_id, CASE WHEN gr.level = ''country'' THEN gr.name ELSE parent.name END as country_name FROM genus_locations gl JOIN pc.geographic_regions gr ON gl.region_id = gr.id LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id WHERE gl.genus_id = :genus_id',
                '{"genus_id": "integer"}', '2026-02-14T00:00:00')
    """)

    # New composite detail queries (Phase 46)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_hierarchy', 'Taxonomy hierarchy for a genus (walk up parent chain)',
                'WITH RECURSIVE ancestors AS (SELECT tr.id, tr.name, tr.rank, tr.author, tr.parent_id, 0 as depth FROM taxonomic_ranks tr WHERE tr.id = (SELECT parent_id FROM taxonomic_ranks WHERE id = :genus_id) UNION ALL SELECT tr.id, tr.name, tr.rank, tr.author, tr.parent_id, a.depth + 1 FROM taxonomic_ranks tr JOIN ancestors a ON tr.id = a.parent_id) SELECT id, name, rank, author FROM ancestors ORDER BY depth DESC',
                '{"genus_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_ics_mapping', 'ICS chronostrat mapping for a temporal code',
                'SELECT ic.id, ic.name, ic.rank, m.mapping_type FROM pc.temporal_ics_mapping m JOIN pc.ics_chronostrat ic ON m.ics_id = ic.id WHERE m.temporal_code = :temporal_code',
                '{"temporal_code": "string"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('rank_children', 'Direct children of a taxonomic rank',
                'SELECT id, name, rank, author, genera_count FROM taxonomic_ranks WHERE parent_id = :rank_id ORDER BY rank, name LIMIT 20',
                '{"rank_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('rank_children_counts', 'Children counts by rank for a taxonomic rank',
                'SELECT rank, COUNT(*) as count FROM taxonomic_ranks WHERE parent_id = :rank_id GROUP BY rank',
                '{"rank_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('country_detail', 'Country basic information with taxa count',
                'SELECT gr.id, gr.name, gr.cow_ccode, (SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl WHERE gl.country_id = gr.id OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = gr.id)) as taxa_count FROM pc.geographic_regions gr WHERE gr.id = :country_id AND gr.parent_id IS NULL',
                '{"country_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('country_regions', 'Child regions of a country',
                'SELECT gr.id, gr.name, COUNT(DISTINCT gl.genus_id) as taxa_count FROM pc.geographic_regions gr LEFT JOIN genus_locations gl ON gl.region_id = gr.id WHERE gr.parent_id = :country_id AND gr.level = ''region'' GROUP BY gr.id ORDER BY taxa_count DESC, gr.name',
                '{"country_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('country_genera', 'Genera found in a country',
                'SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid, gr.name as region, gr.id as region_id FROM genus_locations gl JOIN taxonomic_ranks tr ON gl.genus_id = tr.id JOIN pc.geographic_regions gr ON gl.region_id = gr.id WHERE gl.region_id = :country_id OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = :country_id) ORDER BY tr.name',
                '{"country_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('region_detail', 'Region basic information with parent and taxa count',
                'SELECT gr.id, gr.name, gr.level, COUNT(DISTINCT gl.genus_id) as taxa_count, parent.id as country_id, parent.name as country_name FROM pc.geographic_regions gr LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id LEFT JOIN genus_locations gl ON gl.region_id = gr.id WHERE gr.id = :region_id AND gr.level = ''region'' GROUP BY gr.id',
                '{"region_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('region_genera', 'Genera found in a specific region',
                'SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid FROM genus_locations gl JOIN taxonomic_ranks tr ON gl.genus_id = tr.id WHERE gl.region_id = :region_id ORDER BY tr.name',
                '{"region_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('formation_detail', 'Formation basic information with taxa count',
                'SELECT f.id, f.name, f.normalized_name, f.formation_type, f.country, f.region, f.period, gr.id as country_id, tr.code as temporal_code, COUNT(DISTINCT gf.genus_id) as taxa_count FROM pc.formations f LEFT JOIN genus_formations gf ON gf.formation_id = f.id LEFT JOIN pc.geographic_regions gr ON f.country = gr.name AND gr.level = ''country'' LEFT JOIN pc.temporal_ranges tr ON f.period = tr.name WHERE f.id = :formation_id GROUP BY f.id',
                '{"formation_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('formation_genera', 'Genera found in a specific formation',
                'SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid FROM genus_formations gf JOIN taxonomic_ranks tr ON gf.genus_id = tr.id WHERE gf.formation_id = :formation_id ORDER BY tr.name',
                '{"formation_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('bibliography_detail', 'Bibliography entry detail',
                'SELECT id, authors, year, year_suffix, title, journal, volume, pages, publisher, city, editors, book_title, reference_type, raw_entry FROM bibliography WHERE id = :bibliography_id',
                '{"bibliography_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('bibliography_genera', 'Genera related to a bibliography entry by author name',
                'SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid FROM taxonomic_ranks tr WHERE tr.rank = ''Genus'' AND tr.author LIKE ''%%'' || :author_name || ''%%'' ORDER BY tr.name',
                '{"author_name": "string"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('chronostrat_detail', 'ICS chronostratigraphic unit detail with parent',
                'SELECT ics.id, ics.name, ics.rank, ics.parent_id, ics.start_mya, ics.start_uncertainty, ics.end_mya, ics.end_uncertainty, ics.short_code, ics.color, ics.ratified_gssp, p.id as parent_detail_id, p.name as parent_name, p.rank as parent_rank FROM pc.ics_chronostrat ics LEFT JOIN pc.ics_chronostrat p ON ics.parent_id = p.id WHERE ics.id = :chronostrat_id',
                '{"chronostrat_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('chronostrat_children', 'Children of an ICS chronostratigraphic unit',
                'SELECT id, name, rank, start_mya, end_mya, color FROM pc.ics_chronostrat WHERE parent_id = :chronostrat_id ORDER BY display_order',
                '{"chronostrat_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('chronostrat_mappings', 'Temporal code mappings for an ICS unit',
                'SELECT temporal_code, mapping_type FROM pc.temporal_ics_mapping WHERE ics_id = :chronostrat_id ORDER BY temporal_code',
                '{"chronostrat_id": "integer"}', '2026-02-14T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('chronostrat_genera', 'Genera related to an ICS chronostratigraphic unit',
                'SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid, tr.temporal_code FROM pc.temporal_ics_mapping m JOIN taxonomic_ranks tr ON tr.temporal_code = m.temporal_code WHERE m.ics_id = :chronostrat_id AND tr.rank = ''Genus'' ORDER BY tr.name',
                '{"chronostrat_id": "integer"}', '2026-02-14T00:00:00')
    """)

    # Taxon opinions query (B-1)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('taxon_opinions', 'Taxonomic opinions for a specific taxon',
                'SELECT o.id, o.opinion_type, o.related_taxon_id, t.name as related_taxon_name, t.rank as related_taxon_rank, o.bibliography_id, b.authors as bib_authors, b.year as bib_year, o.assertion_status, o.curation_confidence, o.is_accepted, o.notes, o.created_at FROM taxonomic_opinions o LEFT JOIN taxonomic_ranks t ON o.related_taxon_id = t.id LEFT JOIN bibliography b ON o.bibliography_id = b.id WHERE o.taxon_id = :taxon_id ORDER BY o.is_accepted DESC, o.created_at',
                '{"taxon_id": "integer"}', '2026-02-18T00:00:00')
    """)

    # SCODA UI Manifest (Phase 15)
    cursor.execute("""
        CREATE TABLE ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    import json as _json
    test_manifest = {
        "default_view": "taxonomy_tree",
        "views": {
            "taxonomy_tree": {
                "type": "hierarchy",
                "display": "tree",
                "title": "Taxonomy Tree",
                "description": "Hierarchical classification from Class to Family",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "rank",
                    "sort_by": "label",
                    "order_key": "id",
                    "skip_ranks": []
                },
                "tree_display": {
                    "leaf_rank": "Family",
                    "count_key": "genera_count",
                    "on_node_info": {"detail_view": "rank_detail", "id_key": "id"},
                    "item_query": "family_genera",
                    "item_param": "family_id",
                    "item_columns": [
                        {"key": "name", "label": "Genus", "italic": True},
                        {"key": "author", "label": "Author"},
                        {"key": "year", "label": "Year"},
                        {"key": "type_species", "label": "Type Species", "truncate": 40},
                        {"key": "location", "label": "Location", "truncate": 30}
                    ],
                    "on_item_click": {"detail_view": "genus_detail", "id_key": "id"},
                    "item_valid_filter": {"key": "is_valid", "label": "Valid only", "default": True}
                }
            },
            "genera_table": {
                "type": "table",
                "title": "All Genera",
                "description": "Flat list of all trilobite genera",
                "source_query": "genera_list",
                "icon": "bi-table",
                "columns": [
                    {"key": "name", "label": "Genus", "sortable": True, "searchable": True, "italic": True},
                    {"key": "author", "label": "Author", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "family", "label": "Family", "sortable": True, "searchable": True},
                    {"key": "is_valid", "label": "Valid", "sortable": True, "searchable": False, "type": "boolean"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
            },
            "references_table": {
                "type": "table",
                "title": "Bibliography",
                "description": "Literature references",
                "source_query": "bibliography_list",
                "icon": "bi-book",
                "columns": [
                    {"key": "authors", "label": "Authors", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "title", "label": "Title", "sortable": False, "searchable": True}
                ],
                "default_sort": {"key": "authors", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "bibliography_detail", "id_key": "id"}
            },
            "formations_table": {
                "type": "table",
                "title": "Formations",
                "description": "Geological formations",
                "source_query": "formations_list",
                "icon": "bi-layers",
                "columns": [
                    {"key": "name", "label": "Formation", "sortable": True, "searchable": True}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "formation_detail", "id_key": "id"}
            },
            "countries_table": {
                "type": "table",
                "title": "Countries",
                "description": "Countries with trilobite occurrences",
                "source_query": "countries_list",
                "icon": "bi-globe",
                "columns": [
                    {"key": "name", "label": "Country", "sortable": True, "searchable": True}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "country_detail", "id_key": "id"}
            },
            "chronostratigraphy_table": {
                "type": "hierarchy",
                "display": "nested_table",
                "title": "Chronostratigraphy",
                "description": "ICS International Chronostratigraphic Chart (GTS 2020)",
                "source_query": "ics_chronostrat_list",
                "icon": "bi-clock-history",
                "columns": [
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "rank", "label": "Rank", "sortable": True, "searchable": True},
                    {"key": "start_mya", "label": "Start (Ma)", "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)", "sortable": True, "type": "number"},
                    {"key": "color", "label": "Color", "sortable": False, "type": "color"}
                ],
                "default_sort": {"key": "display_order", "direction": "asc"},
                "searchable": True,
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "rank",
                    "sort_by": "order_key",
                    "order_key": "display_order",
                    "skip_ranks": ["Super-Eon"]
                },
                "nested_table_display": {
                    "color_key": "color",
                    "rank_columns": [
                        {"rank": "Eon", "label": "Eon"},
                        {"rank": "Era", "label": "Era"},
                        {"rank": "Period", "label": "System / Period"},
                        {"rank": "Sub-Period", "label": "Sub-Period"},
                        {"rank": "Epoch", "label": "Series / Epoch"},
                        {"rank": "Age", "label": "Stage / Age"}
                    ],
                    "value_column": {"key": "start_mya", "label": "Age (Ma)"},
                    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
                }
            },
            "formation_detail": {
                "type": "detail",
                "title": "Formation Detail",
                "source": "/api/composite/formation_detail?id={id}",
                "source_query": "formation_detail",
                "source_param": "formation_id",
                "sub_queries": {
                    "genera": {"query": "formation_genera", "params": {"formation_id": "id"}},
                    "temporal_ics_mapping": {"query": "genus_ics_mapping", "params": {"temporal_code": "result.temporal_code"}}
                },
                "icon": "bi-layers",
                "title_template": {"format": "{icon} {name}", "icon": "bi-layers"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [
                         {"key": "name", "label": "Name"},
                         {"key": "formation_type", "label": "Type"},
                         {"key": "country", "label": "Country", "format": "link",
                          "link": {"detail_view": "country_detail", "id_path": "country_id"}},
                         {"key": "region", "label": "Region"},
                         {"key": "period", "label": "Period", "format": "temporal_range"},
                         {"key": "taxa_count", "label": "Taxa Count"}
                     ]},
                    {"title": "Genera ({count})", "type": "linked_table",
                     "data_key": "genera",
                     "columns": [{"key": "name", "label": "Genus", "italic": True}],
                     "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}}
                ]
            },
            "country_detail": {
                "type": "detail",
                "title": "Country Detail",
                "source": "/api/composite/country_detail?id={id}",
                "source_query": "country_detail",
                "source_param": "country_id",
                "sub_queries": {
                    "regions": {"query": "country_regions", "params": {"country_id": "id"}},
                    "genera": {"query": "country_genera", "params": {"country_id": "id"}}
                },
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [{"key": "name", "label": "Name"}]}
                ]
            },
            "region_detail": {
                "type": "detail",
                "title": "Region Detail",
                "source": "/api/composite/region_detail?id={id}",
                "source_query": "region_detail",
                "source_param": "region_id",
                "sub_queries": {
                    "genera": {"query": "region_genera", "params": {"region_id": "id"}}
                },
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [{"key": "name", "label": "Name"}]}
                ]
            },
            "bibliography_detail": {
                "type": "detail",
                "title": "Bibliography Detail",
                "source": "/api/composite/bibliography_detail?id={id}",
                "source_query": "bibliography_detail",
                "source_param": "bibliography_id",
                "sub_queries": {
                    "genera": {"query": "bibliography_genera", "params": {"author_name": "result.authors"}}
                },
                "icon": "bi-book",
                "title_template": {"format": "{icon} {authors}, {year}", "icon": "bi-book"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [{"key": "authors", "label": "Authors"}]},
                    {"title": "Original Entry", "type": "raw_text",
                     "data_key": "raw_entry", "condition": "raw_entry"}
                ]
            },
            "chronostrat_detail": {
                "type": "detail",
                "title": "Chronostratigraphy Detail",
                "source": "/api/composite/chronostrat_detail?id={id}",
                "source_query": "chronostrat_detail",
                "source_param": "chronostrat_id",
                "sub_queries": {
                    "children": {"query": "chronostrat_children", "params": {"chronostrat_id": "id"}},
                    "mappings": {"query": "chronostrat_mappings", "params": {"chronostrat_id": "id"}},
                    "genera": {"query": "chronostrat_genera", "params": {"chronostrat_id": "id"}}
                },
                "icon": "bi-clock-history",
                "title_template": {"format": "{icon} {name}", "icon": "bi-clock-history"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [{"key": "name", "label": "Name"}]}
                ]
            },
            "genus_detail": {
                "type": "detail",
                "title": "Genus Detail",
                "source": "/api/composite/genus_detail?id={id}",
                "source_query": "genus_detail",
                "source_param": "genus_id",
                "sub_queries": {
                    "hierarchy": {"query": "genus_hierarchy", "params": {"genus_id": "id"}},
                    "synonyms": {"query": "genus_synonyms", "params": {"genus_id": "id"}},
                    "formations": {"query": "genus_formations", "params": {"genus_id": "id"}},
                    "locations": {"query": "genus_locations", "params": {"genus_id": "id"}},
                    "temporal_ics_mapping": {"query": "genus_ics_mapping", "params": {"temporal_code": "result.temporal_code"}}
                },
                "title_template": {"format": "<i>{name}</i> {author}, {year}"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [
                         {"key": "name", "label": "Name", "format": "italic"},
                         {"key": "hierarchy", "label": "Classification", "format": "hierarchy"},
                         {"key": "temporal_code", "label": "Temporal Range", "format": "temporal_range"}
                     ]},
                    {"title": "Type Species", "type": "field_grid", "condition": "type_species",
                     "fields": [{"key": "type_species", "label": "Species", "format": "italic"}]},
                    {"title": "Geographic Information", "type": "genus_geography"},
                    {"title": "Synonymy", "type": "synonym_list", "data_key": "synonyms", "condition": "synonyms"},
                    {"title": "Original Entry", "type": "raw_text", "data_key": "raw_entry", "condition": "raw_entry"},
                    {"title": "My Notes", "type": "annotations", "entity_type": "genus"}
                ]
            },
            "rank_detail": {
                "type": "detail",
                "title": "Rank Detail",
                "source": "/api/composite/rank_detail?id={id}",
                "source_query": "rank_detail",
                "source_param": "rank_id",
                "sub_queries": {
                    "children_counts": {"query": "rank_children_counts", "params": {"rank_id": "id"}},
                    "children": {"query": "rank_children", "params": {"rank_id": "id"}},
                    "opinions": {"query": "taxon_opinions", "params": {"taxon_id": "id"}}
                },
                "title_template": {"format": "<span class=\"badge bg-secondary me-2\">{rank}</span> {name}"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [
                         {"key": "name", "label": "Name"},
                         {"key": "rank", "label": "Rank"},
                         {"key": "parent_name", "label": "Parent",
                          "format": "link",
                          "link": {"detail_view": "rank_detail", "id_path": "parent_id"},
                          "suffix_key": "parent_rank", "suffix_format": "({value})"}
                     ]},
                    {"title": "Statistics", "type": "rank_statistics"},
                    {"title": "Children", "type": "rank_children", "data_key": "children", "condition": "children"},
                    {"title": "Taxonomic Opinions ({count})", "type": "linked_table",
                     "data_key": "opinions", "condition": "opinions",
                     "columns": [
                         {"key": "related_taxon_name", "label": "Proposed Parent"},
                         {"key": "related_taxon_rank", "label": "Rank"},
                         {"key": "bib_authors", "label": "Author"},
                         {"key": "bib_year", "label": "Year"},
                         {"key": "assertion_status", "label": "Status"},
                         {"key": "is_accepted", "label": "Accepted", "format": "boolean"}
                     ],
                     "on_row_click": {"detail_view": "rank_detail", "id_key": "related_taxon_id"}},
                    {"title": "My Notes", "type": "annotations", "entity_type_from": "rank"}
                ]
            }
        }
    }
    cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'Test manifest', _json.dumps(test_manifest), '2026-02-07T00:00:00')
    )

    conn.commit()
    conn.close()

    # Create PALEOCORE database (PaleoCore tables accessed via pc.* prefix)
    paleocore_db_path = str(tmp_path / "test_paleocore.db")
    pc_conn = sqlite3.connect(paleocore_db_path)
    pc_cursor = pc_conn.cursor()

    pc_cursor.executescript("""
        CREATE TABLE countries (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            code TEXT,
            taxa_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_countries_uid ON countries(uid);

        CREATE TABLE geographic_regions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            cow_ccode INTEGER,
            taxa_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
        );
        CREATE UNIQUE INDEX idx_geographic_regions_uid ON geographic_regions(uid);

        CREATE TABLE formations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            normalized_name TEXT,
            formation_type TEXT,
            country TEXT,
            region TEXT,
            period TEXT,
            taxa_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_formations_uid ON formations(uid);

        CREATE TABLE temporal_ranges (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT,
            period TEXT,
            epoch TEXT,
            start_mya REAL,
            end_mya REAL,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_temporal_ranges_uid ON temporal_ranges(uid);

        CREATE TABLE ics_chronostrat (
            id INTEGER PRIMARY KEY,
            ics_uri TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            rank TEXT NOT NULL,
            parent_id INTEGER,
            start_mya REAL,
            start_uncertainty REAL,
            end_mya REAL,
            end_uncertainty REAL,
            short_code TEXT,
            color TEXT,
            display_order INTEGER,
            ratified_gssp INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
        );
        CREATE UNIQUE INDEX idx_ics_chronostrat_uid ON ics_chronostrat(uid);
        CREATE INDEX idx_pc_ics_chrono_parent ON ics_chronostrat(parent_id);
        CREATE INDEX idx_pc_ics_chrono_rank ON ics_chronostrat(rank);

        CREATE TABLE temporal_ics_mapping (
            id INTEGER PRIMARY KEY,
            temporal_code TEXT NOT NULL,
            ics_id INTEGER NOT NULL,
            mapping_type TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
        );
        CREATE INDEX idx_pc_tim_code ON temporal_ics_mapping(temporal_code);
        CREATE INDEX idx_pc_tim_ics ON temporal_ics_mapping(ics_id);
    """)

    # Populate PaleoCore tables with same data as canonical
    pc_cursor.executescript("""
        INSERT INTO countries (id, name, code, taxa_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Germany', 'DE', 150, 'scoda:geo:country:iso3166-1:DE', 'iso3166-1', 'high');
        INSERT INTO countries (id, name, code, taxa_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Sweden', 'SE', 80, 'scoda:geo:country:iso3166-1:SE', 'iso3166-1', 'high');

        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Germany', 'country', NULL, 255, 150, 'scoda:geo:country:iso3166-1:DE', 'iso3166-1', 'high');
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Sweden', 'country', NULL, 380, 80, 'scoda:geo:country:iso3166-1:SE', 'iso3166-1', 'high');
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count, uid, uid_method, uid_confidence)
        VALUES (3, 'Eifel', 'region', 1, NULL, 5, 'scoda:geo:region:name:DE:eifel', 'name', 'high');
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count, uid, uid_method, uid_confidence)
        VALUES (4, 'Scania', 'region', 2, NULL, 20, 'scoda:geo:region:name:SE:scania', 'name', 'high');

        INSERT INTO temporal_ranges (id, code, name, period, epoch, start_mya, end_mya, uid, uid_method, uid_confidence)
        VALUES (1, 'UCAM', 'Upper Cambrian', 'Cambrian', 'Upper', 497.0, 486.85, 'scoda:strat:temporal:code:UCAM', 'code', 'high');
        INSERT INTO temporal_ranges (id, code, name, period, epoch, start_mya, end_mya, uid, uid_method, uid_confidence)
        VALUES (2, 'LDEV', 'Lower Devonian', 'Devonian', 'Lower', 419.2, 393.3, 'scoda:strat:temporal:code:LDEV', 'code', 'high');
        INSERT INTO temporal_ranges (id, code, name, period, epoch, start_mya, end_mya, uid, uid_method, uid_confidence)
        VALUES (3, 'DEV', 'Devonian', 'Devonian', NULL, 419.2, 358.9, 'scoda:strat:temporal:code:DEV', 'code', 'high');
        INSERT INTO temporal_ranges (id, code, name, period, epoch, start_mya, end_mya, uid, uid_method, uid_confidence)
        VALUES (4, 'CAM', 'Cambrian', 'Cambrian', NULL, 538.8, 486.85, 'scoda:strat:temporal:code:CAM', 'code', 'high');

        INSERT INTO formations (id, name, normalized_name, formation_type, country, period, taxa_count,
            uid, uid_method, uid_confidence)
        VALUES (1, 'Büdesheimer Sh', 'budesheimer sh', 'Sh', 'Germany', 'Devonian', 5,
            'scoda:strat:formation:fp_v1:sha256:test_budesheimer', 'fp_v1', 'medium');
        INSERT INTO formations (id, name, normalized_name, formation_type, country, period, taxa_count,
            uid, uid_method, uid_confidence)
        VALUES (2, 'Alum Sh', 'alum sh', 'Sh', 'Sweden', 'Cambrian', 20,
            'scoda:strat:formation:fp_v1:sha256:test_alum', 'fp_v1', 'medium');
        INSERT INTO formations (id, name, normalized_name, formation_type, country, period, taxa_count,
            uid, uid_method, uid_confidence)
        VALUES (3, 'St. Clair Ls', 'st clair ls', 'Ls', 'United States', 'Silurian', 8,
            'scoda:strat:formation:lexicon:macrostrat:12345', 'lexicon', 'high');

        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (1, 'http://resource.geosciml.org/classifier/ics/ischart/Phanerozoic', 'Phanerozoic', 'Eon', NULL, 538.8, 0.6, 0.0, NULL, NULL, '#9AD9DD', 170, 1, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Phanerozoic', 'ics_uri', 'high');
        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (2, 'http://resource.geosciml.org/classifier/ics/ischart/Paleozoic', 'Paleozoic', 'Era', 1, 538.8, 0.6, 251.9, 0.024, NULL, '#99C08D', 169, 1, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Paleozoic', 'ics_uri', 'high');
        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (3, 'http://resource.geosciml.org/classifier/ics/ischart/Cambrian', 'Cambrian', 'Period', 2, 538.8, 0.6, 486.85, 1.5, 'Ep', '#7FA056', 154, 1, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Cambrian', 'ics_uri', 'high');
        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (4, 'http://resource.geosciml.org/classifier/ics/ischart/Miaolingian', 'Miaolingian', 'Epoch', 3, 506.5, NULL, 497.0, NULL, 'Ep3', '#A6CF86', 148, 0, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Miaolingian', 'ics_uri', 'high');
        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (5, 'http://resource.geosciml.org/classifier/ics/ischart/Wuliuan', 'Wuliuan', 'Age', 4, 506.5, NULL, 504.5, NULL, NULL, '#B6D88B', 147, 1, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Wuliuan', 'ics_uri', 'high');
        INSERT INTO ics_chronostrat (id, ics_uri, name, rank, parent_id, start_mya, start_uncertainty, end_mya, end_uncertainty, short_code, color, display_order, ratified_gssp, uid, uid_method, uid_confidence)
        VALUES (6, 'http://resource.geosciml.org/classifier/ics/ischart/Furongian', 'Furongian', 'Epoch', 3, 497.0, NULL, 486.85, 1.5, 'Ep4', '#B3E095', 144, 1, 'scoda:strat:ics:uri:http://resource.geosciml.org/classifier/ics/ischart/Furongian', 'ics_uri', 'high');

        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (1, 'MCAM', 4, 'exact');
        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (2, 'UCAM', 6, 'exact');
        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (3, 'CAM', 3, 'exact');
        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (4, 'MUCAM', 4, 'aggregate');
        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (5, 'MUCAM', 6, 'aggregate');
        INSERT INTO temporal_ics_mapping (id, temporal_code, ics_id, mapping_type) VALUES (6, 'DEV', 2, 'partial');
    """)

    # PaleoCore SCODA metadata (needed by ScodaPackage.create)
    pc_cursor.executescript("""
        CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'paleocore');
        INSERT INTO artifact_metadata (key, value) VALUES ('name', 'PaleoCore');
        INSERT INTO artifact_metadata (key, value) VALUES ('version', '0.3.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Shared paleontological infrastructure');
        INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');

        CREATE TABLE provenance (id INTEGER PRIMARY KEY, source_type TEXT NOT NULL,
            citation TEXT NOT NULL, description TEXT, year INTEGER, url TEXT);
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (1, 'primary', 'COW v2024', 'Correlates of War state system', 2024);

        CREATE TABLE schema_descriptions (table_name TEXT NOT NULL, column_name TEXT,
            description TEXT NOT NULL, PRIMARY KEY (table_name, column_name));

        CREATE TABLE ui_display_intent (id INTEGER PRIMARY KEY, entity TEXT NOT NULL,
            default_view TEXT NOT NULL, description TEXT, source_query TEXT, priority INTEGER DEFAULT 0);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (1, 'countries', 'table', 'Country list', 'countries_list', 0);

        CREATE TABLE ui_queries (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            description TEXT, sql TEXT NOT NULL, params_json TEXT, created_at TEXT NOT NULL);
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('countries_list', 'All countries', 'SELECT id, name FROM countries ORDER BY name', NULL, '2026-02-13T00:00:00');
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('formations_list', 'All formations', 'SELECT id, name FROM formations ORDER BY name', NULL, '2026-02-13T00:00:00');

        CREATE TABLE ui_manifest (name TEXT PRIMARY KEY, description TEXT, manifest_json TEXT NOT NULL, created_at TEXT NOT NULL);
    """)

    import json as _json
    pc_manifest = {
        "default_view": "countries_table",
        "views": {
            "countries_table": {
                "type": "table",
                "title": "Countries",
                "description": "Country data",
                "source_query": "countries_list",
                "icon": "bi-globe",
                "columns": [{"key": "name", "label": "Country", "sortable": True, "searchable": True}],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            }
        }
    }
    pc_cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'PaleoCore manifest', _json.dumps(pc_manifest), '2026-02-13T00:00:00')
    )

    pc_conn.commit()
    pc_conn.close()

    # Create OVERLAY database using init_overlay_db script
    create_overlay_db(overlay_db_path, canonical_version='1.0.0')

    return canonical_db_path, overlay_db_path, paleocore_db_path


@pytest.fixture
def client(test_db):
    """Create test client with test databases (canonical + overlay + dependencies)."""
    from starlette.testclient import TestClient
    canonical_db_path, overlay_db_path, paleocore_db_path = test_db
    scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path, extra_dbs={'pc': paleocore_db_path})
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


@pytest.fixture
def no_manifest_db(tmp_path):
    """Create a minimal DB with data tables but NO ui_manifest/ui_queries/SCODA metadata.

    This simulates opening a plain SQLite database that has no SCODA packaging.
    """
    db_path = str(tmp_path / "plain.db")
    overlay_path = str(tmp_path / "plain_overlay.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            genus TEXT,
            habitat TEXT,
            is_extinct INTEGER DEFAULT 0
        );
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (1, 'Paradoxides davidis', 'Paradoxides', 'Marine', 1);
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (2, 'Phacops rana', 'Phacops', 'Marine', 1);
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (3, 'Elrathia kingii', 'Elrathia', 'Marine', 1);

        CREATE TABLE localities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            latitude REAL,
            longitude REAL
        );
        INSERT INTO localities (id, name, country, latitude, longitude)
        VALUES (1, 'Burgess Shale', 'Canada', 51.4, -116.5);
        INSERT INTO localities (id, name, country, latitude, longitude)
        VALUES (2, 'Wheeler Formation', 'USA', 39.3, -113.3);
    """)

    conn.commit()
    conn.close()

    # Create overlay DB
    create_overlay_db(overlay_path, canonical_version='1.0.0')

    return db_path, overlay_path


@pytest.fixture
def no_manifest_client(no_manifest_db):
    """Create test client with a plain DB that has no manifest."""
    from starlette.testclient import TestClient
    db_path, overlay_path = no_manifest_db
    scoda_package._set_paths_for_testing(db_path, overlay_path)
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


@pytest.fixture
def mcp_tools_data():
    """Return a test mcp_tools.json dict with 3 tools (single, named_query, composite)."""
    return {
        "format_version": "1.0",
        "tools": [
            {
                "name": "test_search",
                "description": "Test single SQL search",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["pattern"]
                },
                "query_type": "single",
                "sql": "SELECT id, name FROM taxonomic_ranks WHERE name LIKE :pattern ORDER BY name LIMIT :limit",
                "default_params": {"limit": 10}
            },
            {
                "name": "test_tree",
                "description": "Test named query tree",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "query_type": "named_query",
                "named_query": "taxonomy_tree"
            },
            {
                "name": "test_genus_detail",
                "description": "Test composite genus detail",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "genus_id": {"type": "integer"}
                    },
                    "required": ["genus_id"]
                },
                "query_type": "composite",
                "view_name": "genus_detail",
                "param_mapping": {"genus_id": "genus_id"}
            }
        ]
    }


@pytest.fixture
def scoda_with_mcp_tools(test_db, mcp_tools_data, tmp_path):
    """Create a .scoda package that includes mcp_tools.json."""
    canonical_db_path, overlay_db_path, paleocore_db_path = test_db

    # Write mcp_tools.json to a temp file
    mcp_tools_path = str(tmp_path / "mcp_tools.json")
    with open(mcp_tools_path, 'w') as f:
        json.dump(mcp_tools_data, f)

    # Create .scoda package
    output_path = str(tmp_path / "test_with_mcp.scoda")
    ScodaPackage.create(
        canonical_db_path,
        output_path,
        mcp_tools_path=mcp_tools_path
    )

    return output_path, canonical_db_path, overlay_db_path, paleocore_db_path

