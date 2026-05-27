"""
BookBrain Benchmark
===================
Measures speed and correctness of every BookBrain subsystem.
Outputs a formatted console report + BENCHMARK_REPORT.md.

Run:
    # Full benchmark (Iron Letter mock book only)
    python -m tests.bookbrain.benchmark

    # Include a real-book bootstrap test (e.g. Crime and Punishment)
    python -m tests.bookbrain.benchmark --real-book "Crime and Punishment" --author "Fyodor Dostoevsky"

    # Skip slow phases
    python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint

    # Custom service URL
    python -m tests.bookbrain.benchmark --base-url http://staging.internal:8000/api/v1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Import mock data — same fixtures used in demo and unit tests
# ---------------------------------------------------------------------------
try:
    from tests.bookbrain.mock_book_chunks import (
        BOOK_TITLE as MOCK_BOOK_TITLE,
        DEMO_SEARCH_QUERIES,
        EXPECTED_CHARACTERS,
        build_mock_chunks,
    )
except ImportError:
    print("ERROR: Run from microservices/ai-service/ root:")
    print("  python -m tests.bookbrain.benchmark")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BENCHMARK_BOOK_ID = "benchmark-iron-letter-001"
REPORT_PATH = Path(__file__).parent / "BENCHMARK_REPORT.md"

INGEST_WARN_S  = 10.0
INGEST_FAIL_S  = 20.0
SEARCH_WARN_S  =  2.0
SEARCH_FAIL_S  =  5.0
LINT_FAIL_S    = 120.0


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class PhaseResult:
    name: str
    passed: bool
    warning: bool = False
    duration_s: float = 0.0
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class BenchmarkRun:
    started_at: str = ""
    base_url: str = ""
    real_book_title: Optional[str] = None
    real_book_author: Optional[str] = None

    health:    Optional[PhaseResult] = None
    bootstrap: Optional[PhaseResult] = None
    ingest:    Optional[PhaseResult] = None
    wiki_audit: Optional[PhaseResult] = None
    search:    Optional[PhaseResult] = None
    lint:      Optional[PhaseResult] = None
    export:    Optional[PhaseResult] = None

    total_duration_s: float = 0.0


# ---------------------------------------------------------------------------
# Console formatting helpers
# ---------------------------------------------------------------------------

W = 62  # report width

def _hr(char="─"):
    return char * W

def _banner(title: str):
    pad = (W - len(title) - 2) // 2
    print("╔" + "═" * W + "╗")
    print("║" + " " * pad + title + " " * (W - pad - len(title)) + "║")
    print("╚" + "═" * W + "╝")

def _section(title: str):
    print()
    print(f"  {title}")
    print("  " + _hr())

def _row(label: str, value: str, width: int = 30):
    dots = "." * (width - len(label))
    print(f"  {label} {dots} {value}")

def _verdict(result: PhaseResult) -> str:
    if not result.passed:
        return "❌ FAIL"
    if result.warning:
        return "⚠️  WARN"
    return "✅ PASS"

def _status(ok: bool, warn: bool = False) -> str:
    if not ok:
        return "❌"
    if warn:
        return "⚠️ "
    return "✅"


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

async def run_health(client: httpx.AsyncClient, base_url: str) -> PhaseResult:
    t0 = time.monotonic()
    try:
        r = await client.get(base_url.replace("/api/v1", "") + "/", timeout=10.0)
        ok = r.status_code < 300
        return PhaseResult(
            name="Health Check",
            passed=ok,
            duration_s=time.monotonic() - t0,
            detail=f"HTTP {r.status_code}",
            data=r.json() if ok else {},
        )
    except Exception as e:
        return PhaseResult(
            name="Health Check",
            passed=False,
            duration_s=time.monotonic() - t0,
            detail=str(e),
        )


async def run_reset(client: httpx.AsyncClient, base_url: str, book_id: str):
    try:
        await client.delete(f"{base_url}/bookbrain/{book_id}", timeout=15.0)
    except Exception:
        pass  # ignore — book may not exist yet


async def run_bootstrap(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
    book_title: str,
    author: Optional[str],
) -> PhaseResult:
    t0 = time.monotonic()
    payload = {"book_title": book_title}
    if author:
        payload["author"] = author
    try:
        r = await client.post(
            f"{base_url}/bookbrain/{book_id}/bootstrap",
            json=payload,
            timeout=90.0,
        )
        r.raise_for_status()
        data = r.json()
        duration = time.monotonic() - t0
        succeeded = data.get("sources_succeeded", [])
        seeded    = data.get("entries_seeded", 0)
        passed    = len(succeeded) > 0
        warn      = seeded == 0
        detail = (
            f"{len(succeeded)}/4 sources succeeded, "
            f"{seeded} entries seeded, "
            f"{duration:.1f}s"
        )
        return PhaseResult(
            name="Bootstrap",
            passed=passed,
            warning=warn,
            duration_s=duration,
            detail=detail,
            data=data,
        )
    except Exception as e:
        return PhaseResult(
            name="Bootstrap",
            passed=False,
            duration_s=time.monotonic() - t0,
            detail=str(e),
        )


async def run_ingest(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
) -> PhaseResult:
    chunks = build_mock_chunks()
    total_chars = sum(c["character_count"] for c in chunks)
    timings: list[dict] = []
    all_passed = True
    any_warn = False

    t_total = time.monotonic()
    for chunk in chunks:
        t0 = time.monotonic()
        try:
            r = await client.post(
                f"{base_url}/bookbrain/{book_id}/ingest",
                json={
                    "chunk_text":   chunk["text"],
                    "chunk_index":  chunk["chunk_id"] - 1,
                    "book_title":   MOCK_BOOK_TITLE,
                    "total_chunks": len(chunks),
                },
                timeout=60.0,
            )
            r.raise_for_status()
            elapsed = time.monotonic() - t0
            ok   = elapsed < INGEST_FAIL_S
            warn = elapsed >= INGEST_WARN_S
            if not ok:
                all_passed = False
            if warn:
                any_warn = True
            timings.append({
                "chunk_id":  chunk["chunk_id"],
                "chars":     chunk["character_count"],
                "duration_s": round(elapsed, 2),
                "passed":    ok,
                "warning":   warn,
            })
            status = _status(ok, warn)
            print(f"    Chunk {chunk['chunk_id']} ({chunk['character_count']:,} chars) "
                  f"... {elapsed:.1f}s  {status}")
        except Exception as e:
            elapsed = time.monotonic() - t0
            all_passed = False
            timings.append({
                "chunk_id":  chunk["chunk_id"],
                "chars":     chunk["character_count"],
                "duration_s": round(elapsed, 2),
                "passed":    False,
                "error":     str(e),
            })
            print(f"    Chunk {chunk['chunk_id']} ... ❌ ERROR: {e}")

    total_duration = time.monotonic() - t_total
    throughput = total_chars / total_duration if total_duration > 0 else 0
    avg_per_chunk = total_duration / len(chunks)

    return PhaseResult(
        name="Chunk Ingestion",
        passed=all_passed,
        warning=any_warn and all_passed,
        duration_s=total_duration,
        detail=(
            f"{len(chunks)} chunks, {total_chars:,} chars, "
            f"{throughput:.0f} chars/sec, avg {avg_per_chunk:.1f}s/chunk"
        ),
        data={
            "chunks": timings,
            "total_chars": total_chars,
            "throughput_chars_per_sec": round(throughput, 1),
            "avg_per_chunk_s": round(avg_per_chunk, 2),
        },
    )


async def run_wiki_audit(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
) -> PhaseResult:
    t0 = time.monotonic()
    try:
        r = await client.get(f"{base_url}/bookbrain/{book_id}/wiki", timeout=15.0)
        r.raise_for_status()
        entries = r.json()
    except Exception as e:
        return PhaseResult(
            name="Wiki Audit",
            passed=False,
            duration_s=time.monotonic() - t0,
            detail=str(e),
        )

    # Count by type
    by_type: dict[str, int] = {}
    for e in entries:
        by_type[e["entry_type"]] = by_type.get(e["entry_type"], 0) + 1

    # Check expected characters
    entry_titles = {e["title"].lower() for e in entries}
    char_hits: list[dict] = []
    for ec in EXPECTED_CHARACTERS:
        found_by_name  = ec["name"].lower() in entry_titles
        found_by_alias = any(a.lower() in " ".join(entry_titles) for a in ec["aliases"])
        found = found_by_name or found_by_alias
        char_hits.append({
            "name":   ec["name"],
            "found":  found,
            "method": "name" if found_by_name else ("alias" if found_by_alias else "—"),
        })

    characters_found = sum(1 for c in char_hits if c["found"])
    passed = characters_found >= max(1, len(EXPECTED_CHARACTERS) - 1)  # allow 1 miss
    warn   = characters_found < len(EXPECTED_CHARACTERS)

    return PhaseResult(
        name="Wiki Quality Audit",
        passed=passed,
        warning=warn and passed,
        duration_s=time.monotonic() - t0,
        detail=(
            f"{len(entries)} total entries across {len(by_type)} types; "
            f"{characters_found}/{len(EXPECTED_CHARACTERS)} expected characters found"
        ),
        data={
            "total_entries":    len(entries),
            "by_type":          by_type,
            "character_hits":   char_hits,
            "characters_found": characters_found,
        },
    )


async def run_search(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
) -> PhaseResult:
    timings: list[dict] = []
    all_passed = True
    any_warn   = False

    for query, expected_type in DEMO_SEARCH_QUERIES:
        t0 = time.monotonic()
        try:
            r = await client.post(
                f"{base_url}/bookbrain/{book_id}/wiki/search",
                json={"query": query, "top_k": 3},
                timeout=30.0,
            )
            r.raise_for_status()
            data     = r.json()
            elapsed  = time.monotonic() - t0
            results  = data.get("results", [])
            top_type = results[0]["entry_type"] if results else "none"
            ok   = elapsed < SEARCH_FAIL_S
            warn = elapsed >= SEARCH_WARN_S
            if not ok:
                all_passed = False
            if warn:
                any_warn = True
            hit = top_type == expected_type
            timings.append({
                "query":         query,
                "expected_type": expected_type,
                "top_type":      top_type,
                "type_match":    hit,
                "duration_s":    round(elapsed, 3),
                "results":       len(results),
                "passed":        ok,
                "warning":       warn,
            })
            status = _status(ok, warn)
            match  = "✅" if hit else "⚠️ "
            print(f"    {elapsed:.3f}s  {status}  type={top_type:<12} {match}  \"{query[:40]}\"")
        except Exception as e:
            elapsed = time.monotonic() - t0
            all_passed = False
            timings.append({
                "query": query, "duration_s": round(elapsed, 3),
                "passed": False, "error": str(e),
            })
            print(f"    ❌ ERROR: {e}")

    latencies   = [t["duration_s"] for t in timings if "error" not in t]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    type_matches = sum(1 for t in timings if t.get("type_match"))

    return PhaseResult(
        name="Semantic Search",
        passed=all_passed,
        warning=any_warn and all_passed,
        duration_s=sum(latencies),
        detail=(
            f"{len(DEMO_SEARCH_QUERIES)} queries, avg {avg_latency:.3f}s, "
            f"max {max_latency:.3f}s, "
            f"{type_matches}/{len(DEMO_SEARCH_QUERIES)} top results matched expected type"
        ),
        data={
            "queries":         timings,
            "avg_latency_s":   round(avg_latency, 3),
            "max_latency_s":   round(max_latency, 3),
            "type_match_rate": f"{type_matches}/{len(DEMO_SEARCH_QUERIES)}",
        },
    )


async def run_lint(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
) -> PhaseResult:
    t0 = time.monotonic()
    try:
        r = await client.post(
            f"{base_url}/bookbrain/{book_id}/lint",
            timeout=180.0,
        )
        r.raise_for_status()
        data = r.json()
        duration = time.monotonic() - t0
        checked  = data.get("entries_checked", 0)
        enriched = data.get("entries_enriched", 0)
        gaps     = len(data.get("gaps", []))
        warn     = duration > LINT_FAIL_S / 2
        return PhaseResult(
            name="Lint Pass",
            passed=True,
            warning=warn,
            duration_s=duration,
            detail=(
                f"{checked} entries checked, "
                f"{gaps} gaps found, "
                f"{enriched} enriched, "
                f"{duration:.1f}s"
            ),
            data=data,
        )
    except Exception as e:
        return PhaseResult(
            name="Lint Pass",
            passed=False,
            duration_s=time.monotonic() - t0,
            detail=str(e),
        )


async def run_export(
    client: httpx.AsyncClient,
    base_url: str,
    book_id: str,
) -> PhaseResult:
    t0 = time.monotonic()
    try:
        r = await client.get(
            f"{base_url}/bookbrain/{book_id}/export",
            timeout=15.0,
        )
        r.raise_for_status()
        data = r.json()
        md   = data.get("markdown", "")
        duration = time.monotonic() - t0
        lines = md.count("\n")
        return PhaseResult(
            name="Markdown Export",
            passed=bool(md),
            duration_s=duration,
            detail=f"{len(md):,} chars, {lines} lines, {duration:.2f}s",
            data={"markdown_chars": len(md), "markdown_lines": lines},
        )
    except Exception as e:
        return PhaseResult(
            name="Markdown Export",
            passed=False,
            duration_s=time.monotonic() - t0,
            detail=str(e),
        )


# ---------------------------------------------------------------------------
# Console report printer
# ---------------------------------------------------------------------------

def print_report(run: BenchmarkRun):
    print()
    _banner(f"BOOKBRAIN BENCHMARK  —  {run.started_at}")
    print(f"  Service: {run.base_url}")
    print(f"  Mock book: {MOCK_BOOK_TITLE}  (book_id: {BENCHMARK_BOOK_ID})")
    if run.real_book_title:
        print(f"  Real book: {run.real_book_title}"
              + (f" by {run.real_book_author}" if run.real_book_author else ""))

    # --- Health ---
    if run.health:
        _section("Phase 0 │ Health Check")
        _row("Status", run.health.detail)
        _row("Verdict", _verdict(run.health))

    # --- Bootstrap ---
    if run.bootstrap:
        _section(f"Phase 1 │ Bootstrap — {run.real_book_title or MOCK_BOOK_TITLE}")
        d = run.bootstrap.data
        sources_ok  = d.get("sources_succeeded", [])
        sources_all = d.get("sources_queried", [])
        _row("Sources queried",   ", ".join(sources_all))
        _row("Sources succeeded", f"{len(sources_ok)}/{len(sources_all)}  ({', '.join(sources_ok) or 'none'})")
        _row("Entries seeded",    str(d.get("entries_seeded", 0)))
        _row("Duration",          f"{run.bootstrap.duration_s:.1f}s")
        _row("Verdict",           _verdict(run.bootstrap))

    # --- Ingest ---
    if run.ingest:
        _section(f"Phase 2 │ Chunk Ingestion — {MOCK_BOOK_TITLE}")
        d = run.ingest.data
        # per-chunk rows already printed live; show summary only
        _row("Total chunks",      str(len(d.get("chunks", []))))
        _row("Total chars",       f"{d.get('total_chars', 0):,}")
        _row("Total duration",    f"{run.ingest.duration_s:.1f}s")
        _row("Throughput",        f"{d.get('throughput_chars_per_sec', 0):.0f} chars/sec")
        _row("Avg per chunk",     f"{d.get('avg_per_chunk_s', 0):.1f}s")
        _row("Verdict",           _verdict(run.ingest))

    # --- Wiki audit ---
    if run.wiki_audit:
        _section("Phase 3 │ Wiki Quality Audit")
        d = run.wiki_audit.data
        by_type = d.get("by_type", {})
        _row("Total entries",     str(d.get("total_entries", 0)))
        for etype, count in sorted(by_type.items()):
            _row(f"  → {etype}", str(count))
        print()
        _row("Expected characters", f"{d.get('characters_found', 0)}/{len(EXPECTED_CHARACTERS)}")
        for ch in d.get("character_hits", []):
            icon = "✅" if ch["found"] else "❌"
            _row(f"  {icon} {ch['name']}", f"found via {ch.get('method', '—')}")
        _row("Verdict", _verdict(run.wiki_audit))

    # --- Search ---
    if run.search:
        _section("Phase 4 │ Semantic Search")
        d = run.search.data
        # query rows already printed live
        _row("Avg latency",     f"{d.get('avg_latency_s', 0):.3f}s")
        _row("Max latency",     f"{d.get('max_latency_s', 0):.3f}s")
        _row("Type match rate", d.get("type_match_rate", "—"))
        _row("Verdict",         _verdict(run.search))

    # --- Lint ---
    if run.lint:
        _section("Phase 5 │ Lint Pass")
        d = run.lint.data
        _row("Entries checked",  str(d.get("entries_checked", 0)))
        _row("Gaps detected",    str(len(d.get("gaps", []))))
        _row("Entries enriched", str(d.get("entries_enriched", 0)))
        _row("Duration",         f"{run.lint.duration_s:.1f}s")
        _row("Verdict",          _verdict(run.lint))

    # --- Export ---
    if run.export:
        _section("Phase 6 │ Markdown Export")
        d = run.export.data
        _row("Output size",     f"{d.get('markdown_chars', 0):,} chars")
        _row("Lines",           str(d.get("markdown_lines", 0)))
        _row("Duration",        f"{run.export.duration_s:.2f}s")
        _row("Verdict",         _verdict(run.export))

    # --- Summary ---
    print()
    print("  " + "═" * W)
    print("  BENCHMARK SUMMARY")
    print("  " + "═" * W)

    phases = [
        ("Health Check",     run.health),
        ("Bootstrap",        run.bootstrap),
        ("Chunk Ingestion",  run.ingest),
        ("Wiki Quality",     run.wiki_audit),
        ("Search Latency",   run.search),
        ("Lint Pass",        run.lint),
        ("Export",           run.export),
    ]
    all_passed = True
    for label, result in phases:
        if result is None:
            continue
        icon = _verdict(result)
        detail_short = result.detail[:35] if result.detail else ""
        _row(label, f"{icon}  {detail_short}")
        if not result.passed:
            all_passed = False

    print("  " + "─" * W)
    overall = "✅  ALL SYSTEMS GO" if all_passed else "❌  FAILURES DETECTED — see phases above"
    print(f"  OVERALL ............... {overall}")
    print(f"  Total runtime ......... {run.total_duration_s:.1f}s")
    print(f"  Report saved to ....... {REPORT_PATH.name}")
    print("  " + "═" * W)
    print()


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------

def _md_status(ok: bool, warn: bool = False) -> str:
    if not ok:
        return "❌ FAIL"
    if warn:
        return "⚠️ WARN"
    return "✅ PASS"


def write_markdown_report(run: BenchmarkRun):
    lines: list[str] = []

    lines += [
        f"# BookBrain Benchmark Report",
        f"",
        f"**Generated:** {run.started_at}  ",
        f"**Service:** `{run.base_url}`  ",
        f"**Mock book:** *{MOCK_BOOK_TITLE}* (`{BENCHMARK_BOOK_ID}`)  ",
    ]
    if run.real_book_title:
        lines.append(
            f"**Real book tested:** *{run.real_book_title}*"
            + (f" by {run.real_book_author}" if run.real_book_author else "") + "  "
        )

    lines += ["", "---", ""]

    # Summary table first — the "screenshot this" section
    lines += [
        "## Summary",
        "",
        "| Phase | Result | Detail |",
        "|-------|--------|--------|",
    ]
    phases = [
        ("Health Check",      run.health),
        ("Bootstrap",         run.bootstrap),
        ("Chunk Ingestion",   run.ingest),
        ("Wiki Quality",      run.wiki_audit),
        ("Semantic Search",   run.search),
        ("Lint Pass",         run.lint),
        ("Markdown Export",   run.export),
    ]
    all_passed = True
    for label, result in phases:
        if result is None:
            lines.append(f"| {label} | ⏭️ Skipped | — |")
            continue
        icon = _md_status(result.passed, result.warning)
        if not result.passed:
            all_passed = False
        lines.append(f"| {label} | {icon} | {result.detail} |")

    overall = "✅ ALL SYSTEMS GO" if all_passed else "❌ FAILURES DETECTED"
    lines += [
        "",
        f"**Overall verdict:** {overall}  ",
        f"**Total runtime:** {run.total_duration_s:.1f}s  ",
        "",
        "---",
        "",
    ]

    # ---- Bootstrap detail ----
    if run.bootstrap:
        lines += ["## Phase 1 — Bootstrap", ""]
        d = run.bootstrap.data
        lines += [
            f"| | |",
            f"|---|---|",
            f"| Sources queried | {', '.join(d.get('sources_queried', []))} |",
            f"| Sources succeeded | {', '.join(d.get('sources_succeeded', [])) or 'none'} |",
            f"| Entries seeded | **{d.get('entries_seeded', 0)}** |",
            f"| Duration | {run.bootstrap.duration_s:.1f}s |",
            f"| Verdict | {_md_status(run.bootstrap.passed, run.bootstrap.warning)} |",
            "",
        ]

    # ---- Ingest detail ----
    if run.ingest:
        lines += ["## Phase 2 — Chunk Ingestion", ""]
        d = run.ingest.data
        chunks = d.get("chunks", [])
        lines += [
            "| Chunk | Chars | Duration | Status |",
            "|-------|-------|----------|--------|",
        ]
        for c in chunks:
            icon = _md_status(c.get("passed", False), c.get("warning", False))
            err = c.get("error", "")
            lines.append(
                f"| {c['chunk_id']} | {c['chars']:,} | {c['duration_s']:.2f}s | {icon}{' — ' + err if err else ''} |"
            )
        lines += [
            f"| **Total** | **{d.get('total_chars', 0):,}** | **{run.ingest.duration_s:.1f}s** | |",
            "",
            f"**Throughput:** {d.get('throughput_chars_per_sec', 0):.0f} chars/sec  ",
            f"**Avg per chunk:** {d.get('avg_per_chunk_s', 0):.1f}s  ",
            f"**Verdict:** {_md_status(run.ingest.passed, run.ingest.warning)}  ",
            "",
        ]

    # ---- Wiki audit detail ----
    if run.wiki_audit:
        lines += ["## Phase 3 — Wiki Quality Audit", ""]
        d = run.wiki_audit.data
        by_type = d.get("by_type", {})
        lines += [
            "### Entry Distribution",
            "",
            "| Entry Type | Count |",
            "|------------|-------|",
        ]
        for etype, count in sorted(by_type.items()):
            lines.append(f"| {etype} | {count} |")
        lines += [
            f"| **Total** | **{d.get('total_entries', 0)}** |",
            "",
            "### Character Detection",
            "",
            "| Character | Aliases | Found | Method |",
            "|-----------|---------|-------|--------|",
        ]
        char_hits = d.get("character_hits", [])
        for i, ch in enumerate(char_hits):
            exp = EXPECTED_CHARACTERS[i]
            icon = "✅" if ch["found"] else "❌"
            aliases = ", ".join(exp.get("aliases", []))
            lines.append(f"| {ch['name']} | {aliases} | {icon} | {ch.get('method', '—')} |")
        lines += [
            "",
            f"**Characters found:** {d.get('characters_found', 0)}/{len(EXPECTED_CHARACTERS)}  ",
            f"**Verdict:** {_md_status(run.wiki_audit.passed, run.wiki_audit.warning)}  ",
            "",
        ]

    # ---- Search detail ----
    if run.search:
        lines += ["## Phase 4 — Semantic Search", ""]
        d = run.search.data
        lines += [
            "| Query | Expected Type | Got | Match | Latency |",
            "|-------|--------------|-----|-------|---------|",
        ]
        for t in d.get("queries", []):
            match = "✅" if t.get("type_match") else "⚠️"
            err   = t.get("error", "")
            lines.append(
                f"| {t['query'][:48]} | {t.get('expected_type', '—')} "
                f"| {t.get('top_type', '❌')} | {match} | {t['duration_s']:.3f}s |"
                + (f" ❌ {err}" if err else "")
            )
        lines += [
            "",
            f"**Avg latency:** {d.get('avg_latency_s', 0):.3f}s  ",
            f"**Max latency:** {d.get('max_latency_s', 0):.3f}s  ",
            f"**Type match rate:** {d.get('type_match_rate', '—')}  ",
            f"**Verdict:** {_md_status(run.search.passed, run.search.warning)}  ",
            "",
        ]

    # ---- Lint detail ----
    if run.lint:
        lines += ["## Phase 5 — Lint Pass", ""]
        d = run.lint.data
        gaps = d.get("gaps", [])
        lines += [
            f"| | |",
            f"|---|---|",
            f"| Entries checked | {d.get('entries_checked', 0)} |",
            f"| Gaps detected | {len(gaps)} |",
            f"| Entries enriched | **{d.get('entries_enriched', 0)}** |",
            f"| Duration | {run.lint.duration_s:.1f}s |",
            f"| Verdict | {_md_status(run.lint.passed, run.lint.warning)} |",
            "",
        ]
        if gaps:
            enriched_gaps = [g for g in gaps if g.get("was_enriched")]
            lines += [
                "### Enriched Entries",
                "",
                "| Title | Type | Fields Filled |",
                "|-------|------|---------------|",
            ]
            for g in enriched_gaps[:20]:
                lines.append(
                    f"| {g['title']} | {g['entry_type']} | {', '.join(g.get('missing_fields', []))} |"
                )
            lines.append("")

    # ---- Export detail ----
    if run.export:
        lines += ["## Phase 6 — Markdown Export", ""]
        d = run.export.data
        lines += [
            f"| | |",
            f"|---|---|",
            f"| Output size | {d.get('markdown_chars', 0):,} chars |",
            f"| Lines | {d.get('markdown_lines', 0)} |",
            f"| Duration | {run.export.duration_s:.2f}s |",
            f"| Verdict | {_md_status(run.export.passed)} |",
            "",
        ]

    lines += [
        "---",
        "",
        f"*Report generated by `tests/bookbrain/benchmark.py` — {run.started_at}*",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace):
    run = BenchmarkRun(
        started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        base_url=args.base_url,
        real_book_title=args.real_book,
        real_book_author=args.author,
    )

    t_total = time.monotonic()

    async with httpx.AsyncClient() as client:

        # Health
        _section("Phase 0 │ Health Check")
        run.health = await run_health(client, args.base_url)
        _row("Status",  run.health.detail)
        _row("Verdict", _verdict(run.health))
        if not run.health.passed:
            print()
            print("  ❌ Service is not reachable. Start ai-service and retry.")
            print()
            return run

        # Reset the benchmark book (clean slate)
        print()
        print(f"  Resetting benchmark wiki (book_id={BENCHMARK_BOOK_ID})...")
        await run_reset(client, args.base_url, BENCHMARK_BOOK_ID)

        # Bootstrap
        if not args.skip_bootstrap:
            book_for_bootstrap = args.real_book or MOCK_BOOK_TITLE
            bootstrap_book_id  = "benchmark-bootstrap-001" if args.real_book else BENCHMARK_BOOK_ID
            _section(f"Phase 1 │ Bootstrap — {book_for_bootstrap}")
            run.bootstrap = await run_bootstrap(
                client, args.base_url,
                book_id=bootstrap_book_id,
                book_title=book_for_bootstrap,
                author=args.author,
            )
            _row("Sources succeeded", f"{len(run.bootstrap.data.get('sources_succeeded', []))}/4")
            _row("Entries seeded",    str(run.bootstrap.data.get("entries_seeded", 0)))
            _row("Duration",          f"{run.bootstrap.duration_s:.1f}s")
            _row("Verdict",           _verdict(run.bootstrap))
            # Clean up the real-book scratch space
            if args.real_book:
                await run_reset(client, args.base_url, bootstrap_book_id)

        # Ingest
        _section(f"Phase 2 │ Chunk Ingestion — {MOCK_BOOK_TITLE}")
        run.ingest = await run_ingest(client, args.base_url, BENCHMARK_BOOK_ID)
        _row("Total duration",  f"{run.ingest.duration_s:.1f}s")
        _row("Throughput",      f"{run.ingest.data.get('throughput_chars_per_sec', 0):.0f} chars/sec")
        _row("Verdict",         _verdict(run.ingest))

        # Wiki audit
        _section("Phase 3 │ Wiki Quality Audit")
        run.wiki_audit = await run_wiki_audit(client, args.base_url, BENCHMARK_BOOK_ID)
        d = run.wiki_audit.data
        _row("Total entries",      str(d.get("total_entries", 0)))
        _row("Characters found",   f"{d.get('characters_found', 0)}/{len(EXPECTED_CHARACTERS)}")
        _row("Verdict",            _verdict(run.wiki_audit))

        # Search
        _section("Phase 4 │ Semantic Search")
        run.search = await run_search(client, args.base_url, BENCHMARK_BOOK_ID)
        _row("Avg latency",     f"{run.search.data.get('avg_latency_s', 0):.3f}s")
        _row("Type match rate", run.search.data.get("type_match_rate", "—"))
        _row("Verdict",         _verdict(run.search))

        # Lint
        if not args.skip_lint:
            _section("Phase 5 │ Lint Pass")
            run.lint = await run_lint(client, args.base_url, BENCHMARK_BOOK_ID)
            _row("Entries checked",  str(run.lint.data.get("entries_checked", 0)))
            _row("Entries enriched", str(run.lint.data.get("entries_enriched", 0)))
            _row("Duration",         f"{run.lint.duration_s:.1f}s")
            _row("Verdict",          _verdict(run.lint))

        # Export
        _section("Phase 6 │ Markdown Export")
        run.export = await run_export(client, args.base_url, BENCHMARK_BOOK_ID)
        _row("Output size", run.export.detail)
        _row("Verdict",     _verdict(run.export))

    run.total_duration_s = time.monotonic() - t_total

    print_report(run)
    write_markdown_report(run)

    return run


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BookBrain Benchmark")
    p.add_argument(
        "--base-url", default="http://localhost:8000/api/v1",
        help="ai-service base URL (default: http://localhost:8000/api/v1)",
    )
    p.add_argument(
        "--real-book", default=None, metavar="TITLE",
        help='Optional real book title for bootstrap test (e.g. "Crime and Punishment")',
    )
    p.add_argument(
        "--author", default=None, metavar="AUTHOR",
        help='Author name for --real-book (e.g. "Fyodor Dostoevsky")',
    )
    p.add_argument(
        "--skip-bootstrap", action="store_true",
        help="Skip the bootstrap phase (faster iteration)",
    )
    p.add_argument(
        "--skip-lint", action="store_true",
        help="Skip the lint phase (saves ~30-60s)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
