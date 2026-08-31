from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote
from urllib.parse import urlparse

from .candidate import EvidenceReference, MemoryCandidate
from .scenario_fixture import candidate_from_mapping, load_fixture


SCHEMA_VERSION = "phase2b-sqlite-prototype-v0"


def connect(db_path: Path | str) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS prototype_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_records (
            source_kind TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_event_id TEXT NOT NULL,
            role TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (source_kind, source_id)
        );

        CREATE TABLE IF NOT EXISTS source_files (
            source_file_id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            source_file_id TEXT NOT NULL,
            title TEXT NOT NULL,
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL,
            current_node_id TEXT NOT NULL,
            node_count INTEGER NOT NULL,
            raw_json TEXT NOT NULL,
            FOREIGN KEY (source_file_id) REFERENCES source_files(source_file_id)
        );

        CREATE TABLE IF NOT EXISTS conversation_nodes (
            conversation_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            source_file_id TEXT NOT NULL,
            parent_node_id TEXT NOT NULL,
            child_ids_json TEXT NOT NULL,
            is_current_path INTEGER NOT NULL CHECK(is_current_path IN (0, 1)),
            is_off_path INTEGER NOT NULL CHECK(is_off_path IN (0, 1)),
            current_path_index INTEGER,
            message_id TEXT NOT NULL,
            role TEXT NOT NULL,
            author_name TEXT NOT NULL,
            recipient TEXT NOT NULL,
            status TEXT NOT NULL,
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (conversation_id, node_id),
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
            FOREIGN KEY (source_file_id) REFERENCES source_files(source_file_id)
        );

        CREATE TABLE IF NOT EXISTS conversation_node_edges (
            conversation_id TEXT NOT NULL,
            parent_node_id TEXT NOT NULL,
            child_node_id TEXT NOT NULL,
            PRIMARY KEY (conversation_id, parent_node_id, child_node_id),
            FOREIGN KEY (conversation_id, parent_node_id) REFERENCES conversation_nodes(conversation_id, node_id),
            FOREIGN KEY (conversation_id, child_node_id) REFERENCES conversation_nodes(conversation_id, node_id)
        );

        CREATE TABLE IF NOT EXISTS attachments (
            attachment_record_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            attachment_id TEXT NOT NULL,
            name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            local_path TEXT NOT NULL,
            availability_state TEXT NOT NULL CHECK(availability_state IN ('available', 'missing', 'download_failed')),
            size_bytes INTEGER,
            sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        );

        CREATE TABLE IF NOT EXISTS web_sources (
            web_source_id TEXT PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_provenance TEXT NOT NULL,
            first_accessed_at TEXT NOT NULL,
            last_accessed_at TEXT NOT NULL,
            latest_access_status TEXT NOT NULL,
            latest_content_ref TEXT NOT NULL,
            latest_content_sha256 TEXT NOT NULL,
            latest_content_bytes INTEGER NOT NULL,
            latest_content_chars INTEGER NOT NULL,
            metadata_json TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS web_access_events (
            access_event_id TEXT PRIMARY KEY,
            web_source_id TEXT NOT NULL,
            url TEXT NOT NULL,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            accessed_at TEXT NOT NULL,
            access_status TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_provenance TEXT NOT NULL,
            http_status INTEGER,
            content_ref TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            content_bytes INTEGER NOT NULL,
            content_chars INTEGER NOT NULL,
            excerpt TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            FOREIGN KEY (web_source_id) REFERENCES web_sources(web_source_id)
        );

        CREATE TABLE IF NOT EXISTS evidence_references (
            evidence_id TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_event_id TEXT NOT NULL,
            location TEXT NOT NULL,
            summary TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            source_provenance TEXT NOT NULL,
            scope_summary TEXT NOT NULL,
            scope_json TEXT NOT NULL,
            extraction_confidence REAL NOT NULL,
            candidate_state TEXT NOT NULL CHECK(candidate_state IN ('open', 'deferred', 'closed')),
            evidence_summary TEXT NOT NULL,
            validation_requirements_json TEXT NOT NULL,
            proposed_validity TEXT NOT NULL,
            representation_facet_hint TEXT NOT NULL,
            relation_hint TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS candidate_scope_dimensions (
            candidate_id TEXT NOT NULL,
            dimension_key TEXT NOT NULL,
            dimension_value TEXT NOT NULL,
            PRIMARY KEY (candidate_id, dimension_key),
            FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
        );

        CREATE TABLE IF NOT EXISTS candidate_evidence (
            candidate_id TEXT NOT NULL,
            evidence_id TEXT NOT NULL,
            evidence_order INTEGER NOT NULL,
            PRIMARY KEY (candidate_id, evidence_id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id),
            FOREIGN KEY (evidence_id) REFERENCES evidence_references(evidence_id)
        );

        CREATE TABLE IF NOT EXISTS retrieval_probes (
            query_id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            expected_candidate_ids_json TEXT NOT NULL,
            required_scope_dimensions_json TEXT NOT NULL,
            required_uncertainty TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO prototype_metadata(key, value)
        VALUES('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (SCHEMA_VERSION,),
    )
    _ensure_column(connection, "web_sources", "source_provenance", "TEXT NOT NULL DEFAULT 'external'")
    _ensure_column(connection, "web_access_events", "source_provenance", "TEXT NOT NULL DEFAULT 'external'")
    connection.commit()


def ingest_fixture(connection: sqlite3.Connection, fixture_path: Path | str) -> dict[str, int]:
    fixture = load_fixture(Path(fixture_path))
    initialize(connection)
    for turn in _list_of_dicts(fixture.get("turns")):
        ingest_source_record(connection, turn)
    state_by_candidate_id = _fixture_candidate_states(fixture)
    for candidate_data in _list_of_dicts(fixture.get("expected_candidates")):
        candidate = candidate_from_mapping(candidate_data)
        candidate_state = state_by_candidate_id.get(candidate.candidate_id, candidate.candidate_state)
        insert_candidate(
            connection,
            candidate.with_state(candidate_state),
            raw_mapping=candidate_data,
        )
    for probe in _list_of_dicts(fixture.get("retrieval_probes")):
        insert_retrieval_probe(connection, probe)
    connection.commit()
    return counts(connection)


def ingest_exported_conversation(connection: sqlite3.Connection, export_path: Path | str) -> dict[str, int]:
    records = json.loads(Path(export_path).read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("exported conversation must be a JSON list")
    initialize(connection)
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"exported conversation record {index} must be a mapping")
        ingest_exported_message(connection, record, index=index)
    connection.commit()
    return counts(connection)


def ingest_chatgpt_export_directory(connection: sqlite3.Connection, corpus_dir: Path | str) -> dict[str, int]:
    corpus_dir = Path(corpus_dir)
    attachment_report = _load_attachment_report(corpus_dir)
    initialize(connection)
    for export_path in sorted(corpus_dir.glob("*.json")):
        if export_path.name == "attachment-export-report.json":
            continue
        ingest_chatgpt_export(
            connection,
            export_path,
            corpus_dir=corpus_dir,
            attachment_report=attachment_report,
        )
    connection.commit()
    return counts(connection)


def ingest_chatgpt_export(
    connection: sqlite3.Connection,
    export_path: Path | str,
    *,
    corpus_dir: Path | str | None = None,
    attachment_report: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    export_path = Path(export_path)
    corpus_dir = Path(corpus_dir) if corpus_dir is not None else export_path.parent
    payload = json.loads(export_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError("ChatGPT export must be a JSON object")
    mapping = payload.get("mapping")
    if not isinstance(mapping, Mapping):
        raise ValueError("ChatGPT export mapping missing")
    conversation_id = str(payload.get("conversation_id") or "")
    if not conversation_id:
        raise ValueError("ChatGPT export conversation_id missing")

    initialize(connection)
    source_file_id = insert_source_file(connection, export_path, kind="chatgpt_export_json")
    current_path = _current_path_node_ids(mapping, str(payload.get("current_node") or ""))
    current_path_index = {node_id: index for index, node_id in enumerate(current_path)}
    node_by_message_id: dict[str, str] = {}
    for node_id, node in mapping.items():
        if isinstance(node, Mapping):
            message = node.get("message")
            if isinstance(message, Mapping):
                message_id = str(message.get("id") or "")
                if message_id:
                    node_by_message_id[message_id] = str(node_id)
    connection.execute(
        """
        INSERT INTO conversations(
            conversation_id,
            source_file_id,
            title,
            create_time,
            update_time,
            current_node_id,
            node_count,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            source_file_id = excluded.source_file_id,
            title = excluded.title,
            create_time = excluded.create_time,
            update_time = excluded.update_time,
            current_node_id = excluded.current_node_id,
            node_count = excluded.node_count,
            raw_json = excluded.raw_json
        """,
        (
            conversation_id,
            source_file_id,
            str(payload.get("title") or ""),
            str(payload.get("create_time") or ""),
            str(payload.get("update_time") or ""),
            str(payload.get("current_node") or ""),
            len(mapping),
            _json_dumps(_conversation_raw_summary(payload)),
        ),
    )
    for node_id, node in mapping.items():
        if not isinstance(node, Mapping):
            continue
        insert_conversation_node(
            connection,
            conversation_id=conversation_id,
            source_file_id=source_file_id,
            node_id=str(node_id),
            node=node,
            current_path_index=current_path_index.get(str(node_id)),
        )
    for node_id, node in mapping.items():
        if not isinstance(node, Mapping):
            continue
        for child_id in _string_list(node.get("children")):
            connection.execute(
                """
                INSERT INTO conversation_node_edges(conversation_id, parent_node_id, child_node_id)
                VALUES(?, ?, ?)
                ON CONFLICT(conversation_id, parent_node_id, child_node_id) DO NOTHING
                """,
                (conversation_id, str(node_id), child_id),
            )
    for node_id, node in mapping.items():
        if isinstance(node, Mapping):
            insert_message_attachments_from_node(
                connection,
                conversation_id=conversation_id,
                node_id=str(node_id),
                node=node,
                corpus_dir=corpus_dir,
            )
    if attachment_report is not None:
        insert_attachment_report_records(
            connection,
            conversation_id=conversation_id,
            node_by_message_id=node_by_message_id,
            corpus_dir=corpus_dir,
            attachment_report=attachment_report,
        )
    connection.commit()
    return counts(connection)


def ingest_web_fixture(connection: sqlite3.Connection, fixture_path: Path | str) -> dict[str, int]:
    fixture_path = Path(fixture_path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, Mapping):
        raise ValueError("web fixture must be a JSON object")
    initialize(connection)
    for event in _list_of_dicts(payload.get("web_access_events")):
        insert_web_access_event(connection, event, base_dir=fixture_path.parent)
    connection.commit()
    return counts(connection)


def insert_source_file(connection: sqlite3.Connection, path: Path | str, *, kind: str) -> str:
    path = Path(path)
    digest = _file_sha256(path)
    source_file_id = f"SF-{digest[:16]}"
    metadata = {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix,
        "kind": kind,
        "size_bytes": path.stat().st_size,
        "sha256": digest,
    }
    connection.execute(
        """
        INSERT INTO source_files(source_file_id, path, kind, size_bytes, sha256, raw_json)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            kind = excluded.kind,
            size_bytes = excluded.size_bytes,
            sha256 = excluded.sha256,
            raw_json = excluded.raw_json
        """,
        (source_file_id, str(path), kind, metadata["size_bytes"], digest, _json_dumps(metadata)),
    )
    return source_file_id


def insert_conversation_node(
    connection: sqlite3.Connection,
    *,
    conversation_id: str,
    source_file_id: str,
    node_id: str,
    node: Mapping[str, Any],
    current_path_index: int | None,
) -> None:
    message = node.get("message")
    if not isinstance(message, Mapping):
        message = {}
    author = message.get("author")
    if not isinstance(author, Mapping):
        author = {}
    content = message.get("content")
    if not isinstance(content, Mapping):
        content = {}
    metadata = message.get("metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    content_text = _message_content_text(content)
    child_ids = _string_list(node.get("children"))
    connection.execute(
        """
        INSERT INTO conversation_nodes(
            conversation_id,
            node_id,
            source_file_id,
            parent_node_id,
            child_ids_json,
            is_current_path,
            is_off_path,
            current_path_index,
            message_id,
            role,
            author_name,
            recipient,
            status,
            create_time,
            update_time,
            content_type,
            content_text,
            metadata_json,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id, node_id) DO UPDATE SET
            source_file_id = excluded.source_file_id,
            parent_node_id = excluded.parent_node_id,
            child_ids_json = excluded.child_ids_json,
            is_current_path = excluded.is_current_path,
            is_off_path = excluded.is_off_path,
            current_path_index = excluded.current_path_index,
            message_id = excluded.message_id,
            role = excluded.role,
            author_name = excluded.author_name,
            recipient = excluded.recipient,
            status = excluded.status,
            create_time = excluded.create_time,
            update_time = excluded.update_time,
            content_type = excluded.content_type,
            content_text = excluded.content_text,
            metadata_json = excluded.metadata_json,
            raw_json = excluded.raw_json
        """,
        (
            conversation_id,
            node_id,
            source_file_id,
            str(node.get("parent") or ""),
            _json_dumps(child_ids),
            1 if current_path_index is not None else 0,
            0 if current_path_index is not None else 1,
            current_path_index,
            str(message.get("id") or ""),
            str(author.get("role") or ""),
            str(author.get("name") or ""),
            str(message.get("recipient") or ""),
            str(message.get("status") or ""),
            str(message.get("create_time") or ""),
            str(message.get("update_time") or ""),
            str(content.get("content_type") or ""),
            content_text,
            _json_dumps(dict(metadata)),
            _json_dumps(dict(node)),
        ),
    )


def insert_message_attachments_from_node(
    connection: sqlite3.Connection,
    *,
    conversation_id: str,
    node_id: str,
    node: Mapping[str, Any],
    corpus_dir: Path,
) -> None:
    message = node.get("message")
    if not isinstance(message, Mapping):
        return
    metadata = message.get("metadata")
    if not isinstance(metadata, Mapping):
        return
    for attachment in _list_of_dicts(metadata.get("attachments")):
        _insert_attachment(
            connection,
            conversation_id=conversation_id,
            node_id=node_id,
            message_id=str(message.get("id") or ""),
            attachment_id=str(attachment.get("id") or attachment.get("file_id") or ""),
            name=str(attachment.get("name") or ""),
            mime_type=str(attachment.get("mime_type") or ""),
            local_path="",
            availability_state="missing",
            metadata=attachment,
            corpus_dir=corpus_dir,
        )


def insert_attachment_report_records(
    connection: sqlite3.Connection,
    *,
    conversation_id: str,
    node_by_message_id: Mapping[str, str],
    corpus_dir: Path,
    attachment_report: Mapping[str, Any],
) -> None:
    for conversation_report in _list_of_dicts(attachment_report.get("conversations")):
        if str(conversation_report.get("conversation_id") or "") != conversation_id:
            continue
        for attachment in _list_of_dicts(conversation_report.get("downloaded")):
            message_id = str(attachment.get("messageId") or attachment.get("message_id") or "")
            local_path = _attachment_local_path(corpus_dir, str(attachment.get("path") or ""))
            _insert_attachment(
                connection,
                conversation_id=conversation_id,
                node_id=node_by_message_id.get(message_id, message_id),
                message_id=message_id,
                attachment_id=str(attachment.get("id") or attachment.get("file_id") or attachment.get("library_file_id") or ""),
                name=str(attachment.get("name") or ""),
                mime_type=str(attachment.get("mime_type") or ""),
                local_path=str(local_path) if local_path else "",
                availability_state="available" if local_path and local_path.exists() else "missing",
                metadata=attachment,
                corpus_dir=corpus_dir,
            )
        for attachment in _list_of_dicts(conversation_report.get("failures")):
            message_id = str(attachment.get("messageId") or attachment.get("message_id") or "")
            _insert_attachment(
                connection,
                conversation_id=conversation_id,
                node_id=node_by_message_id.get(message_id, message_id),
                message_id=message_id,
                attachment_id=str(attachment.get("id") or attachment.get("file_id") or ""),
                name=str(attachment.get("name") or ""),
                mime_type=str(attachment.get("mime_type") or ""),
                local_path="",
                availability_state="download_failed",
                metadata=attachment,
                corpus_dir=corpus_dir,
            )


def ingest_exported_message(connection: sqlite3.Connection, record: Mapping[str, Any], *, index: int = 0) -> None:
    source_id = str(record.get("id") or f"exported-message-{index:06d}")
    content = _exported_message_content(record)
    connection.execute(
        """
        INSERT INTO source_records(
            source_kind, source_id, source_event_id, role, category, content, raw_json
        )
        VALUES('exported_conversation_message', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_kind, source_id) DO UPDATE SET
            source_event_id = excluded.source_event_id,
            role = excluded.role,
            category = excluded.category,
            content = excluded.content,
            raw_json = excluded.raw_json
        """,
        (
            source_id,
            source_id,
            str(record.get("role") or ""),
            "conversation_export",
            content,
            _json_dumps(dict(record)),
        ),
    )


def ingest_source_record(connection: sqlite3.Connection, turn: Mapping[str, Any]) -> None:
    turn_id = str(turn.get("turn_id") or "")
    connection.execute(
        """
        INSERT INTO source_records(
            source_kind, source_id, source_event_id, role, category, content, raw_json
        )
        VALUES('conversation_turn', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_kind, source_id) DO UPDATE SET
            source_event_id = excluded.source_event_id,
            role = excluded.role,
            category = excluded.category,
            content = excluded.content,
            raw_json = excluded.raw_json
        """,
        (
            turn_id,
            turn_id,
            str(turn.get("role") or ""),
            str(turn.get("category") or ""),
            str(turn.get("content") or ""),
            _json_dumps(dict(turn)),
        ),
    )


def insert_web_access_event(
    connection: sqlite3.Connection,
    event: Mapping[str, Any],
    *,
    base_dir: Path | str | None = None,
) -> str:
    normalized = _normalize_web_access_event(event, base_dir=base_dir)
    web_source = normalized["web_source"]
    access_event = normalized["access_event"]
    existing = connection.execute(
        "SELECT first_accessed_at FROM web_sources WHERE web_source_id = ?",
        (web_source["web_source_id"],),
    ).fetchone()
    first_accessed_at = (
        str(existing["first_accessed_at"])
        if existing is not None and str(existing["first_accessed_at"])
        else web_source["first_accessed_at"]
    )
    connection.execute(
        """
        INSERT INTO web_sources(
            web_source_id,
            url,
            domain,
            title,
            source_type,
            source_provenance,
            first_accessed_at,
            last_accessed_at,
            latest_access_status,
            latest_content_ref,
            latest_content_sha256,
            latest_content_bytes,
            latest_content_chars,
            metadata_json,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(web_source_id) DO UPDATE SET
            url = excluded.url,
            domain = excluded.domain,
            title = excluded.title,
            source_type = excluded.source_type,
            source_provenance = excluded.source_provenance,
            first_accessed_at = web_sources.first_accessed_at,
            last_accessed_at = excluded.last_accessed_at,
            latest_access_status = excluded.latest_access_status,
            latest_content_ref = excluded.latest_content_ref,
            latest_content_sha256 = excluded.latest_content_sha256,
            latest_content_bytes = excluded.latest_content_bytes,
            latest_content_chars = excluded.latest_content_chars,
            metadata_json = excluded.metadata_json,
            raw_json = excluded.raw_json
        """,
        (
            web_source["web_source_id"],
            web_source["url"],
            web_source["domain"],
            web_source["title"],
            web_source["source_type"],
            web_source["source_provenance"],
            first_accessed_at,
            web_source["last_accessed_at"],
            web_source["latest_access_status"],
            web_source["latest_content_ref"],
            web_source["latest_content_sha256"],
            web_source["latest_content_bytes"],
            web_source["latest_content_chars"],
            _json_dumps(web_source["metadata"]),
            _json_dumps(web_source["raw"]),
        ),
    )
    connection.execute(
        """
        INSERT INTO web_access_events(
            access_event_id,
            web_source_id,
            url,
            domain,
            title,
            accessed_at,
            access_status,
            source_type,
            source_provenance,
            http_status,
            content_ref,
            content_sha256,
            content_bytes,
            content_chars,
            excerpt,
            metadata_json,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(access_event_id) DO UPDATE SET
            web_source_id = excluded.web_source_id,
            url = excluded.url,
            domain = excluded.domain,
            title = excluded.title,
            accessed_at = excluded.accessed_at,
            access_status = excluded.access_status,
            source_type = excluded.source_type,
            source_provenance = excluded.source_provenance,
            http_status = excluded.http_status,
            content_ref = excluded.content_ref,
            content_sha256 = excluded.content_sha256,
            content_bytes = excluded.content_bytes,
            content_chars = excluded.content_chars,
            excerpt = excluded.excerpt,
            metadata_json = excluded.metadata_json,
            raw_json = excluded.raw_json
        """,
        (
            access_event["access_event_id"],
            access_event["web_source_id"],
            access_event["url"],
            access_event["domain"],
            access_event["title"],
            access_event["accessed_at"],
            access_event["access_status"],
            access_event["source_type"],
            access_event["source_provenance"],
            access_event["http_status"],
            access_event["content_ref"],
            access_event["content_sha256"],
            access_event["content_bytes"],
            access_event["content_chars"],
            access_event["excerpt"],
            _json_dumps(access_event["metadata"]),
            _json_dumps(access_event["raw"]),
        ),
    )
    return str(access_event["access_event_id"])


def insert_candidate(
    connection: sqlite3.Connection,
    candidate: MemoryCandidate,
    *,
    raw_mapping: Mapping[str, Any] | None = None,
) -> None:
    payload = candidate.to_dict()
    raw_json = _json_dumps(dict(raw_mapping) if raw_mapping is not None else payload)
    scope = payload["scope_hypothesis"]
    connection.execute(
        """
        INSERT INTO candidates(
            candidate_id,
            claim,
            source_provenance,
            scope_summary,
            scope_json,
            extraction_confidence,
            candidate_state,
            evidence_summary,
            validation_requirements_json,
            proposed_validity,
            representation_facet_hint,
            relation_hint,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(candidate_id) DO UPDATE SET
            claim = excluded.claim,
            source_provenance = excluded.source_provenance,
            scope_summary = excluded.scope_summary,
            scope_json = excluded.scope_json,
            extraction_confidence = excluded.extraction_confidence,
            candidate_state = excluded.candidate_state,
            evidence_summary = excluded.evidence_summary,
            validation_requirements_json = excluded.validation_requirements_json,
            proposed_validity = excluded.proposed_validity,
            representation_facet_hint = excluded.representation_facet_hint,
            relation_hint = excluded.relation_hint,
            raw_json = excluded.raw_json
        """,
        (
            candidate.candidate_id,
            candidate.claim,
            candidate.source_provenance,
            str(scope.get("summary") or ""),
            _json_dumps(scope),
            candidate.extraction_confidence,
            candidate.candidate_state,
            candidate.evidence_summary,
            _json_dumps(list(candidate.validation_requirements)),
            candidate.proposed_validity,
            candidate.representation_facet_hint,
            candidate.relation_hint,
            raw_json,
        ),
    )
    for key, value in dict(candidate.scope_hypothesis.dimensions).items():
        connection.execute(
            """
            INSERT INTO candidate_scope_dimensions(candidate_id, dimension_key, dimension_value)
            VALUES(?, ?, ?)
            ON CONFLICT(candidate_id, dimension_key) DO UPDATE SET
                dimension_value = excluded.dimension_value
            """,
            (candidate.candidate_id, key, value),
        )
    for index, reference in enumerate(candidate.evidence_references):
        evidence_id = insert_evidence_reference(connection, reference)
        connection.execute(
            """
            INSERT INTO candidate_evidence(candidate_id, evidence_id, evidence_order)
            VALUES(?, ?, ?)
            ON CONFLICT(candidate_id, evidence_id) DO UPDATE SET
                evidence_order = excluded.evidence_order
            """,
            (candidate.candidate_id, evidence_id, index),
        )


def insert_evidence_reference(connection: sqlite3.Connection, reference: EvidenceReference) -> str:
    payload = reference.to_dict()
    evidence_id = _evidence_id(payload)
    connection.execute(
        """
        INSERT INTO evidence_references(
            evidence_id, source_kind, source_id, source_event_id, location, summary, raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(evidence_id) DO UPDATE SET
            source_kind = excluded.source_kind,
            source_id = excluded.source_id,
            source_event_id = excluded.source_event_id,
            location = excluded.location,
            summary = excluded.summary,
            raw_json = excluded.raw_json
        """,
        (
            evidence_id,
            payload["source_kind"],
            payload["source_id"],
            payload["source_event_id"],
            payload["location"],
            payload["summary"],
            _json_dumps(payload),
        ),
    )
    return evidence_id


def insert_retrieval_probe(connection: sqlite3.Connection, probe: Mapping[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO retrieval_probes(
            query_id,
            query,
            expected_candidate_ids_json,
            required_scope_dimensions_json,
            required_uncertainty,
            raw_json
        )
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(query_id) DO UPDATE SET
            query = excluded.query,
            expected_candidate_ids_json = excluded.expected_candidate_ids_json,
            required_scope_dimensions_json = excluded.required_scope_dimensions_json,
            required_uncertainty = excluded.required_uncertainty,
            raw_json = excluded.raw_json
        """,
        (
            str(probe.get("query_id") or ""),
            str(probe.get("query") or ""),
            _json_dumps(list(probe.get("expected_candidate_ids") or [])),
            _json_dumps(list(probe.get("required_scope_dimensions") or [])),
            str(probe.get("required_uncertainty") or ""),
            _json_dumps(dict(probe)),
        ),
    )


def get_candidate(connection: sqlite3.Connection, candidate_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM candidates WHERE candidate_id = ?",
        (candidate_id,),
    ).fetchone()
    if row is None:
        return None
    candidate = dict(row)
    candidate["scope_dimensions"] = {
        scope_row["dimension_key"]: scope_row["dimension_value"]
        for scope_row in connection.execute(
            """
            SELECT dimension_key, dimension_value
            FROM candidate_scope_dimensions
            WHERE candidate_id = ?
            ORDER BY dimension_key
            """,
            (candidate_id,),
        ).fetchall()
    }
    candidate["validation_requirements"] = json.loads(candidate.pop("validation_requirements_json"))
    candidate["scope"] = json.loads(candidate.pop("scope_json"))
    candidate["raw"] = json.loads(candidate.pop("raw_json"))
    return candidate


def get_evidence(connection: sqlite3.Connection, evidence_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM evidence_references WHERE evidence_id = ?",
        (evidence_id,),
    ).fetchone()
    if row is None:
        return None
    evidence = dict(row)
    evidence["raw"] = json.loads(evidence.pop("raw_json"))
    return evidence


def get_web_source(connection: sqlite3.Connection, web_source_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM web_sources WHERE web_source_id = ?",
        (web_source_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_web_source(dict(row))


def get_web_access_event(connection: sqlite3.Connection, access_event_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM web_access_events WHERE access_event_id = ?",
        (access_event_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_web_access_event(dict(row))


def trace_candidate(connection: sqlite3.Connection, candidate_id: str) -> dict[str, Any] | None:
    candidate = get_candidate(connection, candidate_id)
    if candidate is None:
        return None
    evidence_rows = connection.execute(
        """
        SELECT evidence_id
        FROM candidate_evidence
        WHERE candidate_id = ?
        ORDER BY evidence_order
        """,
        (candidate_id,),
    ).fetchall()
    trace_items: list[dict[str, Any]] = []
    for row in evidence_rows:
        evidence = get_evidence(connection, row["evidence_id"])
        if evidence is None:
            continue
        source = connection.execute(
            """
            SELECT *
            FROM source_records
            WHERE source_kind = ? AND source_id = ?
            """,
            (evidence["source_kind"], evidence["source_id"]),
        ).fetchone()
        source_payload = dict(source) if source is not None else None
        if source_payload is not None:
            source_payload["raw"] = json.loads(source_payload.pop("raw_json"))
        trace_items.append({"evidence": evidence, "source_record": source_payload})
    return {"candidate": candidate, "trace": trace_items}


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    table_names = (
        "source_files",
        "conversations",
        "conversation_nodes",
        "conversation_node_edges",
        "attachments",
        "web_sources",
        "web_access_events",
        "source_records",
        "evidence_references",
        "candidates",
        "candidate_evidence",
        "candidate_scope_dimensions",
        "retrieval_probes",
    )
    return {
        table_name: int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        for table_name in table_names
    }


def candidate_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT candidate_id, candidate_state, source_provenance, claim
            FROM candidates
            ORDER BY candidate_id
            """
        ).fetchall()
    ]


def conversation_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT conversation_id, title, current_node_id, node_count
            FROM conversations
            ORDER BY title
            """
        ).fetchall()
    ]


def conversation_node_trace(connection: sqlite3.Connection, conversation_id: str, node_id: str) -> dict[str, Any] | None:
    node = connection.execute(
        """
        SELECT *
        FROM conversation_nodes
        WHERE conversation_id = ? AND node_id = ?
        """,
        (conversation_id, node_id),
    ).fetchone()
    if node is None:
        return None
    parent = None
    if node["parent_node_id"]:
        parent = connection.execute(
            """
            SELECT conversation_id, node_id, parent_node_id, child_ids_json, role, content_type, content_text
            FROM conversation_nodes
            WHERE conversation_id = ? AND node_id = ?
            """,
            (conversation_id, node["parent_node_id"]),
        ).fetchone()
    children = connection.execute(
        """
        SELECT n.conversation_id, n.node_id, n.parent_node_id, n.child_ids_json, n.role, n.content_type, n.content_text
        FROM conversation_node_edges e
        JOIN conversation_nodes n
          ON n.conversation_id = e.conversation_id
         AND n.node_id = e.child_node_id
        WHERE e.conversation_id = ? AND e.parent_node_id = ?
        ORDER BY n.node_id
        """,
        (conversation_id, node_id),
    ).fetchall()
    source_file = connection.execute(
        "SELECT * FROM source_files WHERE source_file_id = ?",
        (node["source_file_id"],),
    ).fetchone()
    return {
        "node": _decode_conversation_node(dict(node)),
        "parent": _decode_conversation_node(dict(parent)) if parent is not None else None,
        "children": [_decode_conversation_node(dict(child)) for child in children],
        "source_file": dict(source_file) if source_file is not None else None,
    }


def attachment_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT conversation_id, node_id, message_id, attachment_id, name, mime_type, local_path, availability_state
            FROM attachments
            ORDER BY conversation_id, name, attachment_record_id
            """
        ).fetchall()
    ]


def web_source_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT web_source_id, url, domain, title, source_type, source_provenance,
                   first_accessed_at, last_accessed_at, latest_access_status,
                   latest_content_ref, latest_content_sha256,
                   latest_content_bytes, latest_content_chars
            FROM web_sources
            ORDER BY domain, url
            """
        ).fetchall()
    ]


def web_access_event_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT access_event_id, web_source_id, url, domain, title, accessed_at,
                   access_status, source_type, source_provenance, http_status,
                   content_ref, content_sha256, content_bytes, content_chars, excerpt
            FROM web_access_events
            ORDER BY accessed_at, access_event_id
            """
        ).fetchall()
    ]


def evidence_reference_for_conversation_node(
    connection: sqlite3.Connection,
    conversation_id: str,
    node_id: str,
    *,
    location: str = "content_text",
    summary: str = "",
) -> EvidenceReference:
    row = connection.execute(
        """
        SELECT conversation_id, node_id, content_text, content_type, role
        FROM conversation_nodes
        WHERE conversation_id = ? AND node_id = ?
        """,
        (conversation_id, node_id),
    ).fetchone()
    if row is None:
        raise KeyError(f"conversation node not found: {conversation_id}:{node_id}")
    return EvidenceReference(
        source_kind="conversation_node",
        source_id=f"{conversation_id}:{node_id}",
        source_event_id=node_id,
        location=location,
        summary=summary or _reference_summary(row["content_text"], fallback=f"{row['role']} {row['content_type']} node"),
    )


def evidence_reference_for_attachment(
    connection: sqlite3.Connection,
    attachment_record_id: str,
    *,
    location: str = "attachment",
    summary: str = "",
) -> EvidenceReference:
    row = connection.execute(
        """
        SELECT attachment_record_id, node_id, name, availability_state
        FROM attachments
        WHERE attachment_record_id = ?
        """,
        (attachment_record_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"attachment not found: {attachment_record_id}")
    return EvidenceReference(
        source_kind="attachment",
        source_id=attachment_record_id,
        source_event_id=row["node_id"],
        location=location,
        summary=summary or f"{row['name']} ({row['availability_state']})",
    )


def evidence_reference_for_web_access_event(
    connection: sqlite3.Connection,
    access_event_id: str,
    *,
    location: str = "excerpt",
    summary: str = "",
) -> EvidenceReference:
    row = connection.execute(
        """
        SELECT access_event_id, url, title, access_status, excerpt
        FROM web_access_events
        WHERE access_event_id = ?
        """,
        (access_event_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"web access event not found: {access_event_id}")
    fallback = f"{row['title'] or row['url']} ({row['access_status']})"
    return EvidenceReference(
        source_kind="web_access_event",
        source_id=access_event_id,
        source_event_id=access_event_id,
        location=location,
        summary=summary or _reference_summary(row["excerpt"], fallback=fallback),
    )


def web_access_trace(connection: sqlite3.Connection, access_event_id: str) -> dict[str, Any] | None:
    access_event = get_web_access_event(connection, access_event_id)
    if access_event is None:
        return None
    return {
        "access_event": access_event,
        "web_source": get_web_source(connection, access_event["web_source_id"]),
    }


def trace_evidence_reference(connection: sqlite3.Connection, reference: EvidenceReference) -> dict[str, Any]:
    payload = reference.to_dict()
    source_kind = payload["source_kind"]
    if source_kind == "conversation_node":
        conversation_id, node_id = _parse_conversation_node_source_id(payload["source_id"])
        return {
            "evidence_reference": payload,
            "source": conversation_node_trace(connection, conversation_id, node_id),
        }
    if source_kind == "attachment":
        attachment = connection.execute(
            "SELECT * FROM attachments WHERE attachment_record_id = ?",
            (payload["source_id"],),
        ).fetchone()
        if attachment is None:
            return {"evidence_reference": payload, "source": None}
        attachment_payload = dict(attachment)
        attachment_payload["metadata"] = json.loads(attachment_payload.pop("metadata_json"))
        return {
            "evidence_reference": payload,
            "source": {
                "attachment": attachment_payload,
                "node": conversation_node_trace(connection, attachment_payload["conversation_id"], attachment_payload["node_id"]),
            },
        }
    if source_kind == "web_access_event":
        return {
            "evidence_reference": payload,
            "source": web_access_trace(connection, payload["source_id"]),
        }
    if source_kind in {"conversation_turn", "exported_conversation_message"}:
        source = connection.execute(
            """
            SELECT *
            FROM source_records
            WHERE source_kind = ? AND source_id = ?
            """,
            (source_kind, payload["source_id"]),
        ).fetchone()
        if source is None:
            return {"evidence_reference": payload, "source": None}
        source_payload = dict(source)
        source_payload["raw"] = json.loads(source_payload.pop("raw_json"))
        return {"evidence_reference": payload, "source": source_payload}
    return {"evidence_reference": payload, "source": None}


def _insert_attachment(
    connection: sqlite3.Connection,
    *,
    conversation_id: str,
    node_id: str,
    message_id: str,
    attachment_id: str,
    name: str,
    mime_type: str,
    local_path: str,
    availability_state: str,
    metadata: Mapping[str, Any],
    corpus_dir: Path,
) -> None:
    local = Path(local_path) if local_path else None
    digest = _file_sha256(local) if local is not None and local.exists() else ""
    size_bytes = local.stat().st_size if local is not None and local.exists() else None
    if local is not None and local.exists():
        insert_source_file(connection, local, kind="attachment_file")
    stable = {
        "conversation_id": conversation_id,
        "node_id": node_id,
        "message_id": message_id,
        "name": name,
    }
    attachment_record_id = f"ATT-{hashlib.sha256(_json_dumps(stable).encode('utf-8')).hexdigest()[:16]}"
    connection.execute(
        """
        INSERT INTO attachments(
            attachment_record_id,
            conversation_id,
            node_id,
            message_id,
            attachment_id,
            name,
            mime_type,
            local_path,
            availability_state,
            size_bytes,
            sha256,
            metadata_json
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(attachment_record_id) DO UPDATE SET
            local_path = excluded.local_path,
            availability_state = excluded.availability_state,
            size_bytes = excluded.size_bytes,
            sha256 = excluded.sha256,
            metadata_json = excluded.metadata_json
        """,
        (
            attachment_record_id,
            conversation_id,
            node_id,
            message_id,
            attachment_id,
            name,
            mime_type,
            local_path,
            availability_state,
            size_bytes,
            digest,
            _json_dumps({"metadata": dict(metadata), "corpus_dir": str(corpus_dir)}),
        ),
    )


def _normalize_web_access_event(event: Mapping[str, Any], *, base_dir: Path | str | None = None) -> dict[str, dict[str, Any]]:
    url = str(event.get("url") or "").strip()
    if not url:
        raise ValueError("web access event url missing")
    parsed = urlparse(url)
    domain = str(event.get("domain") or parsed.netloc or "").strip()
    title = str(event.get("title") or "").strip()
    accessed_at = str(event.get("accessed_at") or "").strip()
    access_status = str(event.get("access_status") or "").strip() or "unknown"
    source_type = str(event.get("source_type") or "web_page").strip()
    source_provenance = str(event.get("source_provenance") or "external").strip() or "external"
    content_ref = str(event.get("content_ref") or "").strip()
    content_path = _resolve_content_ref(content_ref, base_dir=base_dir)
    content_sha256 = _file_sha256(content_path) if content_path is not None and content_path.exists() else ""
    content_bytes = content_path.stat().st_size if content_path is not None and content_path.exists() else 0
    content_chars = len(content_path.read_text(encoding="utf-8", errors="replace")) if content_path is not None and content_path.exists() else 0
    metadata = event.get("metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    access_event_id = str(event.get("access_event_id") or "").strip()
    if not access_event_id:
        access_event_id = _web_access_event_id(url=url, accessed_at=accessed_at, access_status=access_status)
    web_source_id = _web_source_id(url)
    raw = dict(event)
    raw["content_ref_resolved"] = str(content_path) if content_path is not None else ""
    access_event = {
        "access_event_id": access_event_id,
        "web_source_id": web_source_id,
        "url": url,
        "domain": domain,
        "title": title,
        "accessed_at": accessed_at,
        "access_status": access_status,
        "source_type": source_type,
        "source_provenance": source_provenance,
        "http_status": _optional_int(event.get("http_status")),
        "content_ref": content_ref,
        "content_sha256": content_sha256,
        "content_bytes": content_bytes,
        "content_chars": content_chars,
        "excerpt": str(event.get("excerpt") or "").strip(),
        "metadata": dict(metadata),
        "raw": raw,
    }
    web_source = {
        "web_source_id": web_source_id,
        "url": url,
        "domain": domain,
        "title": title,
        "source_type": source_type,
        "source_provenance": source_provenance,
        "first_accessed_at": accessed_at,
        "last_accessed_at": accessed_at,
        "latest_access_status": access_status,
        "latest_content_ref": content_ref,
        "latest_content_sha256": content_sha256,
        "latest_content_bytes": content_bytes,
        "latest_content_chars": content_chars,
        "metadata": dict(metadata),
        "raw": raw,
    }
    return {"web_source": web_source, "access_event": access_event}


def _resolve_content_ref(content_ref: str, *, base_dir: Path | str | None) -> Path | None:
    if not content_ref:
        return None
    path = Path(content_ref)
    if path.is_absolute():
        return path
    if base_dir is None:
        return path
    return Path(base_dir) / path


def _web_source_id(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"WEB-SRC-{digest}"


def _web_access_event_id(*, url: str, accessed_at: str, access_status: str) -> str:
    payload = {"url": url, "accessed_at": accessed_at, "access_status": access_status}
    digest = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()[:16]
    return f"WEB-EV-{digest}"


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decode_web_source(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("metadata_json", "raw_json"):
        if key in row:
            row[key.removesuffix("_json")] = json.loads(row.pop(key))
    return row


def _decode_web_access_event(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("metadata_json", "raw_json"):
        if key in row:
            row[key.removesuffix("_json")] = json.loads(row.pop(key))
    return row


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_spec: str) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_spec}")


def _fixture_candidate_states(fixture: Mapping[str, Any]) -> dict[str, str]:
    outcome = fixture.get("expected_outcome")
    if not isinstance(outcome, Mapping):
        return {}
    states: dict[str, str] = {}
    for candidate_id in _string_list(outcome.get("deferred_candidate_ids")):
        states[candidate_id] = "deferred"
    for key in (
        "active_memory_candidate_ids",
        "dormant_or_low_priority_candidate_ids",
        "rejected_candidate_ids",
    ):
        for candidate_id in _string_list(outcome.get(key)):
            states.setdefault(candidate_id, "closed")
    for edge in _list_of_dicts(outcome.get("supersession_edges")):
        candidate_id = str(edge.get("to_candidate_id") or "")
        if candidate_id:
            states.setdefault(candidate_id, "closed")
    return states


def _evidence_id(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_json_dumps(dict(payload)).encode("utf-8")).hexdigest()[:16]
    return f"EV-{digest}"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _current_path_node_ids(mapping: Mapping[str, Any], current_node: str) -> list[str]:
    path: list[str] = []
    seen: set[str] = set()
    node_id = current_node
    while node_id and node_id not in seen:
        node = mapping.get(node_id)
        if not isinstance(node, Mapping):
            break
        seen.add(node_id)
        path.append(node_id)
        node_id = str(node.get("parent") or "")
    path.reverse()
    return path


def _conversation_raw_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "conversation_id": payload.get("conversation_id"),
        "title": payload.get("title"),
        "create_time": payload.get("create_time"),
        "update_time": payload.get("update_time"),
        "current_node": payload.get("current_node"),
        "mapping_keys": list(payload.get("mapping", {}).keys()) if isinstance(payload.get("mapping"), Mapping) else [],
        "source": "chatgpt_export",
    }


def _message_content_text(content: Mapping[str, Any]) -> str:
    parts = content.get("parts")
    if isinstance(parts, list):
        normalized_parts = []
        for item in parts:
            if isinstance(item, str):
                normalized_parts.append(item)
            elif item is not None:
                normalized_parts.append(_json_dumps(item))
        return "\n".join(part for part in normalized_parts if part.strip())
    text = content.get("text")
    if isinstance(text, str):
        return text
    return ""


def _load_attachment_report(corpus_dir: Path) -> dict[str, Any]:
    report_path = corpus_dir / "attachment-export-report.json"
    if not report_path.exists():
        return {}
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    if not isinstance(report, dict):
        raise ValueError("attachment-export-report.json must be a JSON object")
    return report


def _attachment_local_path(corpus_dir: Path, report_path: str) -> Path | None:
    if not report_path:
        return None
    return corpus_dir / unquote(report_path)


def _decode_conversation_node(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("child_ids_json", "metadata_json", "raw_json"):
        if key in row:
            decoded_key = key.removesuffix("_json")
            row[decoded_key] = json.loads(row.pop(key))
    return row


def _parse_conversation_node_source_id(source_id: str) -> tuple[str, str]:
    conversation_id, separator, node_id = source_id.partition(":")
    if not separator or not conversation_id or not node_id:
        raise ValueError(f"invalid conversation_node source_id: {source_id}")
    return conversation_id, node_id


def _reference_summary(text: str, *, fallback: str) -> str:
    text = " ".join(str(text or "").split())
    if not text:
        return fallback
    return text[:160]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exported_message_content(record: Mapping[str, Any]) -> str:
    contents = record.get("contents")
    if not isinstance(contents, list):
        return ""
    parts: list[str] = []
    for item in contents:
        if not isinstance(item, Mapping):
            continue
        content_type = str(item.get("type") or "")
        if content_type == "text":
            text = str(item.get("content") or "").strip()
            if text:
                parts.append(text)
        elif content_type:
            parts.append(f"[{content_type}]")
    return "\n".join(parts)
