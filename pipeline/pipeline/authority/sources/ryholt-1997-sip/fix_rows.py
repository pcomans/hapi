"""Apply schema-audit corrections to Ryholt 1997 SIP's reconciled.jsonl.

Issue #177 audit (Tier 2, 6 P1) — strict-all-6-P1 fix per the
established policy from issue #176 (PR #188). Ryholt's flat schema is
too thin for a fragmentary-evidence corpus where individual kings are
attested by partial titularies (only a Horus name, only a prenomen,
only an Abydos King-List entry). Structural facts get smuggled back
in via:
- compound `ryholt_id` (`N.*`, `Abyd.*`, `17.a`)
- in-string glyph annotations (`(?)`, `(syllabic)`, `[...]`, `var.`,
  `(III)`)
- silent-default nulls (`date_bce_start = None` for both "no date"
  and "single-cell entry")

This module migrates each to its own typed field per Rule-3
(deterministic enforcement over convention) and Rule-4 (single source
of truth).

Run:
    cd pipeline && uv run python pipeline/authority/sources/ryholt-1997-sip/fix_rows.py

Idempotent: re-running produces byte-identical reconciled.jsonl.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

SOURCE_DIR = Path(__file__).parent
RECONCILED = SOURCE_DIR / "reconciled.jsonl"


# === SCHEMA_FIELD_DEFAULTS ===================================================
SCHEMA_FIELD_DEFAULTS: dict[str, object] = {
    # Issue #177 Shape A: distinguishes Abydos Dynasty (real dynasty,
    # 8 rows, prefix `Abyd.*`) from numbered dynasties from truly
    # unattributed kings (23 rows, prefix `N|P|H|D|G.*`). Replaces
    # the convention of inferring from `dynasty is None` + ryholt_id
    # prefix scrutiny.
    "dynasty_label": None,
    # Issue #177 Shape A + H: typed enum for the prefix's meaning.
    # `king` = canonical attested king (numbered dynasty rows),
    # `abydos` = Abydos King-List entry (Abyd.* prefix),
    # `nomen_only` / `prenomen_only` / `horus_only` / `nebty_only` /
    # `golden_horus_only` = unattributed king known only by one
    # name-type (N/P/H/Nb/G prefix per Ryholt's catalogue convention).
    "attestation_class": None,
    # Issue #177 Shape J: typed flag for the 23 unattributed-king rows.
    # True iff prefix is N/P/H/D/G; False otherwise. Replaces the
    # convention `dynasty is None and not ryholt_id.startswith('Abyd.')`.
    "is_unattributed": False,
    # Issue #177 Shape J: typed flag for the 8 Abydos Dynasty rows.
    "is_abydos_dynasty": False,
    # Issue #177 Shape J: typed flag for `(?)` uncertainty marker
    # in nomen / prenomen. 3 rows in current corpus.
    "is_uncertain_attribution": False,
    # Issue #177 Shape J: typed flag for any name field containing
    # `[...]` / `[..]` lacuna markers. ~32 rows.
    "is_lacunose": False,
    # Issue #177 Shape J: typed flag for nomen-transliterated rows
    # in Ryholt's syllabic orthography (the `(syllabic)` marker).
    # 23 rows in current corpus.
    "is_syllabic_nomen": False,
    # Issue #177 Shape J: typed integer for Roman-numeral homonym
    # disambiguator (e.g. Sewadjkare (I), Awibre (II)). 4 rows.
    "homonym_index": None,
    # Issue #177 Shape D: enum for the date-attestation pattern.
    # Replaces the silent-null convention where (start=None, end=None)
    # could mean "no date" OR "single-cell entry that Ryholt couldn't
    # reconcile to a range."
    # Values: `"both"`, `"start_only"`, `"end_only"`, `"none"`.
    "date_attestation": "none",
    # Issue #177 Shape I: list of nomen-transliterated variants when
    # Ryholt prints `<canonical>, var. <alt>` (3 rows: 13.22, 14.2, 14.4).
    "nomen_transliterated_variants": [],
}


def backfill_schema_fields(rows: list[dict]) -> list[str]:
    """Add SCHEMA_FIELD_DEFAULTS keys to every row that's missing them.
    Idempotent. Defensive deepcopy."""
    log_lines: list[str] = []
    for row in rows:
        added: list[str] = []
        for field, default in SCHEMA_FIELD_DEFAULTS.items():
            if field not in row:
                row[field] = copy.deepcopy(default)
                added.append(field)
        if added:
            log_lines.append(f"  {row['ryholt_id']}: backfilled {sorted(added)!r}")
    return log_lines


# === Deterministic per-row computation ======================================
#
# These migrations are deterministic functions of the existing row
# fields (ryholt_id prefix, name field contents, date null pattern).
# Running them multiple times produces the same output.

_PREFIX_TO_ATTESTATION_CLASS = {
    "N": "nomen_only",
    "P": "prenomen_only",
    "H": "horus_only",
    "Nb": "nebty_only",
    "G": "golden_horus_only",
    "D": "djed_only",  # 1 row; Ryholt doesn't enumerate this in the README
                       # but the prefix `D` exists in the corpus (likely a
                       # Djed-pillar variant per Ryholt's catalogue convention).
                       # Phase-A consumer may want to treat as `unknown`.
    "Abyd": "abydos",
}


def _ryholt_id_prefix(rid: str) -> str | None:
    """Extract the alphabetic prefix from a ryholt_id (e.g. `N.5` → `N`,
    `Abyd.3` → `Abyd`, `13.7` → None for numbered-dynasty rows)."""
    m = re.match(r"^([A-Za-z]+)\.", rid)
    return m.group(1) if m else None


def _compute_dynasty_label(row: dict) -> str | None:
    """`"13" .. "17"` for numbered dynasties; `"Abydos"` for Abyd rows;
    `None` for truly-unattributed N/P/H/D/G rows."""
    if row.get("dynasty"):
        return str(row["dynasty"])
    prefix = _ryholt_id_prefix(row["ryholt_id"])
    if prefix == "Abyd":
        return "Abydos"
    return None


def _compute_attestation_class(row: dict) -> str:
    """Maps from ryholt_id prefix to the typed enum. Numbered dynasties
    (no prefix) are `"king"`."""
    prefix = _ryholt_id_prefix(row["ryholt_id"])
    if prefix is None:
        return "king"
    return _PREFIX_TO_ATTESTATION_CLASS.get(prefix, "unknown")


def _compute_date_attestation(row: dict) -> str:
    """Match the row's date-bound null pattern to the enum."""
    s, e = row.get("date_bce_start"), row.get("date_bce_end")
    if s is not None and e is not None:
        return "both"
    if s is not None:
        return "start_only"
    if e is not None:
        return "end_only"
    return "none"


def apply_deterministic_passes(rows: list[dict]) -> list[str]:
    """Compute typed fields from existing values. Idempotent (same input
    → same output). Pure derivation; no scholarly judgment.
    """
    log_lines: list[str] = []
    for row in rows:
        new_label = _compute_dynasty_label(row)
        if row["dynasty_label"] != new_label:
            row["dynasty_label"] = new_label
            log_lines.append(f"  {row['ryholt_id']}: dynasty_label → {new_label!r}")
        new_class = _compute_attestation_class(row)
        if row["attestation_class"] != new_class:
            row["attestation_class"] = new_class
            log_lines.append(f"  {row['ryholt_id']}: attestation_class → {new_class!r}")
        new_unattributed = _ryholt_id_prefix(row["ryholt_id"]) in {"N", "P", "H", "D", "G", "Nb"}
        if row["is_unattributed"] != new_unattributed:
            row["is_unattributed"] = new_unattributed
            log_lines.append(f"  {row['ryholt_id']}: is_unattributed → {new_unattributed}")
        new_abydos = _ryholt_id_prefix(row["ryholt_id"]) == "Abyd"
        if row["is_abydos_dynasty"] != new_abydos:
            row["is_abydos_dynasty"] = new_abydos
            log_lines.append(f"  {row['ryholt_id']}: is_abydos_dynasty → {new_abydos}")
        new_date_att = _compute_date_attestation(row)
        if row["date_attestation"] != new_date_att:
            row["date_attestation"] = new_date_att
            log_lines.append(f"  {row['ryholt_id']}: date_attestation → {new_date_att!r}")
    return log_lines


# === In-string glyph migrations =============================================
#
# Strip `(?)`, `(syllabic)`, `(I)/(II)/(III)` from name strings;
# promote each to its typed flag. Lacuna `[...]` markers are KEPT
# in the name string (they show position of missing characters)
# but the row also gets `is_lacunose=True`.

_PAREN_QUESTION_RE = re.compile(r"\s*\(\?\)\s*$")
_PAREN_SYLLABIC_RE = re.compile(r"\s*\(syllabic\)\s*$")
_PAREN_ROMAN_RE = re.compile(r"\s*\(([IVX]+)\)\s*$")
_VAR_SPLIT_RE = re.compile(r",\s*var\.\s*")
_LACUNA_RE = re.compile(r"\[\.\.+\]")
_ROMAN_TO_INT = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}


def apply_glyph_migrations(rows: list[dict]) -> list[str]:
    """Strip in-string uncertainty / syllabic / homonym glyphs from
    name fields; promote each to its typed flag. Idempotent."""
    log_lines: list[str] = []
    for row in rows:
        rid = row["ryholt_id"]
        # `(?)` in nomen / prenomen → is_uncertain_attribution
        for f in ("nomen", "prenomen"):
            v = row.get(f)
            if v and _PAREN_QUESTION_RE.search(v):
                row[f] = _PAREN_QUESTION_RE.sub("", v)
                if not row["is_uncertain_attribution"]:
                    row["is_uncertain_attribution"] = True
                    log_lines.append(f"  {rid}: stripped `(?)` from {f}; is_uncertain_attribution=True")
        # `(syllabic)` (or `(syllabic?)`, `(syllabic)⁽¹⁾`, `(syllabic),
        # not preceded by ...`) in nomen_transliterated → is_syllabic_nomen.
        # Set the flag whenever any `(syllabic` substring occurs;
        # only strip the cleanly-trailing `(syllabic)` form to avoid
        # destroying prose annotations like the L15.3 trailing
        # `, not preceded by *sꜣ-rꜥ` qualifier.
        v = row.get("nomen_transliterated")
        if v and "(syllabic" in v.lower():
            if not row["is_syllabic_nomen"]:
                row["is_syllabic_nomen"] = True
                log_lines.append(f"  {rid}: detected `(syllabic` in nomen_transliterated; is_syllabic_nomen=True")
            if _PAREN_SYLLABIC_RE.search(v):
                row["nomen_transliterated"] = _PAREN_SYLLABIC_RE.sub("", v)
                log_lines.append(f"  {rid}: stripped trailing `(syllabic)` from nomen_transliterated")
        # `(I)/(II)/(III)` in nomen → homonym_index
        v = row.get("nomen")
        if v:
            m = _PAREN_ROMAN_RE.search(v)
            if m:
                row["nomen"] = _PAREN_ROMAN_RE.sub("", v)
                idx = _ROMAN_TO_INT.get(m.group(1))
                if row["homonym_index"] != idx:
                    row["homonym_index"] = idx
                    log_lines.append(f"  {rid}: stripped `({m.group(1)})` from nomen; homonym_index={idx}")
        # `, var. <alt>` in nomen_transliterated → nomen_transliterated_variants
        v = row.get("nomen_transliterated")
        if v and ", var." in v:
            parts = _VAR_SPLIT_RE.split(v, 1)
            canonical = parts[0].strip()
            variant = parts[1].strip() if len(parts) > 1 else ""
            row["nomen_transliterated"] = canonical
            if variant and variant not in row["nomen_transliterated_variants"]:
                row["nomen_transliterated_variants"] = sorted({*row["nomen_transliterated_variants"], variant})
                log_lines.append(f"  {rid}: split `var.` from nomen_transliterated; variants={row['nomen_transliterated_variants']}")
        # `[...]` lacuna → is_lacunose flag (keep marker in string)
        is_lac = any(
            _LACUNA_RE.search(row.get(f) or "")
            for f in (
                "nomen", "nomen_transliterated",
                "prenomen", "prenomen_transliterated",
                "horus_name_transliterated", "nebty_name_transliterated",
                "golden_horus_name_transliterated",
            )
        )
        if is_lac and not row["is_lacunose"]:
            row["is_lacunose"] = True
            log_lines.append(f"  {rid}: contains [...] lacuna; is_lacunose=True")
    return log_lines


def main() -> None:
    rows = [
        json.loads(line)
        for line in RECONCILED.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    backfill_log = backfill_schema_fields(rows)
    glyph_log = apply_glyph_migrations(rows)
    deterministic_log = apply_deterministic_passes(rows)
    RECONCILED.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n",
        encoding="utf-8",
    )
    total = len(backfill_log) + len(glyph_log) + len(deterministic_log)
    print(
        f"Backfilled {len(backfill_log)} fields; "
        f"applied {len(glyph_log)} glyph migrations + "
        f"{len(deterministic_log)} deterministic passes "
        f"({total} log lines this run)."
    )
    # Walk to repo root via .git marker for stable display path.
    repo_root = RECONCILED
    for _ in range(10):
        repo_root = repo_root.parent
        if (repo_root / ".git").exists():
            break
    try:
        rel = RECONCILED.relative_to(repo_root)
    except ValueError:
        rel = RECONCILED
    print(f"Updated {rel}")


if __name__ == "__main__":
    main()
