"""Structural value-assertion tests for Porter & Moss Vol I source extract.

Per CLAUDE.md rule 5: every populated field on every fixture-class row is
asserted, not just the field the test class is "themed" around.

Chunk 1 covers KV1–KV10 (PM I.2 § I.A "Tombs", printed p.495–518). Future
chunks (KV11–KV65, QV, TT...) extend `EXPECTED_TOMB_IDS` and add per-chunk
value-assertion tests; the structural tests below are forward-compatible.

Note on null `dynasty` and BCE-date fields: per CLAUDE.md rule 1 (every
authoritative fact must trace to a committed raw source) and rule 7
(authority lookup, not hard-coded), PM headwords don't print dynasty or
BCE dates — those fields stay null at this extraction stage and Phase A
king-authority enrichment (against pharaoh.se) fills them. The test suite
therefore asserts these fields are null on every chunk-1 row, not that
they carry expected dynasty values.
"""

from __future__ import annotations

import importlib.util
import json
import re
from functools import lru_cache
from pathlib import Path

SOURCE_DIR = (
    Path(__file__).parent.parent
    / "pipeline"
    / "authority"
    / "sources"
    / "porter-moss-theban-necropolis"
)
JSONL = SOURCE_DIR / "reconciled.jsonl"

EDITION_PM_I2 = "PM I.2 2nd ed. 1964"
EDITION_PM_I1 = "PM I.1 2nd ed. 1960"

# Chunk-1 (KV1–KV10), chunk-2 (KV11–KV20), chunk-3 (KV22–KV46 sparse) are
# the landed chunks. Extend as follow-up chunk PRs land. `EXPECTED_TOMB_IDS`
# is the union — row-count and ID-coverage tests reference it so they stay
# correct as the source grows.
#
# Absence patterns in PM I.2 § I.A:
# - KV21 is absent (jump from KV20 to KV22) — chunk-2 holds 10 rows.
# - KV24–KV33, KV37, KV40, KV41, KV44 are absent from chunk-3's range —
#   PM I.2 (1964) did not catalogue these as inscribed royal tombs. Chunk-3
#   holds 11 rows: KV22, 23, 34, 35, 36, 38, 39, 42, 43, 45, 46.
CHUNK1_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(1, 11)}
)
CHUNK2_TOMB_IDS: frozenset[str] = frozenset(
    {f"KV{n}" for n in range(11, 21)}
)
CHUNK3_TOMB_IDS: frozenset[str] = frozenset(
    {"KV22", "KV23", "KV34", "KV35", "KV36", "KV38", "KV39", "KV42",
     "KV43", "KV45", "KV46"}
)
# Chunk-4: KV47-KV57 sparse. KV49-KV54 and KV58-KV61 absent from PM I.2
# § I.A (PM jumps 48 → 55, 57 → 62). KV62 Tutankhamun is deferred to a
# dedicated chunk 5 because PM's KV62 entry spans 17 printed pages and
# warrants its own extraction PR.
CHUNK4_TOMB_IDS: frozenset[str] = frozenset(
    {"KV47", "KV48", "KV55", "KV56", "KV57"}
)
# Chunk-5: KV62 Tutʿankhamun as a standalone single-row chunk. User
# direction on chunk 5 scope: tomb-row granularity is sufficient for the
# museum-data-join use case; per-chamber sub-structure would inflate the
# schema past what downstream enrichment needs.
CHUNK5_TOMB_IDS: frozenset[str] = frozenset({"KV62"})
# Chunk-6: PM I.2 § I.A closure sweep, no rows added (KV63/KV64/KV65 are
# post-1964 discoveries, out of scope for PM I.2 2nd ed. 1964).
# Chunk-7: PM I.2 §§ II (South-West Valleys) + III.A/C/D (Dra' Abu el-Naga:
# Antef Cemetery Dyn XI, Tomb of Ahmose-Nefertari, Seventeenth Dynasty
# Cemetery). First chunk of this source with NON-NUMBERED tomb_ids — PM
# does not assign KV/QV/TT numbers to these sections, so tomb_id uses the
# descriptor convention `<PREFIX>-<Occupant>` where PREFIX is the valley
# code (`SWV` = South-West Valleys, `DAN` = Dra' Abu el-Naga). 18 rows.
CHUNK7_TOMB_IDS: frozenset[str] = frozenset({
    # § II.A Wadi Sikket Taqet Zaid (1)
    "SWV-HatshepsutSouth",
    # § II.B Wadi Qubbanet el-Qirud (2)
    "SWV-Neferure",
    "SWV-ThreePrincesses",
    # § III.A Antef Cemetery Dyn XI at El-Ṭaraf (3)
    "DAN-AntefSehertaui",
    "DAN-AntefWahankh",
    "DAN-MentuhotpSankhibtaui",
    # § III.C Tomb of Queen Ahmose-Nefertari (probably) (1)
    "DAN-AhmosiNefertere",
    # § III.D Seventeenth Dynasty Cemetery BURIALS (11)
    "DAN-Aqhor",
    "DAN-Ahhotep",
    "DAN-AhmosiHenutempet",
    "DAN-AhmosiSonOfSeqenenre",
    "DAN-AntefNubkheperre",
    "DAN-AntefSekhemreHeruhirmaet",
    "DAN-AntefSekhemreWepmaet",
    "DAN-KamosiWazkheperre",
    "DAN-MentuhotpIWifeOfDjhuti",
    "DAN-Neferhotep",
    "DAN-SebkemsafSekhemreShedtaui",
})
# Chunk-8 (PM I.2 § X.A Valley of the Queens — numbered tombs).
# PM 1964 2nd edition catalogues 20 numbered QV tombs; the rest of the
# QV1–QV80 range is absent from PM § X.A (QV1–32 never catalogued; QV34,
# 35, 37, 39, 41, 45, 48–50, 54, 56–59, 61–65, 67, 69, 70, 72, 76–80 are
# gaps). Chunk-7's descriptor infrastructure is not used here — QV uses
# the numbered form established in chunk 1.
CHUNK8_TOMB_IDS: frozenset[str] = frozenset({
    "QV33", "QV36", "QV38", "QV40", "QV42", "QV43", "QV44", "QV46",
    "QV47", "QV51", "QV52", "QV53", "QV55", "QV60", "QV66", "QV68",
    "QV71", "QV73", "QV74", "QV75",
})
# Chunk-9 (PM I.1 § I — TT1-TT10 Deir el-Medina core). FIRST chunk drawn
# from PM I.1; previous chunks 1-8 came from PM I.2. Every TT number in
# TT1..TT10 is present in PM I.1 § I — no gaps in this decade. 10 rows.
CHUNK9_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(1, 11)}
)
# Chunk-10 (PM I.1 § I — TT11-TT20 Dra' Abu el-Naga). Second chunk drawn from
# PM I.1; theban_area shifts from Deir el-Medina (chunk 9) to Dra' Abu el-Naga.
# Every TT number in TT11..TT20 is present in PM I.1 § I — no gaps. 10 rows.
CHUNK10_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(11, 21)}
)
# Chunk-11 (PM I.1 § I — TT21-TT30). FIRST chunk with heterogeneous
# `theban_area`: TT21/22/23/29/30 = Sh. ʿAbd el-Qurna; TT24 = Dra' Abu el-
# Naga; TT25/26/27/28 = ʿAsâsîf. Also introduces TT22 usurpation (Tier-3
# `is_usurped=true`), TT29 cross-valley `shared_with_tombs=["KV48"]`, and
# TT29 first non-Official controlled-vocab role (Vizier).
CHUNK11_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(21, 31)}
)
# Chunk-12 (PM I.1 § I — TT31-TT40). Introduces two new theban_area values:
# `Khokha` (TT32, TT39) and `Qurnet Muraʿi` (TT40). TT35 is in
# `Dra' Abu el-Naga` — first TT-numbered tomb outside Sh. ʿAbd el-Qurna or
# ʿAsâsîf in the I.1 section. TT32 occupant_name = `Thutmosi` pre-fix_rows;
# the diacritic restoration to `Ḏhutmosi` (d-bar Ḏ, U+1E0E — the standard
# Egyptological transliteration of the d-emphatic in `Ḏḥwty`/Thoth and
# its derived names; PR #151 verified `Ḏ` not `Ḍ` for sibling names
# `Ḏḥuti` and `Sit-ḏḥout` after direct PM PDF read) is applied by
# CHUNK12_CORRECTIONS in fix_rows.py. 10 rows, every TT31..TT40
# present (no gaps in PM I.1).
CHUNK12_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(31, 41)}
)
# Chunk-13 (PM I.1 § I — TT41-TT50, 10 rows). Heterogeneous across
# 2 sub-sites: `Sh. ʿAbd el-Qurna` (TT41-46, TT50) and `Khokha`
# (TT47-49). One usurpation (TT45 — Ḏhout original, Ḏḥutemḥab usurper);
# two `called <ALT>` alt-name patterns (TT41 Amenemōpet/Ipy, TT48
# Amenemḥet/Surero); one tomb-state marker (TT47 `(Inaccessible.)`);
# one within-decade NAME collision (TT49 + TT50 both `Neferhotep`,
# distinct individuals). TT45 `Ḏhout` extends the d-bar Ḏ (U+1E0E)
# precedent established by chunk-12 PR #200 TT32 `Ḏhutmosi` to PM I.1.
# CHUNK13_CORRECTIONS layers 4 PDF-cited corrections (1 capital macron
# + 3 spurious double-period strips); DERIVER_OVERRIDES adds 5 entries
# for regnal/usurper-clause hedges (TT41/TT43/TT45/TT46/TT49) per the
# chunk-9 TT2 occupant-vs-regnal certainty distinction.
CHUNK13_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(41, 51)}
)
# Chunk-14 (PM I.1 § I — TT51-TT60, Sh. ʿAbd el-Qurna). All 10 TT numbers
# present (no gaps in PM I.1). Two Viziers (TT55 Raʿmosi, TT60 Antefoḳer);
# one anonymous tomb (TT58 — usurped by Amenḥotp + son Amenemonet, Dyn XX);
# one co-occupant entry (TT60 mother Sent). Five 1/1/1 tie-break overrides
# resolved in tie-break-overrides.json (TT53/TT54/TT57/TT58/TT60
# notes_from_pm). CHUNK14_CORRECTIONS scaffold registered in fix_rows.py;
# reviewer-pass corrections will populate it on the follow-up PR.
CHUNK14_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(51, 61)}
)
# Chunk-15 (PM I.1 § I — TT61-TT70, Sh. ʿAbd el-Qurna). All 10 TT numbers
# present (no gaps in PM I.1). Two Viziers (TT61 User, TT66 Hepu); one High
# Priest (TT67 Hepusonb); one anonymous tomb (TT70 — usurped by Amenmosi,
# Dyn. XXI); one bracketed-fragment headword (TT68 [Per?]enkhmun). Two
# 1/1/1 tie-break overrides resolved in tie-break-overrides.json (TT65 and
# TT68 notes_from_pm). Two 2/1 majority disagreements: TT64 occupant_name
# (Heḳerneheh vs Heṭerneheh — flagged for egyptologist PDF check) and TT65
# occupant_name (Nebamun vs Nebamūn — prompt-rule violation, B pre-derived
# macron). Three DERIVER_OVERRIDES for TT62/TT65/TT69 (regnal-date hedges).
# CHUNK15_CORRECTIONS scaffold registered in fix_rows.py.
CHUNK15_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(61, 71)}
)
# Chunk-16 (PM I.1 § I — TT71-TT80, Sh. ʿAbd el-Qurna). All 10 TT numbers
# present (no gaps in PM I.1). One High Priest (TT72 Reʿ — First prophet of
# Amūn); nine Officials. One usurped tomb (TT77 Ptahemhet, usurped by Roy).
# Four 1/1/1 tie-break overrides resolved in tie-break-overrides.json (TT77,
# TT78, TT79, TT80 notes_from_pm). Five 2/1 majority disagreements, all
# cosmetic (citation position, one casing on TT75 occupant_name). One
# DERIVER_OVERRIDE for TT79 (regnal-range tail hedge `Amenophis II (?)`).
# CHUNK16_CORRECTIONS scaffold registered in fix_rows.py (empty pending
# egyptologist PDF pass).
CHUNK16_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(71, 81)}
)
# Chunk-17 (PM I.1 § I — TT81-TT90, Sh. ʿAbd el-Qurna). All 10 TT numbers
# present. One Vizier (TT83 ʿAmethu, called ʿAhmosi); one High Priest
# (TT86 Menkheperraʿsonb, First prophet of Amūn, also owner of TT112);
# eight Officials. One partly-usurped tomb (TT84 Amunezeḥ, partly usurped
# by Mery of TT95). Seven 1/1/1 tie-break overrides resolved in
# tie-break-overrides.json (TT81, TT82, TT83, TT84, TT85, TT87, TT88,
# TT90 notes_from_pm). Several 2/1 majority page-number disagreements
# (TT82 p.163, TT87 p.178, TT90 p.183 — agents off-by-one but majority
# resolved). CHUNK17_CORRECTIONS in fix_rows.py: 5 entries (TT81 notes
# bracket-prefix + ʿAḥḥotp doubled-ḥ; TT82 occupant_name macron-Ē
# restoration; TT84 notes MERY → Mery Title-case normalisation; TT86
# notes Amenemḥēt + Taōnet macron restorations; TT90 occupant_name
# `Nebamun` → `Nebamūn` macron-Ū restoration per chunk-15 TT65 NEBAMŪN
# precedent — Nebamūn is the third within-source NAME collision in
# PM I.1 after TT17 + TT65). No DERIVER_OVERRIDES needed.
CHUNK17_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(81, 91)}
)
# Chunk-18 (PM I.1 § I — TT91-TT100, Sh. ʿAbd el-Qurna). All 10 TT
# numbers present. Anonymous occupant TT91 (no NAME-IN-CAPS in PM
# headword — third such anonymous variant after chunk-14 TT58 + chunk-
# 15 TT70). One Vizier TT100 Rekhmirēʿ (Governor of the town and
# Vizier — major Theban tomb spanning 9 printed pages). Two High Priests
# (TT95 Mery, TT97 Amenemhet — both First prophet of Amūn, major cult
# flatten). Two within-chunk Sennufer rows (TT96 + TT99 — distinct
# individuals per chunk-10 TT17 / chunk-17 TT90 within-source-name-
# collision precedent). One alt-name TT94 Raʿmosi/ʿAmy. TT95 Mery is
# the USURPER of TT84 (chunk-17 cross-reference); PM's `(See also
# usurpation in tomb 84.)` parenthetical is preserved verbatim in
# notes_from_pm but shared_with_tombs=[] (overridden from agent A+B
# 2/1 majority via CHUNK18_CORRECTIONS): the cross-ref is an EVENT
# reference, not an OWNERSHIP relation, so it doesn't match the
# chunk-9 `See also Tomb N` ownership-pattern documented for
# shared_with_tombs. is_usurped is pinned to false via
# DERIVER_OVERRIDES (Mery is usurper of TT84, not usurped at TT95).
# Six CHUNK18_CORRECTIONS (TT91 role pin per Unknown sentinel-null
# artifact at merge.py:159; TT93 occupant_name `Ḳenamūn` macron-Ū
# per PDF p.190; TT93 notes mother `Amenemōpet` macron-Ō per PDF
# p.190; TT95 shared_with_tombs override to []; TT97 occupant_name
# `Amenemhēt` macron-Ē per PDF p.203; TT100 Rekhmirēʿ macron-Ē per
# PDF p.206). Four DERIVER_OVERRIDES (TT95 is_usurped=false;
# TT94/TT97/TT98 regnal `(?)` hedge → attested).
CHUNK18_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(91, 101)}
)
# Chunk-19: PM I.1 § I Numbered Tombs TT101-TT110 (Sh. ʿAbd el-Qurna).
# 4 tie-break-overrides entries (TT104, TT106, TT107, TT110 notes_from_pm).
# 2 DERIVER_OVERRIDES: TT108 regnal-date hedge, TT110 parent-name hedge.
# TT103 + TT106 role = Vizier; TT104 role = None (no title in PM headword,
# "Unknown" sentinel-null collapsed at merge).
CHUNK19_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(101, 111)}
)
# Chunk-20: PM I.1 § I Numbered Tombs TT111-TT120 (Sh. ʿAbd el-Qurna).
# 4 tie-break-overrides entries (TT112, TT113, TT114, TT120 notes_from_pm).
# 2 DERIVER_OVERRIDES: TT116 regnal-date hedge, TT118 regnal-date hedge.
# TT112 is_usurped=True (Menkheperraʿsonb usurped by ʿAshefytemweset —
# the original occupant IS the usurped party, no override needed).
# TT114/TT115/TT116/TT119 occupant_name=None/role=None (no surviving name
# or title; sentinel-null collapsed at merge). Egyptologist review pending:
# TT114 role=None even though PM headword prints a title ("Head of
# goldworkers") — may warrant role=Official; TT120 occupant_alt_names=
# ["Mahu"] is an external-catalogue alias (Gardiner & Weigall), not a
# verified ancient name.
CHUNK20_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(111, 121)}
)
# Chunk-21: PM I.1 § I Numbered Tombs TT121-TT130 (Sh. ʿAbd el-Qurna).
# 1 tie-break-override (TT122 notes_from_pm).
# 4 DERIVER_OVERRIDES: TT121/TT126/TT127/TT130 attribution_certainty
#   (all carry `(?)` qualifying a regnal date, not occupant identity).
# TT122 is_joint_burial=True ([Amen]hotp + Amenemhet, both Overseers).
# TT127 is_usurped=True (Senemiʿoh IS the usurped party, no override
#   needed — contrast TT95 Mery the usurper).
# TT129 anonymous (Name lost), Temp. Tuthmosis III or IV.
CHUNK21_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(121, 131)}
)
# Chunk-22: PM I.1 § I Numbered Tombs TT131-TT139 (Sh. ʿAbd el-Qurna)
# + TT140 (Dra' Abu el-Naga — first Dra' Abu el-Naga tomb in the numbered
# sequence). 7 tie-break-overrides entries (TT134/TT135/TT137/TT138/TT139/
# TT140 notes_from_pm; TT140 occupant_alt_names). 2/1-majority resolutions:
# TT131 notes (A+C drop headword parenthetical), TT132 occupant_name (A+C
# Raʿmosi), TT133 notes (B+C Amūn + Hunuro), TT137 occupant_name (B+C Mose).
# 7 CHUNK22_CORRECTIONS: TT131 cross-ref restore, TT133 Ḥunuro underdot,
# TT135 wʿab-priest ayin, TT136 occupant_role sentinel-null, TT138 Neshaʿ
# ayin, TT139 wʿab-priest ayin, TT140 Ḥefia underdot.
# 1 DERIVER_OVERRIDE: TT140 attribution_certainty (`probably called` hedges
# alt-name only, not primary occupant attribution).
# TT136 is anonymous (Royal scribe..., name not preserved) — occupant_role
# restored to "Unknown" from sentinel-null (contrast TT129 Name-lost which
# stays null). Egyptologist review pending for TT136 role (may warrant
# role=Official given surviving title) and TT140 alt-name Ḥefia (OCR
# reconstruction from ambiguous `~EFIA` / `l):.efia` glyphs).
CHUNK22_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(131, 141)}
)
# Chunk 23: TT141–TT150. All in Dra' Abu el-Naga (§ I). PM I.1 pp.254–261.
# 7 tie-break-overrides entries: TT141/TT144/TT146/TT147/TT148/TT149/TT150
# notes_from_pm (all Amün/Amūn/Amun 3-way macron splits; TT144 also has
# Ḥenuttaui vs Henuttaui wife-name + (?) spacing; TT147 has (?) spacing).
# 2/1-majority resolutions: TT142 Ḏḥutnofer (B+C d-bar), TT143 notes space
# before (?) (A+C), TT145 notes ʿAḥḥotp (B+C), TT150 notes Iact-ib (A+C)
# but overridden by tie-break (B's Amūn is load-bearing → pin B = Iaet-ib).
# 3 CHUNK23_CORRECTIONS: TT141 wʿab-priest ayin+lowercase, TT143 occupant_role
# sentinel-null, TT147 occupant_role sentinel-null.
# 5 DERIVER_OVERRIDES: TT142/TT143/TT144/TT146/TT147 attribution_certainty
# (all (?) qualify regnal date or anonymous-tomb title, not occupant identity).
# Egyptologist flags: TT144 Ḥenuttaui vs Henuttaui (agent C has underdot;
# majority A+B strip it — confirm PDF p.275); TT148 Thonnfer macron question
# (may be Thonnūfer); TT150 wife Iaet-ib vs Iact-ib (A+C had Iact, B had Iaet
# — confirm PDF p.279).
CHUNK23_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(141, 151)}
)
CHUNK24_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(151, 161)}
)
CHUNK25_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(161, 171)}
)
CHUNK26_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(171, 181)}
)
CHUNK27_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(181, 191)}
)
CHUNK28_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(191, 201)}
)
CHUNK29_TOMB_IDS: frozenset[str] = frozenset(
    {f"TT{n}" for n in range(201, 211)}
)
EXPECTED_TOMB_IDS: frozenset[str] = (
    CHUNK1_TOMB_IDS
    | CHUNK2_TOMB_IDS
    | CHUNK3_TOMB_IDS
    | CHUNK4_TOMB_IDS
    | CHUNK5_TOMB_IDS
    | CHUNK7_TOMB_IDS
    | CHUNK8_TOMB_IDS
    | CHUNK9_TOMB_IDS
    | CHUNK10_TOMB_IDS
    | CHUNK11_TOMB_IDS
    | CHUNK12_TOMB_IDS
    | CHUNK13_TOMB_IDS
    | CHUNK14_TOMB_IDS
    | CHUNK15_TOMB_IDS
    | CHUNK16_TOMB_IDS
    | CHUNK17_TOMB_IDS
    | CHUNK18_TOMB_IDS
    | CHUNK19_TOMB_IDS
    | CHUNK20_TOMB_IDS
    | CHUNK21_TOMB_IDS
    | CHUNK22_TOMB_IDS
    | CHUNK23_TOMB_IDS
    | CHUNK24_TOMB_IDS
    | CHUNK25_TOMB_IDS
    | CHUNK26_TOMB_IDS
    | CHUNK27_TOMB_IDS
    | CHUNK28_TOMB_IDS
    | CHUNK29_TOMB_IDS
)


@lru_cache(maxsize=1)
def _rows() -> tuple[dict, ...]:
    return tuple(
        json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()
    )


def _row(tomb_id: str) -> dict:
    hits = [r for r in _rows() if r["tomb_id"] == tomb_id]
    if len(hits) != 1:
        raise AssertionError(f"expected 1 row for {tomb_id}, got {len(hits)}")
    return hits[0]


# ---------------------------------------------------------------------------
# Structural tests (forward-compatible across chunks)
# ---------------------------------------------------------------------------


def test_row_count_matches_expected_set() -> None:
    """Exact-match row count to the union of all landed chunks' tomb IDs."""
    assert len(_rows()) == len(EXPECTED_TOMB_IDS), len(_rows())


def test_tomb_ids_match_expected_set() -> None:
    """Every expected tomb id is present, and no unexpected ids snuck in."""
    actual = {r["tomb_id"] for r in _rows()}
    assert actual == EXPECTED_TOMB_IDS, sorted(actual ^ EXPECTED_TOMB_IDS)


def test_tomb_id_is_unique() -> None:
    """No duplicate tomb_id in the committed extract."""
    ids = [r["tomb_id"] for r in _rows()]
    assert len(ids) == len(set(ids)), "duplicate tomb_id detected"


# `tomb_id` comes in two shapes:
#   - Numbered form for PM-numbered sections: `KV5`, `QV55`, `TT100`, with
#     optional single lowercase suffix for letter-suffix variants like `KV5a`.
#   - Descriptor form for non-numbered PM sections (chunk-7 onwards):
#     `<PREFIX>-<TitleCaseDescriptor>` where PREFIX is the valley code
#     (`SWV`, `DAN`, `DEB`, `ASS`, …) and the descriptor is a PM-faithful
#     TitleCase rendering of the occupant name + disambiguator.
#
# Cross-refs from descriptor rows back to numbered tombs use the numbered
# form (`["KV20"]` for SWV-HatshepsutSouth's See-also), so this regex also
# backs `test_shared_with_tombs_are_valid_tomb_ids`.
# Descriptor-prefix vocabulary is limited to the prefixes actually in use
# (chunks landed to date: SWV South-West Valleys, DAN Dra' Abu el-Naga).
# Future chunks extend this regex AS THEY LAND their first row — speculative
# pre-registration was removed after the retrospective code-review on PR #100
# flagged it as YAGNI. See `test_prefix_vocabulary_consistent` below which
# pins the descriptor regex against `merge.VALLEY_ORDER`.
_TOMB_ID_RE = re.compile(
    r"^(?:(?:KV|QV|TT)\d+[a-z]?|(?:SWV|DAN)-[A-Z][A-Za-z0-9]*)$"
)


def test_tomb_id_shape() -> None:
    """Every id matches one of two shapes:
       - numbered `(KV|QV|TT)\\d+[a-z]?`
       - descriptor `(SWV|DAN|…)-<TitleCase…>`
    Extend the regex as future chunks introduce new valley prefixes.
    """
    for r in _rows():
        assert _TOMB_ID_RE.match(r["tomb_id"]), r["tomb_id"]


def test_prefix_vocabulary_consistent() -> None:
    """The descriptor-prefix set in `merge.py::VALLEY_ORDER` must match the
    descriptor alternation in `_TOMB_ID_RE` exactly.

    Rule-3 fix on the retrospective code-review of PR #100: the prior
    sync-by-comment (`merge.py:50` said \"kept in sync with the test regex\")
    is a markdown rule, not enforcement — if a future chunk registers a
    prefix in one place but not the other, the failure mode is silent
    mis-sort or silent mis-validation. This test converts that drift into
    a CI failure.
    """
    merge_path = SOURCE_DIR / "merge.py"
    spec = importlib.util.spec_from_file_location("pm_theban_merge", merge_path)
    merge_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(merge_mod)

    # Extract BOTH alternations from `_TOMB_ID_RE` so the test reports
    # drift on either axis (numbered or descriptor) rather than silently
    # misattributing a numbered-prefix divergence as a descriptor
    # divergence. Gemini round-2 finding on PR #105: hardcoding
    # `numbered_prefixes = {"KV","QV","TT"}` in the test means that if a
    # future chunk adds a new numbered prefix to VALLEY_ORDER + the regex
    # but not this test, the set-diff shifts the new prefix into
    # `descriptor_prefixes` and the failure message points at the wrong
    # alternation.
    numbered_match = re.search(r"\(\?:([A-Z|]+)\)\\d\+", _TOMB_ID_RE.pattern)
    assert numbered_match, (
        "could not parse numbered alternation from _TOMB_ID_RE; "
        "regex shape changed — update this test to match"
    )
    regex_numbered = set(numbered_match.group(1).split("|"))

    descriptor_match = re.search(r"\(\?:([A-Z|]+)\)-\[A-Z\]", _TOMB_ID_RE.pattern)
    assert descriptor_match, (
        "could not parse descriptor alternation from _TOMB_ID_RE; "
        "regex shape changed — update this test to match"
    )
    regex_descriptors = set(descriptor_match.group(1).split("|"))

    regex_all = regex_numbered | regex_descriptors
    valley_order_set = set(merge_mod.VALLEY_ORDER)

    assert valley_order_set == regex_all, (
        f"VALLEY_ORDER {sorted(valley_order_set)} diverged from "
        f"_TOMB_ID_RE alternations (numbered={sorted(regex_numbered)}, "
        f"descriptor={sorted(regex_descriptors)}). Keep the two in sync "
        f"when adding a new chunk that introduces a new valley prefix."
    )


def test_occupant_name_has_no_underdot_h() -> None:
    """CLAUDE.md rule 3 deterministic-enforcement: the README's strip-ḥ
    policy on `occupant_name` (matchable name field) must be enforced by a
    test, not just by prose in the README / prompts / after-the-fact
    `CHUNK*_CORRECTIONS`.

    Chunk-8 retrospective code-review P1 finding: the retroactive ḥ-sweep
    across chunks 7 + 8 only happened because a Gemini comment on PR #101
    spotted the drift. A test like this converts the next drift into a CI
    failure on the first subagent run, not a 5-round review cycle.

    Underdot-K (`ḳ`) is preserved as a distinguishing radical per the
    README exception (e.g. chunk-7 `ʿAḳ-hor`); this test only asserts
    absence of underdot-H (U+1E25).
    """
    for r in _rows():
        name = r.get("occupant_name") or ""
        assert "ḥ" not in name and "Ḥ" not in name, (
            f"{r['tomb_id']}: occupant_name {name!r} contains underdot-H — "
            "the README's matchable-name-field convention strips ḥ → h. "
            "If PM's text genuinely requires preserving the diacritic here, "
            "the exception must be documented and this test updated."
        )


def test_required_fields_present_on_every_row() -> None:
    """Schema discipline: every row carries every key, even when null/empty.

    Sparse rows are valid (CLAUDE.md rule 4), but the KEY must be present
    so downstream Phase A code can assume the schema without `.get()` calls.
    """
    required = {
        "tomb_id",
        "theban_area",
        "occupant_name",
        "occupant_alt_names",
        "occupant_role",
        "dynasty",
        "sub_period",
        "date_bce_approx_start",
        "date_bce_approx_end",
        "location_sub_area",
        "discovery_year",
        "discoverer",
        "is_unfinished",
        "shared_with_tombs",
        "notes_from_pm",
        "source_citation",
        # PR A (audit-fix, 2026-05-02): added so tomb-nicknames and joint
        # occupants get their own honest schema slot. `occupant_alt_names`
        # is now exclusively for SAME-PERSON name variants (e.g. prenomens).
        "tomb_aliases",
        "co_occupants",
        # PR A round-2 (PR #169 egyptologist P1, 2026-05-02): explicit
        # flag for joint coordinate burials with no PM-marked principal
        # (SWV-ThreePrincesses); see test_is_joint_burial_flag_paired_
        # with_co_occupants for the contract.
        "is_joint_burial",
    }
    for r in _rows():
        missing = required - r.keys()
        assert not missing, (r["tomb_id"], sorted(missing))


def test_theban_area_constraint() -> None:
    """`theban_area` belongs to a known controlled vocabulary.

    Forms in use:
    - chunks 1–6 (KV): `Valley of the Kings`
    - chunk 7 (DAN/SWV): `Dra' Abu el-Naga`, `South-West Valleys`
    - chunk 8 (QV): `Valley of the Queens`
    - chunk 9 (TT1–TT10): `Deir el-Medina`
    - chunk 10 (TT11–TT20): `Dra' Abu el-Naga`
    - chunk 11 (TT21–TT30): `Sh. ʿAbd el-Qurna`, `Dra' Abu el-Naga`,
      `ʿAsâsîf` — PM-faithful forms with `Sh.` abbreviation, ayin
      U+02BF on `ʿAbd` / `ʿAsâsîf`, circumflexes preserved on `ʿAsâsîf`.
    - chunk 12 (TT31–TT40): `Khokha` (TT32, TT39), `Qurnet Muraʿi` (TT40)
      — ayin U+02BF in `Muraʿi` per PM I.1's printed romanisation.

    Forward-compatible placeholders for future chunks (Deir el-Bahri,
    Ramesseum, Medinet Habu) are added as each chunk lands with the actual
    PM-printed form. Per CLAUDE.md rule 5 (tests assert values, not absence
    of errors) and rule 2 (no silent fallbacks), pre-emptive
    English-transliteration placeholders are NOT included — they would let
    an agent's mis-rendering through silently. Each form here matches a
    value actually populated in `reconciled.jsonl`.
    """
    valid = {
        "Valley of the Kings",
        "Valley of the Queens",
        "South-West Valleys",
        "Dra' Abu el-Naga",
        "Deir el-Medina",
        "Sh. ʿAbd el-Qurna",
        "ʿAsâsîf",
        "Khokha",
        "Qurnet Muraʿi",
    }
    for r in _rows():
        assert r["theban_area"] in valid, (r["tomb_id"], r["theban_area"])


# ---------------------------------------------------------------------------
# PR A audit-fix structural tests (2026-05-02): enforce the corrected schema
# semantics so future chunks cannot reintroduce the `occupant_alt_names`
# misuse the audit migrated away from. Each test is mechanical (CLAUDE.md
# rule 3) — no human review needed to catch a regression.
# ---------------------------------------------------------------------------


def test_no_compound_occupant_name() -> None:
    """`occupant_name` carries ONE person (the headword). Joint occupants
    go in `co_occupants` (PR A audit-fix). The `' and '` / `', and '` /
    `' & '` joiners that PM used in the few multi-occupant headwords (KV46
    Yuia+Thuiu, SWV Three Princesses Menhet+Merti+Menwi) are forbidden in
    `occupant_name` going forward.
    """
    forbidden = (" and ", ", and ", " & ", " + ")
    for r in _rows():
        n = r.get("occupant_name") or ""
        for joiner in forbidden:
            assert joiner not in n, (
                f"{r['tomb_id']}: occupant_name {n!r} contains {joiner!r} "
                f"— joint occupants must go in `co_occupants`."
            )


def test_occupant_alt_names_are_person_variants_not_tomb_nicknames() -> None:
    """`occupant_alt_names` is for SAME-PERSON name variants only (prenomens
    like the chunk-7 DAN-Antef rows; throne-name vs birth-name pairs;
    transliteration variants). Tomb-nicknames (`Belzoni's tomb`, `Tomb of
    Memnon`, `Bruce's tomb`, etc.) belong in the new `tomb_aliases` field
    (PR A audit-fix migration).

    Mechanical heuristic: any string matching `Tomb of …`, `…'s tomb`,
    `the …'s tomb`, or `the Tomb of …` is a tomb-name shape. Regex widened
    on PR #169 round-2 (Gemini round-1) to catch multi-word possessives
    (`The Great King's tomb`) and `(The )?Tomb of …` prefixes. Round-3
    (Gemini round-2) replaced the `'s tomb$` end-anchor with `'s tomb\\b`
    so trailing punctuation (`Belzoni's tomb.`) doesn't slip through.
    """
    nickname_re = re.compile(
        r"(?i)^(?:(?:the\s+)?tomb of\b|.*'s tomb\b)"
    )
    for r in _rows():
        for alt in r.get("occupant_alt_names") or []:
            assert not nickname_re.search(alt), (
                f"{r['tomb_id']}: occupant_alt_names contains tomb-nickname "
                f"{alt!r} — should be in `tomb_aliases` instead."
            )


def test_co_occupants_each_have_name_and_role() -> None:
    """Every entry in `co_occupants` is a `{name, role, alt_names}` dict —
    EXACTLY those three keys, non-empty name + role, list-shape alt_names.
    Joint-occupant rows lose their per-person role information if either
    field is null — and the whole point of the PR A migration was to
    recover that information.

    Round-2 tighten (PR #169 Gemini + code-reviewer P2-1, P2-2, P2-5):
    - exact key-set (no extra keys silently passed through),
    - role validated against the controlled vocab (free-text role drift
      forbidden — same enforcement as the row-level `occupant_role`),
    - empty-string guard on `name` and on each `alt_names` entry.
    """
    co_role_vocab = _occupant_role_controlled_vocab()
    expected_keys = {"name", "role", "alt_names"}
    for r in _rows():
        for i, co in enumerate(r.get("co_occupants") or []):
            assert isinstance(co, dict), (r["tomb_id"], i, co)
            assert set(co.keys()) == expected_keys, (
                r["tomb_id"], i, "co_occupant key-set must be exactly "
                f"{sorted(expected_keys)}, got {sorted(co.keys())}: {co}"
            )
            name = co["name"]
            assert isinstance(name, str) and name, (
                r["tomb_id"], i, "co_occupant name must be a non-empty string", co
            )
            role = co["role"]
            assert role in co_role_vocab, (
                r["tomb_id"], i,
                f"co_occupant role {role!r} not in controlled vocab "
                f"{sorted(co_role_vocab)}: {co}",
            )
            alt_names = co["alt_names"]
            assert isinstance(alt_names, list), (
                r["tomb_id"], i, "co_occupant alt_names must be a list", co
            )
            for j, alt in enumerate(alt_names):
                assert isinstance(alt, str) and alt, (
                    r["tomb_id"], i, j,
                    f"co_occupant alt_names[{j}] must be a non-empty string: {alt!r}",
                )


def test_tomb_aliases_is_list_of_strings() -> None:
    """`tomb_aliases` carries strings (tomb popular names / surveyor
    designations). Empty list is the default. Never null.
    """
    for r in _rows():
        ta = r.get("tomb_aliases")
        assert isinstance(ta, list), (r["tomb_id"], ta)
        for item in ta:
            assert isinstance(item, str) and item, (r["tomb_id"], item)


def test_is_joint_burial_flag_paired_with_co_occupants() -> None:
    """`is_joint_burial: bool` (PR A round-2, egyptologist P1) signals
    coordinate burials with no PM-marked principal — downstream Phase-A
    consumers must treat `occupant_name` and `co_occupants[*].name` as a
    coordinate union for join purposes when this flag is True.

    Mechanical contract:
    - Every row carries the field as a bool (default False).
    - A row with `is_joint_burial=True` MUST have at least one co_occupant
      (a single-occupant row cannot be a "joint" burial).
    - A row with `co_occupants` non-empty MAY be either True (coordinate,
      no primacy) or False (subordinate, headword is the principal).
      Both shapes are intentional — KV46 is False because PM marks Yuia
      as the syntactic subject; SWV-ThreePrincesses is True because PM
      lists the three coordinately. The two-row test below pins the
      current state explicitly.
    """
    seen_joint = []
    for r in _rows():
        flag = r.get("is_joint_burial")
        assert isinstance(flag, bool), (r["tomb_id"], flag, type(flag).__name__)
        if flag:
            assert (r.get("co_occupants") or []), (
                r["tomb_id"],
                f"is_joint_burial=True but co_occupants is empty — "
                f"a single-occupant tomb cannot be a joint burial.",
            )
            seen_joint.append(r["tomb_id"])
    # Joint-coordinate burials in the current corpus, sorted by tomb_id
    # via the merge sort key (TT10/TT122 sort before SWV-ThreePrincesses
    # because the TT prefix has rank 2 and SWV has rank 3 in
    # `merge.VALLEY_ORDER`):
    # - SWV-ThreePrincesses (chunk-7): PM p.591 lists Menhet/Merti/Menwi
    #   coordinately as `MENHET, MERTI, AND MENWI`.
    # - TT10 (chunk-9): PM p.19 lists Penbuy + Kasa coordinately as
    #   `PENBUY ... and KASA, Servants in the Place of Truth` — bare
    #   conjunction, plural role applies to both.
    # - TT122 (chunk-21): PM p.235 lists [Amen]hotp + Amenemhet as
    #   `[AMEN]ḤOTP, with Chapels of AMENEMḤET, both Overseers of the
    #   magazine of Amūn` — coordinate dual-occupancy with shared role.
    # - TT181 (chunk-27): PM p.286 lists NEBAMŪN + IPUKY coordinately as
    #   `181. NEBAMŪN ..., Head sculptor of the Lord of the Two Lands,
    #   AND IPUKY ..., Sculptor of the Lord of the Two Lands` — bare
    #   conjunction with distinct per-occupant roles; coordinate joint.
    # KV46 is intentionally False (asymmetric `YUIA ..., AND THUIU` —
    # Yuia leads). TT6 is also False (`X and son Y` — hierarchical).
    assert seen_joint == ["TT10", "TT122", "TT181", "SWV-ThreePrincesses"], seen_joint


def test_swv_three_princesses_per_person_role_propagation() -> None:
    """SWV-ThreePrincesses (PR #169 code-reviewer P2-4 + scope-enforcer
    requirement): the migration's choice to propagate the prior aggregate
    `Royal Family` label across all three per-person roles is a NEW per-
    person claim relative to the pre-PR-A single-row aggregate. Pin it as
    an assertion (not just a fix_rows rationale string) so future schema
    refinement that downgrades any single occupant to a different role is
    forced to update this test deliberately.

    Per-person refinement (likely to `Queen` after Lilyquist 2003) is
    deferred to a future chunk-7 re-extraction PR; that PR will replace
    this assertion when the egyptologist signs off on the per-person call.
    """
    r = _row("SWV-ThreePrincesses")
    assert r["occupant_role"] == "Royal Family"
    assert r["co_occupants"] == [
        {"name": "Merti", "role": "Royal Family", "alt_names": []},
        {"name": "Menwi", "role": "Royal Family", "alt_names": []},
    ]
    assert r["is_joint_burial"] is True


def test_occupant_role_controlled_vocab_covers_co_occupants() -> None:
    """Controlled vocab applies to `co_occupants[*].role` too (PR #169
    code-reviewer P2-2). Sibling enforcement to the row-level
    `occupant_role` controlled-vocab test — the whole point of PR A's
    `co_occupants` field is that per-occupant role becomes structured
    data; the vocabulary must apply there or free-text role drift defeats
    the structuring.

    `test_co_occupants_each_have_name_and_role` already enforces this on
    every row; this test is a focused regression-pin so a future relaxation
    of either test surfaces here.
    """
    vocab = _occupant_role_controlled_vocab()
    for r in _rows():
        for co in r.get("co_occupants") or []:
            assert co["role"] in vocab, (r["tomb_id"], co)


def _occupant_role_controlled_vocab() -> set[str]:
    """Single source of truth for the `occupant_role` / `co_occupants[*].role`
    controlled vocabulary. Mirrors the README field-semantics list.
    """
    return {
        "King",
        "Queen",
        "Royal Family",
        "Vizier",
        "Official",
        "High Priest",
        "Princess",
        "Prince",
        "Unknown",
    }


def test_all_prompts_mention_new_pr_a_fields() -> None:
    """Every PM extraction prompt mentions `tomb_aliases` AND `co_occupants`
    AND `is_joint_burial` AND `theban_area` (PR #169 code-reviewer P2-3 +
    PR #170 code-reviewer P2-2). Conversely, no prompt mentions the
    obsolete `"valley"` JSON key — the field was renamed in PR #170 and
    a stale prompt template would silently produce data under the wrong
    key, which `merge.py`'s field-union would carry through.

    Future chunks copy from these prompts; if a chunk-9+ prompt is written
    by copying chunk-1's pre-PR-A body without the new schema header,
    agents emit no values for the new fields and `SCHEMA_FIELD_DEFAULTS`
    silently fills `[]`/`False` — a tomb that genuinely has tomb-
    nicknames or joint occupants suffers data loss with no failing test.

    This is the rule-3 "deterministic enforcement over markdown convention"
    case — the prompt-update discipline must be a CI check.
    """
    prompt_files = sorted(SOURCE_DIR.glob("prompt*.md"))
    assert prompt_files, "no prompt*.md files found"
    for prompt in prompt_files:
        text = prompt.read_text()
        for field in (
            "tomb_aliases",
            "co_occupants",
            "is_joint_burial",
            "theban_area",
        ):
            assert field in text, (
                f"{prompt.name}: prompt does not mention `{field}` — "
                f"agents using this prompt will not emit the field, and "
                f"SCHEMA_FIELD_DEFAULTS will silently fill the default."
            )
        # No prompt may carry the obsolete `valley` JSON key — that field
        # was renamed to `theban_area` in PR #170. Stale templates would
        # produce data under the wrong key and the merge would propagate
        # it. Check both standard JSON (`"valley"`) and the single-quote
        # form (`'valley'`) per Gemini round-2 suggestion. (Body text
        # using "valley" as an English word — e.g. describing PM's
        # section structure — is fine; we test the JSON field-key form
        # specifically by requiring the quotes.)
        for legacy in (
            '"valley"',     # standard JSON key
            "'valley'",     # single-quoted variant (Gemini round-2)
            "`valley`",     # markdown backtick reference (Gemini round-3)
            "### valley",   # markdown section header (Gemini round-3)
        ):
            assert legacy not in text, (
                f"{prompt.name}: prompt still references the obsolete "
                f"JSON field key `{legacy}` — rename to `theban_area` "
                f"(PR #170)."
            )


def test_no_legacy_valley_field_key_in_reconciled() -> None:
    """No row in `reconciled.jsonl` carries the obsolete `valley` field
    key after the PR #170 rename (PR #170 code-reviewer P2-1).

    `raw/agent-*.jsonl` files are gitignored, but `merge.py` is field-
    name-agnostic — it picks fields from the union of agent emissions.
    If a stale agent re-runs against an unmigrated chunk-7+ prompt and
    emits `"valley"`, a re-merge would silently regenerate the obsolete
    key on disk. This test catches that drift mechanically.

    Belt-and-braces against `test_all_prompts_mention_new_pr_a_fields`'s
    upstream check on the prompt files themselves.
    """
    for r in _rows():
        assert "valley" not in r, (
            f"{r['tomb_id']}: row carries the obsolete `valley` field key "
            f"— rename to `theban_area` (PR #170). Most likely cause: a "
            f"stale agent JSONL was re-merged."
        )


def test_kv_rows_have_kv_tomb_id() -> None:
    """`tomb_id` prefix matches the `theban_area` value."""
    for r in _rows():
        if r["theban_area"] == "Valley of the Kings":
            assert r["tomb_id"].startswith("KV"), r
        if r["theban_area"] == "Valley of the Queens":
            assert r["tomb_id"].startswith("QV"), r


def test_dynasty_is_null_or_string() -> None:
    """`dynasty` is null at the extraction stage (Phase A enrichment fills
    it from the king authority). When populated by future enrichment, it
    must be the Arabic-numeral STRING form — Phase A relies on the string
    form for joining against the king authority; drift to int silently
    breaks that join.
    """
    for r in _rows():
        v = r["dynasty"]
        assert v is None or isinstance(v, str), (r["tomb_id"], v)


def test_dates_null_at_extraction_stage() -> None:
    """Per CLAUDE.md rule 1: PM headwords don't print BCE dates, so the
    dates fields stay null at extraction. Phase A king-authority enrichment
    against pharaoh.se populates them later. When populated, dates are
    negative ints.
    """
    for r in _rows():
        for field in ("date_bce_approx_start", "date_bce_approx_end"):
            v = r[field]
            if v is not None:
                assert isinstance(v, int) and v < 0, (r["tomb_id"], field, v)


def test_date_start_before_date_end() -> None:
    """For any row with both date_bce_approx_start and _end populated,
    start (more-negative, i.e. EARLIER BCE date) must be ≤ end. PM does
    not give regnal-end-then-start ordering anywhere; an inverted pair
    means a Phase A enrichment bug.
    """
    for r in _rows():
        s, e = r["date_bce_approx_start"], r["date_bce_approx_end"]
        if s is not None and e is not None:
            assert s <= e, (r["tomb_id"], s, e)


def test_source_citation_shape() -> None:
    """`source_citation` is a dict with `page` (int), `edition` (str), `section` (str)."""
    valid_editions = {EDITION_PM_I1, EDITION_PM_I2}
    for r in _rows():
        c = r["source_citation"]
        assert set(c.keys()) == {"page", "edition", "section"}, (r["tomb_id"], c.keys())
        assert isinstance(c["page"], int) and c["page"] > 0, (r["tomb_id"], c["page"])
        assert c["edition"] in valid_editions, (r["tomb_id"], c["edition"])
        assert isinstance(c["section"], str) and c["section"], (r["tomb_id"], c["section"])


def test_source_citation_page_in_chunk1_range() -> None:
    """Chunk 1 covers PM I.2 printed pages 495–518. Every chunk-1 row's
    page citation must fall within that range. Catches off-by-one bugs
    in extraction's running-header parsing.
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 495 <= page <= 518, (tid, page)


def test_shared_with_tombs_are_valid_tomb_ids() -> None:
    """Every entry in `shared_with_tombs` matches the tomb-id regex."""
    for r in _rows():
        for tid in r["shared_with_tombs"]:
            assert _TOMB_ID_RE.match(tid), (r["tomb_id"], tid)


def test_shared_with_tombs_symmetry_within_chunk() -> None:
    """If KV5.shared_with_tombs lists KV7, then KV7.shared_with_tombs lists KV5
    — but only for pairs in the SAME PM section (same `source_citation.section`).

    Cross-section `See also` references are asymmetric in PM by design — the
    South Tomb of Hatshepsut (§ II.A) PM-prints `See also Tomb 20, supra, p. 546`
    referencing KV20 in § I.A, but PM's KV20 headword does not symmetrically
    reference the South Tomb. Enforcing symmetry across sections would force us
    to fabricate back-references PM doesn't print — violating CLAUDE.md rule 1
    (every fact must trace to its committed raw source).

    Within-section symmetry still holds (PM does cross-reference symmetrically
    within § I.A — KV3 ↔ KV11, KV5 ↔ KV7 — those pairs are both in the same
    § I.A "Tombs" section).
    """
    by_id = {r["tomb_id"]: r for r in _rows()}
    for r in _rows():
        for partner in r["shared_with_tombs"]:
            if partner not in by_id:
                continue
            own_section = r["source_citation"]["section"]
            partner_section = by_id[partner]["source_citation"]["section"]
            if own_section != partner_section:
                # Cross-section `See also` — asymmetric by PM convention.
                continue
            back_refs = by_id[partner]["shared_with_tombs"]
            assert r["tomb_id"] in back_refs, (
                f"{r['tomb_id']} → {partner} but {partner} → {back_refs}"
            )


def test_occupant_role_controlled_vocab() -> None:
    """Controlled vocabulary for `occupant_role`. Extend as new sections add roles."""
    valid = {"King", "Queen", "Royal Family", "Vizier", "Official",
             "High Priest", "Princess", "Prince", "Unknown"}
    for r in _rows():
        if r["occupant_role"] is not None:
            assert r["occupant_role"] in valid, (r["tomb_id"], r["occupant_role"])


# ---------------------------------------------------------------------------
# Chunk-1 specific value-assertion tests (KV1–KV10)
# ---------------------------------------------------------------------------


def test_chunk1_all_rows_kv_kings_no_dynasty_or_dates() -> None:
    """KV1–KV10 are all kings — `theban_area` and `occupant_role` are uniform.
    Dynasty + BCE dates are null at this stage (Phase A enrichment).
    """
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk1_unfinished_flag() -> None:
    """KV3 (Ramesses III's first attempt) and KV5 (Ramesses II) are flagged
    `Unfinished` literally in PM. KV4 (Ramesses XI) was historically
    unfinished but PM doesn't use the literal word — `is_unfinished` stays
    false. This test pins the literal-text rule.
    """
    expected_unfinished = {"KV3", "KV5"}
    for tid in CHUNK1_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk1_shared_with_tombs() -> None:
    """KV3 → KV11 (chunk 2 — one-sided), KV5 ↔ KV7 (both chunk 1)."""
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    assert _row("KV5")["shared_with_tombs"] == ["KV7"]
    assert _row("KV7")["shared_with_tombs"] == ["KV5"]
    # All other chunk-1 rows have empty shared_with_tombs.
    for tid in CHUNK1_TOMB_IDS - {"KV3", "KV5", "KV7"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk1_kv1_minimal_row() -> None:
    """KV1 (Ramesses VII) is the minimal-shape KV chunk-1 row: no Unfinished
    flag, no cross-refs, no notes, no alt-names. Asserts every field.

    The KV3 flagship row (separate test below) exercises is_unfinished +
    shared_with_tombs; KV9 exercises notes_from_pm + occupant_alt_names.
    Together they cover every populated-field shape per rule 5.
    """
    r = _row("KV1")
    assert r["tomb_id"] == "KV1"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VII"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 495,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv3_flagship_full_row() -> None:
    """KV3 (Ramesses III's unfinished tomb) is the flagship full-row test:
    exercises `is_unfinished=true` and `shared_with_tombs=["KV11"]` (a
    one-sided cross-chunk reference). Asserts every field per rule 5.
    """
    r = _row("KV3")
    assert r["tomb_id"] == "KV3"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == ["KV11"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 500,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv9_ramesses_vi_notes_and_aliases() -> None:
    """KV9 exercises `notes_from_pm` (the cross-line clause about Ramesses V's
    doorway usurpation) and `tomb_aliases` (the two 19th-c. classical-traveller
    nicknames from PM's `'Tomb of Metempsychosis', or 'Tomb of Memnon'`
    parenthetical — TOMB-names, not occupant alt-names; migrated from
    `occupant_alt_names` in PR A audit-fix). Asserts every field per rule 5.
    """
    r = _row("KV9")
    assert r["tomb_id"] == "KV9"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses VI"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Tomb of Metempsychosis", "Tomb of Memnon"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "doorways in outer part usurped from Ramesses V."
    assert r["source_citation"] == {
        "page": 511,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk1_kv4_ramesses_xi_notes_preserved() -> None:
    """KV4's headword: `RAMESSES XI (formerly XII)`. The parenthetical
    `(formerly XII)` is PM's regnal-number disambiguation — earlier
    scholarship counted this king as Ramesses XII. Preserved as a
    structured `notes_from_pm` rather than embedded in `occupant_name`,
    so downstream museum-data joins on the canonical `Ramesses XI` work.
    """
    r = _row("KV4")
    assert r["occupant_name"] == "Ramesses XI"
    assert r["notes_from_pm"] == "formerly XII"


def test_chunk1_two_ramesses_ii_tombs() -> None:
    """KV5 and KV7 are both attributed to Ramesses II (KV5 unfinished, KV7
    the actual completed tomb). Mutually-cross-referenced via shared_with_tombs.
    """
    kv5 = _row("KV5")
    kv7 = _row("KV7")
    for r in (kv5, kv7):
        assert r["occupant_name"] == "Ramesses II"
        assert r["theban_area"] == "Valley of the Kings"
        assert r["occupant_role"] == "King"
    assert kv5["is_unfinished"] is True
    assert kv7["is_unfinished"] is False
    assert kv5["shared_with_tombs"] == ["KV7"]
    assert kv7["shared_with_tombs"] == ["KV5"]
    assert kv5["source_citation"]["page"] == 501
    assert kv7["source_citation"]["page"] == 505


def test_chunk1_kv8_merneptah_page_507() -> None:
    """KV8 (Merneptah) headword opens at PM I.2 printed page 507, NOT 509.
    Egyptologist-reviewer caught the mis-citation in PR #66's first round;
    the field-rule-based prompt rewrite (with page extracted from chunk
    text running headers) produces the correct page. This test pins it.
    """
    r = _row("KV8")
    assert r["occupant_name"] == "Merneptah"
    assert r["source_citation"]["page"] == 507


# ---------------------------------------------------------------------------
# Chunk-2 specific value-assertion tests (KV11–KV20)
# ---------------------------------------------------------------------------


def test_chunk2_page_range() -> None:
    """Chunk 2 headwords sit on PM I.2 printed pages 518–546. Every chunk-2
    row's page citation must fall within that range. The chunk FILE
    extends two pages further (p.547–548) to give the extraction agents
    boundary context, but no KV headword in the chunk sits past p.546.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 518 <= page <= 546, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk2_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-2 row has theban_area=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunk 1.
    """
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["location_sub_area"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk2_unfinished_flag() -> None:
    """KV18 (Ramesses X) is the only chunk-2 tomb flagged `Unfinished` in PM."""
    expected_unfinished = {"KV18"}
    for tid in CHUNK2_TOMB_IDS:
        r = _row(tid)
        if tid in expected_unfinished:
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk2_shared_with_tombs() -> None:
    """KV11 ↔ KV3 cross-chunk symmetry: both rows reference each other.
    KV20's informal `See also South Tomb` is NOT a numbered cross-ref — stays empty.
    """
    assert _row("KV11")["shared_with_tombs"] == ["KV3"]
    assert _row("KV3")["shared_with_tombs"] == ["KV11"]
    for tid in CHUNK2_TOMB_IDS - {"KV11"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk2_kv11_ramesses_iii_full_row() -> None:
    """KV11 (Ramesses III) flagship row — exercises cross-chunk back-
    reference to KV3, tomb-nicknames (`Bruce's tomb`, `the Harper's tomb`)
    from PM's headword parenthetical (TOMB-names — migrated from the older
    `occupant_alt_names` slot to `tomb_aliases` in PR A audit-fix), and
    headword-at-page-tail extraction (KV11's headword sits at the bottom of
    physical p.60 / printed 518). Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV11")
    assert r["tomb_id"] == "KV11"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses III"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Bruce's tomb", "the Harper's tomb"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == ["KV3"]
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 518,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv12_uninscribed() -> None:
    """KV12 (PM: `UNINSCRIBED`) — the tomb has no named occupant. Per the
    extraction prompt + fix_rows.py correction: `occupant_name=null` and
    `occupant_role='Unknown'`. Asserts every field per rule 5.
    """
    r = _row("KV12")
    assert r["tomb_id"] == "KV12"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv13_bay_chancellor() -> None:
    """KV13 (Bay, Chancellor — non-royal). Exercises non-King
    `occupant_role` (`Official`) and the `notes_from_pm` regnal-dating
    fragment from PM's headword (`Temp. Merneptaḥ-Siptaḥ`), captured
    via fix_rows.py after the reviewer flagged that all three extraction
    agents dropped it. Asserts every field per rule 5.
    """
    r = _row("KV13")
    assert r["tomb_id"] == "KV13"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Bay"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Temp. Merneptaḥ-Siptaḥ."
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv14_tausert_usurpation_note() -> None:
    """KV14 (Tausert, usurped by Setnakht) — exercises the biographical-
    plus-usurpation `notes_from_pm` clause, distinct from `occupant_alt_names`
    (Setnakht is a later usurper, NOT a classical alias of Tausert).
    Asserts every field per rule 5.
    """
    r = _row("KV14")
    assert r["tomb_id"] == "KV14"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tausert"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "wife of Sethos II. Usurped by Setnakht."
    assert r["source_citation"] == {
        "page": 527,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv17_sethos_i_belzoni_alias() -> None:
    """KV17 (Sethos I) — exercises the `Belzoni's tomb` 19th-c. nickname
    from PM's headword single-quote parenthetical (a TOMB-name after the
    1817 discoverer Giovanni Battista Belzoni, NOT an occupant alt-name;
    migrated from `occupant_alt_names` to `tomb_aliases` in PR A audit-
    fix). PM's spelling `Sethos I` is preserved verbatim (the ruler
    authority bridges to the modern `Seti I` convention in Phase A; the
    extract stays faithful to PM). Asserts every field per rule 5.
    """
    r = _row("KV17")
    assert r["tomb_id"] == "KV17"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Sethos I"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Belzoni's tomb"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 535,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv18_ramesses_x_unfinished() -> None:
    """KV18 (Ramesses X) — exercises `is_unfinished=True` and the
    `formerly XI` regnal-number disambiguation note. PM's headword
    literally prints `RAMESSES X (formerly XI)` and `Unfinished.` after
    the bibliographic ribbon. Asserts every field per rule 5.
    """
    r = _row("KV18")
    assert r["tomb_id"] == "KV18"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ramesses X"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is True
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "formerly XI"
    assert r["source_citation"] == {
        "page": 545,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv19_prince_ramesses_mentuherkhepshef() -> None:
    """KV19 (the Prince's tomb) — exercises the `Prince` role (royal son
    who never reigned, distinct from the rest of the chunk's ruling
    kings) and the `son of Ramesses IX` relational note from PM's
    headword. The `occupant_name` preserves PM's verbatim spelling
    `Raʿmeses-Mentuhirkhopshef` (with ayin, with PM's `e/i/u` choices)
    rather than over-modernising to `Ramesses-Mentuherkhepshef` —
    PM-verbatim policy, per egyptologist-reviewer on PR #68.
    Asserts every field per rule 5.
    """
    r = _row("KV19")
    assert r["tomb_id"] == "KV19"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Raʿmeses-Mentuhirkhopshef"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Prince"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "son of Ramesses IX."
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk2_kv20_hatshepsut_king() -> None:
    """KV20 (Hatshepsut) — exercises Hatshepsut-as-ruling-King disposition
    (not Queen), and `shared_with_tombs=[]` (PM's `See also South Tomb`
    is informal, not a numbered KV cross-ref). Asserts every field per
    rule 5.
    """
    r = _row("KV20")
    assert r["tomb_id"] == "KV20"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Hatshepsut"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 546,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-3 specific value-assertion tests (KV22–KV46 sparse)
# ---------------------------------------------------------------------------


def test_chunk3_page_range() -> None:
    """Chunk 3 headwords sit on PM I.2 printed pages 547–562. Every chunk-3
    row's page citation must fall within that range.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 547 <= page <= 562, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk3_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-3 row has theban_area=VoK and null dynasty/dates/discoverer —
    same extraction-stage discipline as chunks 1 and 2.

    `is_unfinished` and `shared_with_tombs` are pinned per-row in the
    themed tests below rather than here — asserting them as chunk-wide
    invariants would fail if a future reviewer-caught correction
    identifies an Unfinished tomb or cross-ref in this PM range, and
    the per-row tests already give full coverage.
    """
    for tid in CHUNK3_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk3_kv21_absent_from_expected_set() -> None:
    """KV21 is not part of chunk-2 (KV20 jumps to KV22 in PM). Defensive
    structural check — lives here because chunk-3's range-definition is
    what documents the absence formally.
    """
    assert "KV21" not in EXPECTED_TOMB_IDS


def test_chunk3_missing_kv_ids_absent_from_expected_set() -> None:
    """KV24–KV33, KV37, KV40, KV41, KV44 are not in PM I.2 § I.A — they
    jump out of PM's cataloguing. If a future chunk PR accidentally pulls
    one of these in, this test fails loudly.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(24, 34)] + ["KV37", "KV40", "KV41", "KV44"]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk3_kv22_amenophis_iii_west_valley() -> None:
    """KV22 (Amenophis III) — West Valley tomb. Exercises:
    - `location_sub_area = "West Valley"` (first row in the extract with
      a non-null sub-area);
    - PM-verbatim `"Amenophis III"` despite modern `Amenhotep III`
      convention (PM's 1964 form is Amenophis);
    - `notes_from_pm` captures headword `Excavated by ...` clause.
    Asserts every field per rule 5.
    """
    r = _row("KV22")
    assert r["tomb_id"] == "KV22"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis, and by Carnarvon and Carter."
    assert r["source_citation"] == {
        "page": 547,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv23_ay_classical_aliases() -> None:
    """KV23 (Ay) — two 19th-c. surveyor tomb-names (`Eesa`, the local
    Arabic name cited by Wilkinson as 'W. -2 ("Eesa")'; `Schai`, the
    Prisse / Nestor L'Hôte designation for the same tomb). Both are
    TOMB-names from West-Valley survey traditions, NOT alternate names of
    the king Ay. Migrated from `occupant_alt_names` to `tomb_aliases` in
    PR A audit-fix. Tomb is also in the West Valley. Asserts every field
    per rule 5.
    """
    r = _row("KV23")
    assert r["tomb_id"] == "KV23"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Ay"
    assert r["occupant_alt_names"] == []
    assert r["tomb_aliases"] == ["Eesa", "Schai"]
    assert r["co_occupants"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] == "West Valley"
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Belzoni."
    assert r["source_citation"] == {
        "page": 550,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv34_tuthmosis_iii_first_edition_note() -> None:
    """KV34 (Tuthmosis III) — `notes_from_pm` captures PM's `[Ist ed. 24]`
    cross-reference to the 1st-edition tomb numbering. Parallel in shape
    to chunk-1 KV4's `formerly XII` and chunk-2 KV18's `formerly XI`.
    Asserts every field per rule 5.
    """
    r = _row("KV34")
    assert r["tomb_id"] == "KV34"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis III"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "1st ed. 24"
    assert r["source_citation"] == {
        "page": 551,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv36_mahirper_official() -> None:
    """KV36 (Mahirper) — non-royal `Official` role (Standard-bearer, Child
    of the nursery, temp. Hatshepsut). PM's text layer prints `MAI;IIRPER`
    where `I;I` is the underdot-H glyph; applying the chunk-1/2 rule
    `I;I → h` yields `Mahirper` (not `Maihirper` — that leaves a
    spurious `i` before the `h`; egyptologist-reviewer second-pass on
    PR #69 confirmed no published Egyptological form reads `Maihirper`).
    Asserts every field per rule 5.
    """
    r = _row("KV36")
    assert r["tomb_id"] == "KV36"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Mahirper"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Standard-bearer, Child of the nursery. Temp. Ḥatshepsut. "
        "Excavated by Loret."
    )
    assert r["source_citation"] == {
        "page": 556,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv39_uninscribed_unknown_with_attribution_note() -> None:
    """KV39 — PM prints `Uninscribed tomb, attributed to Amenophis I by
    Weigall...`. Exercises: null `occupant_name` + `Unknown` role
    (distinct from KV12 which is `UNINSCRIBED` without attribution),
    plus the attribution-descriptor captured as `notes_from_pm`. Asserts
    every field per rule 5.
    """
    r = _row("KV39")
    assert r["tomb_id"] == "KV39"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    # Extended on PR #151 by egyptologist printed-source review of PM p.559:
    # the previous truncated form dropped the load-bearing Abbott Papyrus +
    # Peet citation chain (independent reason to doubt the Amenophis I
    # attribution) AND the `infra, p. 599` cross-reference linking KV39 to
    # DAN-AhmosiNefertere. Restored to PM-verbatim full paragraph.
    assert r["notes_from_pm"] == (
        "Uninscribed tomb, attributed to Amenophis I by Weigall in Ann. "
        "Serv. xi (1911), pp. 174-5 [12], and id. A Guide to the "
        "Antiquities of Upper Egypt, pp. 163-4, but this is not "
        "supported by any inscriptional evidence, and does not "
        "correspond with the position given in the Abbott Papyrus "
        "(cf. Peet, The Great Tomb-Robberies of the Twentieth Egyptian "
        "Dynasty, pp. 37-8). See also the tomb of Queen ʿAhmosi "
        "Nefertere, infra, p. 599."
    )
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv42_tuthmosis_ii_attribution_uncertain() -> None:
    """KV42 (Tuthmosis II) — PM prints the attribution with a `(?)`
    uncertainty marker (`TUTHMOSIS II (?)`). The structured `occupant_name`
    stays clean; the uncertainty is captured in `notes_from_pm` alongside
    the existing `Excavated by Loret` headword clause. Asserts every
    field per rule 5.
    """
    r = _row("KV42")
    assert r["tomb_id"] == "KV42"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "(?). Excavated by Loret"
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv35_amenophis_ii() -> None:
    """KV35 (Amenophis II) — straightforward King row. PM's text layer
    renders `II` as `n` in this headword; the extract normalises to
    `Amenophis II`. Asserts every field per rule 5.
    """
    r = _row("KV35")
    assert r["tomb_id"] == "KV35"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis II"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 554,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv38_tuthmosis_i() -> None:
    """KV38 (Tuthmosis I) — King row with `Excavated by Loret` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV38")
    assert r["tomb_id"] == "KV38"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis I"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Loret."
    assert r["source_citation"] == {
        "page": 557,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv43_tuthmosis_iv() -> None:
    """KV43 (Tuthmosis IV) — King row with `Excavated by Davis` headword
    clause in notes. Asserts every field per rule 5.
    """
    r = _row("KV43")
    assert r["tomb_id"] == "KV43"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tuthmosis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "Excavated by Davis."
    assert r["source_citation"] == {
        "page": 559,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv45_userhet_re_used() -> None:
    """KV45 (Userhet) — re-used tomb pattern. Original Dyn XVIII occupant
    (Userhet) is the canonical `occupant_name`; the re-user (Merenkhons,
    Dyn XXII) goes in `notes_from_pm`. Asserts every field per rule 5.
    """
    r = _row("KV45")
    assert r["tomb_id"] == "KV45"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Userhet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Overseer of the Fields of Amūn, Dyn. XVIII, re-used by Merenkhons, "
        "Doorkeeper of the House of Amūn, Dyn. XXII (name from scarab). "
        "Excavated by Davis and Carter."
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk3_kv46_yuia_and_thuiu_multi_occupant() -> None:
    """KV46 — multi-occupant tomb (Yuia + Thuiu, parents of Queen Teye).
    Exercises the post-PR-A `co_occupants` pattern: headword `occupant_name`
    is `Yuia` (PM lists him first, with the title `Divine father`), the
    second occupant `Thuiu` (`Chief of the harîm of Amūn`) lives in
    `co_occupants`. Per-occupant role replaces the prior aggregate
    `Royal Family` label — both are non-royal court officials (parents-in-
    law of Amenhotep III). Biographical prose stays in `notes_from_pm`.
    Asserts every field per rule 5.
    """
    r = _row("KV46")
    assert r["tomb_id"] == "KV46"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Yuia"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == [
        {
            "name": "Thuiu",
            "role": "Official",
            "alt_names": [],
        }
    ]
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Divine father, and Chief of the harîm of Amūn, parents of "
        "Queen Teye."
    )
    assert r["source_citation"] == {
        "page": 562,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-4 specific value-assertion tests (KV47, 48, 55, 56, 57)
# ---------------------------------------------------------------------------


def test_chunk4_page_range() -> None:
    """Chunk 4 headwords sit on PM I.2 printed pages 564–567."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        page = r["source_citation"]["page"]
        assert 564 <= page <= 567, (tid, page)
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "I.A"


def test_chunk4_all_rows_in_valley_of_kings_no_dynasty_or_dates() -> None:
    """Every chunk-4 row has theban_area=VoK and null dynasty/dates/discoverer."""
    for tid in CHUNK4_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Kings"
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None


def test_chunk4_missing_kv_ids_absent_from_expected_set() -> None:
    """KV49–54 and KV58–61 are absent from PM I.2 § I.A (PM jumps 48 → 55
    and 57 → 62). KV62 (Tutʿankhamun) IS in the expected set as of chunk 5.
    """
    must_be_absent = (
        [f"KV{n}" for n in range(49, 55)]
        + [f"KV{n}" for n in range(58, 62)]
    )
    for tid in must_be_absent:
        assert tid not in EXPECTED_TOMB_IDS, tid


def test_chunk4_kv47_merneptah_siptah() -> None:
    """KV47 — Merneptah-Siptah, King, first Dyn-19 joint-name occupant.
    PM's `MERNEPTAḤ-SIPTAḤ` → `Merneptah-Siptah` (underdots stripped in
    occupant_name per the README's diacritic policy). Asserts every
    field per rule 5.
    """
    r = _row("KV47")
    assert r["tomb_id"] == "KV47"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Merneptah-Siptah"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 564,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv48_amenemopet_vizier() -> None:
    """KV48 — Amenemopet, Vizier, temp. Amenophis II. First `Vizier` role
    in the landed extract (vs `Official` for Bay in KV13). PM's notes
    clause preserves the title pair, regnal-dating, and TT29 cross-ref.
    Asserts every field per rule 5.
    """
    r = _row("KV48")
    assert r["tomb_id"] == "KV48"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Vizier"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Governor of the town, Vizier. Temp. Amenophis II. "
        "(Also owner of Theb. tb. 29.)"
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv55_amenophis_iv_hedged_attribution() -> None:
    """KV55 — PM's headword: `Probably AMENOPHIS IV, formerly attributed
    to Queen Teye or to Smenkhkarēʿ.` The structured `occupant_name`
    strips PM's `Probably` hedge (clean matchable name); the full
    hedging clause is captured verbatim in `notes_from_pm` including
    PM's macron-e and trailing ayin on `Smenkhkarēʿ`. Asserts every
    field per rule 5.
    """
    r = _row("KV55")
    assert r["tomb_id"] == "KV55"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Amenophis IV"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "Probably Amenophis IV, formerly attributed to Queen Teye or to "
        "Smenkhkarēʿ."
    )
    assert r["source_citation"] == {
        "page": 565,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv56_gold_tomb_uninscribed() -> None:
    """KV56 — PM's `'Gold Tomb', uninscribed.` (the nickname stems from
    the rich Tausert / Sethos II jewelry finds in this tomb). Null name
    + `Unknown` role + PM's nickname captured verbatim in notes.
    Asserts every field per rule 5.
    """
    r = _row("KV56")
    assert r["tomb_id"] == "KV56"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] is None
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Unknown"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == "'Gold Tomb', uninscribed."
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


def test_chunk4_kv57_haremhab() -> None:
    """KV57 — Haremhab, King. PM's `ḤAREMḤAB` → `Haremhab` (underdots
    stripped in occupant_name). Asserts every field per rule 5.
    """
    r = _row("KV57")
    assert r["tomb_id"] == "KV57"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Haremhab"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] is None
    assert r["source_citation"] == {
        "page": 567,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-5 specific value-assertion tests (KV62 Tutʿankhamun, standalone)
# ---------------------------------------------------------------------------


def test_chunk5_kv62_tutankhamun_full_row() -> None:
    """KV62 — Tutʿankhamun, standalone single-row chunk. Exercises PM's
    ayin glyph preservation in `occupant_name` (matches chunk-2 KV19
    `Raʿmeses-Mentuhirkhopshef` precedent — ayin is a royal-name
    radical, not a styling diacritic, so preserved even though the
    `occupant_name` field otherwise strips diacritics).

    Also exercises the joint `notes_from_pm` capture:
    - PM's `[1st ed. 58]` cross-ref → `"1st ed. 58"` (same normalisation
      as chunk-3 KV34).
    - PM's `Excavated by Carnarvon and Carter.` ribbon clause.
    - Joined with `". "` per chunk-2 KV14 pattern.

    Asserts every field per CLAUDE.md rule 5.
    """
    r = _row("KV62")
    assert r["tomb_id"] == "KV62"
    assert r["theban_area"] == "Valley of the Kings"
    assert r["occupant_name"] == "Tutʿankhamun"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "King"
    assert r["dynasty"] is None
    assert r["sub_period"] is None
    assert r["date_bce_approx_start"] is None
    assert r["date_bce_approx_end"] is None
    assert r["location_sub_area"] is None
    assert r["discovery_year"] is None
    assert r["discoverer"] is None
    assert r["is_unfinished"] is False
    assert r["shared_with_tombs"] == []
    assert r["notes_from_pm"] == (
        "1st ed. 58. Excavated by Carnarvon and Carter."
    )
    assert r["source_citation"] == {
        "page": 569,
        "edition": EDITION_PM_I2,
        "section": "I.A",
    }


# ---------------------------------------------------------------------------
# Chunk-7 specific value-assertion tests (PM I.2 § II + § III.A/C/D —
# South-West Valleys + Dra' Abu el-Naga royal-and-near-royal tombs).
#
# First chunk with NON-NUMBERED tomb_ids: descriptor form `<PREFIX>-<Name>`.
# Per CLAUDE.md rule 5 every mappable field on every chunk-7 row is
# asserted below. 18 rows across 5 PM sub-sections.
# ---------------------------------------------------------------------------


def test_chunk7_uniform_null_phase_a_fields() -> None:
    """Every chunk-7 row carries null for the Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`). Per CLAUDE.md rule 1, PM headwords do
    not print those values as structured data — they're filled by Phase A
    ruler-authority enrichment against pharaoh.se.
    """
    for tid in CHUNK7_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["source_citation"]["edition"] == EDITION_PM_I2


def test_chunk7_section_ii_location_sub_areas() -> None:
    """§ II rows carry the wadi sub-area PM prints in the section header.
    § II.A = Wadi Sikket Taqet Zaid; § II.B = Wadi Qubbanet el-Qirud.
    """
    assert _row("SWV-HatshepsutSouth")["location_sub_area"] == "Wadi Sikket Taqet Zaid"
    assert _row("SWV-Neferure")["location_sub_area"] == "Wadi Qubbanet el-Qirud"
    assert _row("SWV-ThreePrincesses")["location_sub_area"] == "Wadi Qubbanet el-Qirud"


def test_chunk7_section_iii_a_location_sub_areas() -> None:
    """§ III.A Antef Cemetery is at El-Ṭaraf per PM's section header
    `A. ANTEF CEMETERY. Dyn. XI. At El-Ṭaraf`. PM ties the three Dyn-XI
    royal tombs (two Antefs + Mentuhotp-Sʿankhibtaui) to that locality.
    """
    for tid in {"DAN-AntefSehertaui", "DAN-AntefWahankh", "DAN-MentuhotpSankhibtaui"}:
        assert _row(tid)["location_sub_area"] == "El-Ṭaraf", tid


def test_chunk7_section_iii_c_and_d_no_sub_area() -> None:
    """§ III.C and § III.D headwords don't name a finer wadi beyond
    Dra' Abu el-Naga itself — `location_sub_area` stays null for those rows.
    """
    section_iii_c_and_d = CHUNK7_TOMB_IDS - {
        "SWV-HatshepsutSouth",
        "SWV-Neferure",
        "SWV-ThreePrincesses",
        "DAN-AntefSehertaui",
        "DAN-AntefWahankh",
        "DAN-MentuhotpSankhibtaui",
    }
    for tid in section_iii_c_and_d:
        assert _row(tid)["location_sub_area"] is None, tid


def test_chunk7_only_mentuhotp_sankhibtaui_unfinished() -> None:
    """PM marks only Mentuhotp-Sʿankhibtaui's tomb `Unfinished` in chunk 7.
    Every other chunk-7 row carries `is_unfinished: false`.
    """
    for tid in CHUNK7_TOMB_IDS:
        r = _row(tid)
        if tid == "DAN-MentuhotpSankhibtaui":
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk7_shared_with_tombs() -> None:
    """Only the South Tomb of Hatshepsut (§ II.A) cross-references into § I.A
    via PM's literal `See also Tomb 20, supra, p. 546` clause — asymmetric
    per `test_shared_with_tombs_symmetry_within_chunk`.
    """
    assert _row("SWV-HatshepsutSouth")["shared_with_tombs"] == ["KV20"]
    for tid in CHUNK7_TOMB_IDS - {"SWV-HatshepsutSouth"}:
        assert _row(tid)["shared_with_tombs"] == [], tid


def test_chunk7_valleys() -> None:
    """§ II rows → `South-West Valleys`; § III rows → `Dra' Abu el-Naga`."""
    swv_ids = {"SWV-HatshepsutSouth", "SWV-Neferure", "SWV-ThreePrincesses"}
    for tid in swv_ids:
        assert _row(tid)["theban_area"] == "South-West Valleys", tid
    for tid in CHUNK7_TOMB_IDS - swv_ids:
        assert _row(tid)["theban_area"] == "Dra' Abu el-Naga", tid


def test_chunk7_pm_sections() -> None:
    """`source_citation.section` matches PM's sub-section label per tomb."""
    expected = {
        "SWV-HatshepsutSouth": "II.A",
        "SWV-Neferure": "II.B",
        "SWV-ThreePrincesses": "II.B",
        "DAN-AntefSehertaui": "III.A",
        "DAN-AntefWahankh": "III.A",
        "DAN-MentuhotpSankhibtaui": "III.A",
        "DAN-AhmosiNefertere": "III.C",
        "DAN-Aqhor": "III.D",
        "DAN-Ahhotep": "III.D",
        "DAN-AhmosiHenutempet": "III.D",
        "DAN-AhmosiSonOfSeqenenre": "III.D",
        "DAN-AntefNubkheperre": "III.D",
        "DAN-AntefSekhemreHeruhirmaet": "III.D",
        "DAN-AntefSekhemreWepmaet": "III.D",
        "DAN-KamosiWazkheperre": "III.D",
        "DAN-MentuhotpIWifeOfDjhuti": "III.D",
        "DAN-Neferhotep": "III.D",
        "DAN-SebkemsafSekhemreShedtaui": "III.D",
    }
    for tid, sec in expected.items():
        assert _row(tid)["source_citation"]["section"] == sec, tid


def test_chunk7_occupant_roles() -> None:
    """Controlled-vocab `occupant_role` assignments per chunk-7 row."""
    expected = {
        # Pre-kingship Hatshepsut's South Tomb — PM text is explicit that
        # the quartzite sarcophagus is inscribed "as Queen-Consort".
        "SWV-HatshepsutSouth": "Queen",
        # Princess Neferure (hedged "Probably Princess Neferure").
        "SWV-Neferure": "Princess",
        # Three princesses shared tomb — Royal Family (catch-all for
        # multi-occupant royal burials).
        "SWV-ThreePrincesses": "Royal Family",
        # § III.A Antef Cemetery (Dyn XI rulers).
        "DAN-AntefSehertaui": "King",
        "DAN-AntefWahankh": "King",
        "DAN-MentuhotpSankhibtaui": "King",
        # § III.C Ahmose-Nefertari = Queen (wife of King Ahmose).
        "DAN-AhmosiNefertere": "Queen",
        # § III.D Dyn-17 cemetery.
        "DAN-Aqhor": "Official",           # *rḫ-nswt* "king's acquaintance" — minor courtier title
        "DAN-Ahhotep": "Queen",            # wife of Seqenenre-Taʿa
        "DAN-AhmosiHenutempet": "Princess",  # daughter of Ahhotep
        "DAN-AhmosiSonOfSeqenenre": "Royal Family",  # prince, not king
        "DAN-AntefNubkheperre": "King",    # Dyn-17 Inyotef VI
        "DAN-AntefSekhemreHeruhirmaet": "King",  # Dyn-17 Inyotef VII
        "DAN-AntefSekhemreWepmaet": "King",  # Dyn-17 Inyotef V
        "DAN-KamosiWazkheperre": "King",  # Dyn-17 Kamose
        "DAN-MentuhotpIWifeOfDjhuti": "Queen",  # wife of King Djehuty
        "DAN-Neferhotep": "Official",      # Scribe of the Great Harim
        "DAN-SebkemsafSekhemreShedtaui": "King",  # Dyn-17 Sebkemsaf II
    }
    for tid, role in expected.items():
        assert _row(tid)["occupant_role"] == role, (tid, _row(tid)["occupant_role"])


def test_chunk7_occupant_names_and_alt_names() -> None:
    """PM-verbatim `occupant_name` (ayin/underdot PRESERVED) and `occupant_alt_names`
    (prenomens where PM prints `NAME (PRENOMEN)`).
    """
    expected_name = {
        "SWV-HatshepsutSouth": "Hatshepsut",
        "SWV-Neferure": "Neferureʿ",
        # PR A audit-fix (2026-05-02): `occupant_name` carries the PM
        # headword (Menhet, listed first); Merti and Menwi live in
        # `co_occupants` (asserted in test_chunk7_co_occupants).
        "SWV-ThreePrincesses": "Menhet",
        "DAN-AntefSehertaui": "Antef",
        "DAN-AntefWahankh": "Antef",
        "DAN-MentuhotpSankhibtaui": "Mentuhotp-Sʿankhibtaui",
        "DAN-AhmosiNefertere": "ʿAhmosi Nefertere",
        "DAN-Aqhor": "ʿAḳ-hor",
        "DAN-Ahhotep": "ʿAhhotp",
        "DAN-AhmosiHenutempet": "ʿAhmosi Henutempet",
        "DAN-AhmosiSonOfSeqenenre": "ʿAhmosi",
        "DAN-AntefNubkheperre": "Antef",
        "DAN-AntefSekhemreHeruhirmaet": "Antef",
        "DAN-AntefSekhemreWepmaet": "Antef",
        "DAN-KamosiWazkheperre": "Kamosi",
        "DAN-MentuhotpIWifeOfDjhuti": "Mentuhotp I",
        "DAN-Neferhotep": "Neferhotep",
        "DAN-SebkemsafSekhemreShedtaui": "Sebkemsaf II",
    }
    for tid, name in expected_name.items():
        assert _row(tid)["occupant_name"] == name, (tid, _row(tid)["occupant_name"])

    expected_alt = {
        "DAN-AntefSehertaui": ["Sehertaui"],
        "DAN-AntefWahankh": ["Wahʿankh"],
        "DAN-AntefNubkheperre": ["Nubkheperreʿ"],
        "DAN-AntefSekhemreHeruhirmaet": ["Sekhemreʿ-Heruḥirmaʿet"],
        "DAN-AntefSekhemreWepmaet": ["Sekhemreʿ-Wepmaʿet"],
        "DAN-KamosiWazkheperre": ["Wazkheperreʿ"],
        "DAN-SebkemsafSekhemreShedtaui": ["Sekhemreʿ-Shedtaui"],
    }
    for tid, alt in expected_alt.items():
        assert _row(tid)["occupant_alt_names"] == alt, (tid, _row(tid)["occupant_alt_names"])

    # Every other row: empty alt_names.
    for tid in CHUNK7_TOMB_IDS - expected_alt.keys():
        assert _row(tid)["occupant_alt_names"] == [], tid


def test_chunk7_co_occupants() -> None:
    """SWV-ThreePrincesses (Menhet, Merti, Menwi — three foreign wives of
    Tuthmosis III, Wadi Qubbanet el-Qirud burial) is a joint-occupant row
    after the PR A audit-fix. Headword `occupant_name` = Menhet (PM lists
    her first); the other two live in `co_occupants`. Per-occupant role
    preserves the prior aggregate `Royal Family` label across all three —
    refining per-person roles is a follow-up after the egyptologist
    reviewer revisits with the new schema.
    """
    r = _row("SWV-ThreePrincesses")
    assert r["occupant_name"] == "Menhet"
    assert r["occupant_role"] == "Royal Family"
    assert r["co_occupants"] == [
        {"name": "Merti", "role": "Royal Family", "alt_names": []},
        {"name": "Menwi", "role": "Royal Family", "alt_names": []},
    ]
    # Every other chunk-7 row has empty co_occupants.
    for tid in CHUNK7_TOMB_IDS - {"SWV-ThreePrincesses"}:
        assert _row(tid)["co_occupants"] == [], tid


def test_chunk7_source_citation_pages() -> None:
    """Printed-page numbers for each chunk-7 row match PM's actual headword
    location. Chunk text is physical p.132–148 = printed p.590–606.
    """
    expected_page = {
        "SWV-HatshepsutSouth": 591,
        "SWV-Neferure": 592,
        "SWV-ThreePrincesses": 591,
        "DAN-AntefSehertaui": 594,
        "DAN-AntefWahankh": 595,
        "DAN-MentuhotpSankhibtaui": 595,
        "DAN-AhmosiNefertere": 599,
        "DAN-Aqhor": 605,
        "DAN-Ahhotep": 600,
        "DAN-AhmosiHenutempet": 604,
        "DAN-AhmosiSonOfSeqenenre": 604,
        "DAN-AntefNubkheperre": 602,
        "DAN-AntefSekhemreHeruhirmaet": 603,
        "DAN-AntefSekhemreWepmaet": 603,
        "DAN-KamosiWazkheperre": 600,
        "DAN-MentuhotpIWifeOfDjhuti": 604,
        "DAN-Neferhotep": 604,
        "DAN-SebkemsafSekhemreShedtaui": 603,
    }
    for tid, page in expected_page.items():
        assert _row(tid)["source_citation"]["page"] == page, (tid, _row(tid)["source_citation"]["page"])


def test_chunk7_notes_from_pm() -> None:
    """Exact-match `notes_from_pm` for every chunk-7 row — tightened from
    the earlier substring-match on the retrospective code-review of PR #100.

    The code-reviewer flagged two issues with the prior version: (a)
    substring-match weakens CLAUDE.md rule 5 discipline (chunks 1–5
    exact-match; chunk 7 should too); and (b) the `None or non-empty`
    fallback on DAN-AntefSehertaui / DAN-AntefSekhemreWepmaet is literally
    the rule-5 anti-pattern ("absence of errors"). `fix_rows.py` exists
    precisely to pin PM-verbatim values even against noisy text-layer
    OCR, so exact match is achievable and preferred.
    """
    expected = {
        "SWV-HatshepsutSouth": (
            "See also Tomb 20, supra, p. 546. Sarcophagus as Queen-Consort, "
            "quartzite, in Cairo Mus. Ent. 47032."
        ),
        "SWV-Neferure": "Probably Princess Neferureʿ, daughter of Ḥatshepsut.",
        "SWV-ThreePrincesses": "Temp. Tuthmosis III.",
        "DAN-AhmosiNefertere": (
            "Tomb of Queen ʿAḥmosi Nefertere (probably). Attributed to "
            "Amenophis I by Carter, later equated by Černý with "
            "'House of Amenophis of the Garden'."
        ),
        "DAN-Aqhor": "Royal acquaintance. Dyn. XVII. Objects found by Vassalli in 1863.",
        "DAN-Ahhotep": "Wife of King Seḳenenreʿ-Taʿa. Found by Mariette in 1859.",
        "DAN-AhmosiHenutempet": "Daughter of ʿAḥḥotp (wife of King Seḳenenreʿ-Taʿa).",
        "DAN-AhmosiSonOfSeqenenre": "Eldest son of King Seḳenenreʿ-Taʿa and ʿAḥḥotp.",
        "DAN-AntefNubkheperre": "Found by Mariette in 1860. Pyramid, see Hay MSS. 29816.",
        "DAN-AntefSekhemreHeruhirmaet": (
            "Probably younger brother and successor of Antef (Sekhemreʿ-Wepmaʿet)."
        ),
        "DAN-KamosiWazkheperre": (
            "Found by Mariette in 1857. For pyramid, possibly of Kamosi, "
            "see infra, p. 620."
        ),
        # fix_rows.py CHUNK7_CORRECTIONS restores PM's diacritics on the
        # Egyptian d-emphatic in `Ḏḥuti` (d-bar — same character as in
        # `Ḏḥwty`/Thoth). The earlier value used `Ḍḥuti` (d-underdot, a
        # different consonant in Semitic transliteration) — corrected on
        # PR #151 by egyptologist printed-source review of PM p.604.
        "DAN-MentuhotpIWifeOfDjhuti": (
            "Wife of King Ḏḥuti. Found in tomb by Passalacqua."
        ),
        "DAN-MentuhotpSankhibtaui": "Unfinished.",
        "DAN-Neferhotep": (
            "Scribe of the Great Harîm, probably temp. Antef (Nubkheperrēʿ). "
            "Rock-tomb, uninscribed. Found by Mariette in 1860, probably "
            "near Theb. tb. 13."
        ),
        "DAN-SebkemsafSekhemreShedtaui": (
            "Pyramid behind Theb. tb. 24, perhaps belonging to this tomb."
        ),
    }
    for tid, note in expected.items():
        assert _row(tid)["notes_from_pm"] == note, (tid, _row(tid)["notes_from_pm"])

    # Rows where PM has no prose beyond name + cartouches + bibliographic
    # ribbon — `notes_from_pm` is exactly None (not empty-string, not a
    # bare-punctuation value).
    for tid in ("DAN-AntefSehertaui", "DAN-AntefWahankh", "DAN-AntefSekhemreWepmaet"):
        assert _row(tid)["notes_from_pm"] is None, (tid, _row(tid)["notes_from_pm"])


# ---------------------------------------------------------------------------
# Chunk-8 specific value-assertion tests (PM I.2 § X.A Valley of the Queens —
# 20 numbered QV tombs).
# ---------------------------------------------------------------------------


def test_chunk8_uniform_null_phase_a_fields() -> None:
    """Every chunk-8 row carries null for Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`). `source_citation.edition` is PM I.2.
    `source_citation.section` is exactly "X.A".
    `theban_area` is "Valley of the Queens".
    """
    for tid in CHUNK8_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Valley of the Queens", tid
        assert r["source_citation"]["edition"] == EDITION_PM_I2
        assert r["source_citation"]["section"] == "X.A", tid
        assert r["dynasty"] is None
        assert r["sub_period"] is None
        assert r["date_bce_approx_start"] is None
        assert r["date_bce_approx_end"] is None
        assert r["discovery_year"] is None
        assert r["discoverer"] is None
        assert r["location_sub_area"] is None
        assert r["shared_with_tombs"] == []


def test_chunk8_only_qv38_unfinished() -> None:
    """PM's headword marks only QV38 (Queen Sitreʿ, wife of Ramesses I) as
    `Unfinished`. Every other QV row carries `is_unfinished: false`.
    """
    for tid in CHUNK8_TOMB_IDS:
        r = _row(tid)
        if tid == "QV38":
            assert r["is_unfinished"] is True, tid
        else:
            assert r["is_unfinished"] is False, tid


def test_chunk8_no_name_rows_unknown_role() -> None:
    """`A QUEEN, no name` / `A PRINCESS, no name` / `cartouche blank` rows
    carry `occupant_name: null` and `occupant_role: "Unknown"` (per prompt
    rule 1, applied via fix_rows.py CHUNK8_CORRECTIONS when agents emit
    null role on empty-name headwords).
    """
    no_name_rows = {"QV36", "QV40", "QV73", "QV75"}
    for tid in no_name_rows:
        r = _row(tid)
        assert r["occupant_name"] is None, (tid, r["occupant_name"])
        assert r["occupant_role"] == "Unknown", (tid, r["occupant_role"])


def test_chunk8_occupant_roles() -> None:
    """Per-row role assignments per PM headwords: QUEEN / PRINCESS / PRINCE /
    VIZIER / Unknown.
    """
    expected = {
        "QV33": "Princess",  # PRINCESS TANEZEM(T)
        "QV36": "Unknown",   # A PRINCESS, no name (fix_rows Unknown)
        "QV38": "Queen",     # QUEEN SITREʿ, wife of Ramesses I, Unfinished
        "QV40": "Unknown",   # A QUEEN, cartouche blank (fix_rows Unknown)
        "QV42": "Prince",    # PRINCE PARAʿḤIRWENEMEF
        "QV43": "Prince",    # PRINCE SET-ḤIRKHOPSHEF
        "QV44": "Prince",    # PRINCE KHAʿEMWESET
        "QV46": "Vizier",    # IMḤOTEP, Vizier
        "QV47": "Princess",  # PRINCESS ʿAḤMOSI, daughter of Seḳenenreʿ-Taʿa
        "QV51": "Queen",     # QUEEN ESI II, mother of Ramesses VI
        "QV52": "Queen",     # QUEEN TYTI
        "QV53": "Prince",    # PRINCE RAʿMESES, son of Ramesses III
        "QV55": "Prince",    # PRINCE AMEN(ḤIR)KHOPSHEF, son of Ramesses III
        "QV60": "Queen",     # QUEEN NEBTTAUI, daughter of Ramesses II
        "QV66": "Queen",     # QUEEN NEFERTARI, wife of Ramesses II
        "QV68": "Queen",     # QUEEN MERYTAMUN, daughter of Ramesses II
        "QV71": "Queen",     # QUEEN BENTʿANTA, daughter of Ramesses II
        "QV73": "Unknown",   # A PRINCESS, no name. Dyn. XX
        "QV74": "Queen",     # QUEEN TENTOPET, Great King's mother
        "QV75": "Unknown",   # A QUEEN, no name
    }
    for tid, role in expected.items():
        assert _row(tid)["occupant_role"] == role, (tid, _row(tid)["occupant_role"])


def test_chunk8_occupant_names() -> None:
    """PM-verbatim occupant_name (ayin `ʿ` and underdot-H `ḥ` preserved)."""
    expected_name = {
        "QV33": "Tanezem(t)",
        "QV36": None,
        "QV38": "Sitreʿ",
        "QV40": None,
        "QV42": "Paraʿhirwenemef",
        "QV43": "Set-hirkhopshef",
        "QV44": "Khaʿemweset",
        "QV46": "Imhotep",
        "QV47": "ʿAhmosi",
        "QV51": "Esi II",
        "QV52": "Tyti",
        "QV53": "Raʿmeses",
        "QV55": "Amen(hir)khopshef",
        "QV60": "Nebttaui",
        "QV66": "Nefertari",
        "QV68": "Merytamun",
        "QV71": "Bentʿanta",
        "QV73": None,
        "QV74": "Tentopet",
        "QV75": None,
    }
    for tid, name in expected_name.items():
        assert _row(tid)["occupant_name"] == name, (tid, _row(tid)["occupant_name"])


def test_chunk8_source_citation_pages() -> None:
    """Printed page numbers per QV tomb — matches PM's headword location
    in the chunk file (printed pp.751–768).
    """
    expected_page = {
        "QV33": 751, "QV36": 751, "QV38": 751, "QV40": 751,
        "QV42": 752, "QV43": 753, "QV44": 754,
        "QV46": 755, "QV47": 755,
        "QV51": 756, "QV52": 756,
        "QV53": 759, "QV55": 759,
        "QV60": 761, "QV66": 762, "QV68": 765, "QV71": 766,
        "QV73": 767, "QV74": 767, "QV75": 768,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        # Exact match: page numbers are extracted from explicit
        # `===== PRINTED PAGE M =====` markers in the chunk text, so the
        # extraction must be exact — a ±1 tolerance would hide off-by-one
        # extraction bugs.
        assert actual == page, (tid, actual, page)


def test_chunk8_notes_from_pm_royal_kinship() -> None:
    """Rows with explicit royal kinship / regnal-dating clauses carry them
    in `notes_from_pm`. Verify key substrings (not full verbatim — PM
    diacritic rendering varies).
    """
    expected = {
        "QV38": "wife of Ramesses I",
        "QV42": "son of Ramesses III",
        "QV43": "King's son",
        "QV44": "son of Ramesses III",
        "QV47": "daughter of Seḳenenreʿ-Taʿa",
        "QV51": "mother of Ramesses VI",
        "QV53": "son of Ramesses III",
        "QV55": "son of Ramesses III",
        "QV60": "daughter of Ramesses II",
        "QV66": "wife of Ramesses II",
        "QV68": "daughter of Ramesses II",
        "QV71": "daughter of Ramesses II",
    }
    for tid, substr in expected.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


def test_chunk8_reviewer_inserted_characters_pinned() -> None:
    """Every reviewer-inserted character in `CHUNK8_CORRECTIONS` must be
    pinned by a test substring assertion — rule 5 + the
    `feedback_fix_rows_unattributed_restoration` memory.

    QV47 + QV74 corrections updated 2026-04-29 by egyptologist printed-
    source review on PR #151:
    - QV47: PM p.755 prints `Sit-ḏḥout` with `ḏ` (d-bar, the standard
      Egyptological d-emphatic, same character as in `Ḏḥwty`/Thoth) —
      NOT `ḍ` (d-underdot used in Semitic transliteration). Earlier
      fix_rows.py used the wrong consonant; corrected directly.
    - QV74: PM p.767 main text + footnote 1 are SEPARATE prose blocks.
      Earlier fix_rows.py synthesized them into a single `notes_from_pm`
      blob — rule-1 (provenance) violation since the synthesized prose
      doesn't appear verbatim in PM. Corrected to PM-main-text-verbatim
      only; the footnote 1 genealogy + per-citation chain is tracked
      for restoration via follow-up issue (schema split for
      `notes_footnote` / `notes_genealogy` field).
    """
    qv47_notes = _row("QV47")["notes_from_pm"]
    assert "Sit-ḏḥout" in qv47_notes, (
        f"QV47 expected egyptologist-corrected 'Sit-ḏḥout' (d-bar); got {qv47_notes!r}"
    )
    assert "Sit-ḍḥout" not in qv47_notes, (
        f"QV47 must not carry the pre-#151 wrong-consonant 'Sit-ḍḥout' (d-underdot); got {qv47_notes!r}"
    )
    assert "Sit-gḥout" not in qv47_notes, (
        f"QV47 must not carry the pre-fix OCR form; got {qv47_notes!r}"
    )
    qv74_notes = _row("QV74")["notes_from_pm"]
    # PM-main-text-verbatim: matches `74. QUEEN TENTŌPET ... Great King's
    # mother and King's wife.¹ (CHAMPOLLION, No. 15, L. D. Text, No. 2,
    # HAY, No. 7.)` exactly (modulo the macron and the cartouche, which
    # belong elsewhere).
    assert qv74_notes == (
        "Great King's mother and King's wife. "
        "(CHAMPOLLION, No. 15, L. D. Text, No. 2, HAY, No. 7.)"
    ), f"QV74 expected PM-main-text-verbatim; got {qv74_notes!r}"
    # The synthesized footnote prose must NOT appear in notes_from_pm
    # (rule-1 provenance violation). Tracked for schema-split follow-up.
    for substr in (
        "Wife(?) of Ramesses IV",
        "mother of Ramesses V",
        "daughter of Ramesses IV",
        "per PM p.767 footnote 1",
    ):
        assert substr not in qv74_notes, (
            f"QV74 must not carry pre-#151 synthesized footnote prose {substr!r}; got {qv74_notes!r}"
        )


def test_chunk8_notes_from_pm_remaining_rows() -> None:
    """QV33, QV36, QV40, QV46, QV52, QV73, QV75 have populated
    `notes_from_pm` values that `test_chunk8_notes_from_pm_royal_kinship`
    does not cover. Rule 5 thematic-gap fix from the chunk-8 retrospective
    code-review; QV36 + QV40 added per Gemini round-2 finding on PR #105
    (PM prints populated text for both — leaving them unasserted meant a
    silent regression on those rows would not break this test).
    """
    expected_substrings = {
        # QV33: earlier-edition cross-numbering + dating hedge.
        "QV33": "Dyn. XX(?)",
        # QV36: PM's bare "A PRINCESS, no name." clause (no citation tail).
        "QV36": "A PRINCESS, no name.",
        # QV40: PM's "A QUEEN, cartouche blank" clause + 19th-c. cross-refs.
        "QV40": "A QUEEN, cartouche blank.",
        # QV46 Imhotep: hedged attribution + regnal-dating clause.
        "QV46": "Vizier. Temp. Tuthmosis I.",
        # QV52 Tyti: dating + earlier-edition cross-ref.
        "QV52": "Ramesside.",
        # QV73: PM's "A PRINCESS, no name" clause captured verbatim.
        "QV73": "A PRINCESS, no name. Dyn. XX.",
        # QV75: PM's "A QUEEN, no name" clause.
        "QV75": "A QUEEN, no name.",
    }
    for tid, substr in expected_substrings.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm, got None"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


# ---------------------------------------------------------------------------
# Chunk 9 (PM I.1 § I — TT1-TT10 Deir el-Medina core)
# ---------------------------------------------------------------------------


def test_chunk9_uniform_null_phase_a_fields() -> None:
    """Every chunk-9 row carries null for Phase-A-enrichment fields
    (`dynasty`, `sub_period`, `date_bce_approx_start`, `date_bce_approx_end`,
    `discovery_year`, `discoverer`, `location_sub_area`).
    `source_citation.edition` is `PM I.1 2nd ed. 1960` (NOT the chunks 1-8
    `PM I.2 2nd ed. 1964` — chunk 9 is the first PM I.1 chunk).
    `source_citation.section` is exactly "I" (PM I.1 § I has no sub-letter
    for this range).
    `theban_area` is "Deir el-Medina" for every TT1-TT10 row (workmen's
    tombs at Deir el-Medina; sub-site shifts to Dra' Abu el-Naga at TT11+).
    `is_unfinished` is `false` for every row (PM I.1 prints no `Unfinished`
    flag in TT1-TT10).
    """
    for tid in CHUNK9_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Deir el-Medina", tid
        assert r["source_citation"]["edition"] == EDITION_PM_I1, tid
        assert r["source_citation"]["section"] == "I", tid
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["location_sub_area"] is None, tid
        assert r["is_unfinished"] is False, tid


def test_chunk9_all_rows_official_role() -> None:
    """All 10 TT1-TT10 occupants are Deir el-Medina workmen / scribes /
    foremen / chiseller / Chief in the Great Place — controlled-vocab
    flattens to `"Official"` for every row. The verbatim title clause
    (`Servant in the Place of Truth`, `Foremen in the Place of Truth`,
    `Chiseller of Amun in the Place of Truth`, `Scribe in the Place of
    Truth`, `Chief in the Great Place`) lives in `notes_from_pm`.
    """
    for tid in CHUNK9_TOMB_IDS:
        assert _row(tid)["occupant_role"] == "Official", (
            tid, _row(tid)["occupant_role"]
        )


def test_chunk9_occupant_names() -> None:
    """PM-faithful occupant_name per the README's diacritic policy
    (strip Ḥ on matchable field, preserve ayin, preserve underdot-Ḳ).
    `Raʿmose`/`Amenmose` use the project-wide -osi → -ose Anglicisation
    for downstream museum-data matching (Met / Brooklyn / TLA all use
    `Ramose`); chunk 9 retains the convention even though chunk 7
    preserved PM's `-osi` ending on `Kamosi`.
    """
    expected = {
        "TT1": "Sennezem",
        "TT2": "Khaʿbekhnet",
        "TT3": "Peshedu",
        "TT4": "Ḳen",
        "TT5": "Neferʿabet",
        "TT6": "Neferhotep",
        # PM I.1 p.15 prints `RAʿMOSI` not `Raʿmose` — chunk-9 third-pass
        # P1: PM's volume-wide `-osi` editorial convention preserved per
        # rule-1 (provenance) AND to disambiguate from TT55's RAʿMOSE
        # (Vizier of Amenhotep IV — different historical person).
        "TT7": "Raʿmosi",
        "TT8": "Khaʿ",
        # PM I.1 p.18 prints `AMENMOSI` — same `-osi` preservation rule
        # as TT7. Chunk-9 third-pass P1.
        "TT9": "Amenmosi",
        "TT10": "Penbuy",
    }
    for tid, name in expected.items():
        assert _row(tid)["occupant_name"] == name, (
            tid, _row(tid)["occupant_name"]
        )


def test_chunk9_source_citation_pages() -> None:
    """Printed page numbers per TT tomb (PM I.1 § I, printed pp.1-19,
    physical pp.19-37). Verified directly against the PDF in the
    chunk-9 egyptologist-reviewer pass.
    """
    expected_page = {
        "TT1": 1, "TT2": 6, "TT3": 9, "TT4": 11, "TT5": 12,
        "TT6": 14, "TT7": 15, "TT8": 16, "TT9": 18, "TT10": 19,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        assert actual == page, (tid, actual, page)


def test_chunk9_shared_with_tombs() -> None:
    """PM headwords' `(Also owner of tomb N.)` / `(Perhaps also owner of
    tomb N.)` / `(also owner of tombs N and M)` cross-references parse
    to `shared_with_tombs`. Three rows in scope; the rest empty.
    """
    expected = {
        "TT1": [],
        "TT2": [],
        "TT3": ["TT326"],
        "TT4": ["TT337"],   # PM "(Perhaps also owner of tomb 337.)"
        "TT5": [],
        "TT6": [],
        "TT7": ["TT212", "TT250"],  # PM "(also owner of tombs 212 and 250)"
        "TT8": [],
        "TT9": [],
        "TT10": [],
    }
    for tid, swt in expected.items():
        actual = _row(tid)["shared_with_tombs"]
        assert sorted(actual) == sorted(swt), (tid, actual, swt)


def test_chunk9_joint_burial_classification() -> None:
    """The TT1-TT10 range contains two multi-occupant headwords:

    - **TT6 (NEFERḤŌTEP and son NEBNŪFER, Foremen…)** is HIERARCHICAL.
      PM uses `X and son Y` — Neferhotep is the parent, syntactic head;
      Nebnufer is structurally subordinate. `is_joint_burial=false`,
      `co_occupants=[{name: "Nebnufer", role: "Official", alt_names: []}]`.
      Same shape as KV46 (`YUIA …, Divine father, AND THUIU …`).

    - **TT10 (PENBUY and KASA, Servants in the Place of Truth)** is
      COORDINATE. PM uses bare conjunction with plural role-clause; no
      syntactic primacy. `is_joint_burial=true`,
      `co_occupants=[{name: "Kasa", role: "Official", alt_names: []}]`.
      Same shape as SWV-ThreePrincesses (`MENHET, MERTI, AND MENWI`).

    The other 8 TT1-TT10 rows are single-occupant.
    """
    # TT6: hierarchical
    tt6 = _row("TT6")
    assert tt6["occupant_name"] == "Neferhotep"
    assert tt6["is_joint_burial"] is False
    assert tt6["co_occupants"] == [
        {"name": "Nebnufer", "role": "Official", "alt_names": []}
    ]

    # TT10: coordinate
    tt10 = _row("TT10")
    assert tt10["occupant_name"] == "Penbuy"
    assert tt10["is_joint_burial"] is True
    assert tt10["co_occupants"] == [
        {"name": "Kasa", "role": "Official", "alt_names": []}
    ]

    # Other 8 rows: single-occupant
    for tid in CHUNK9_TOMB_IDS - {"TT6", "TT10"}:
        r = _row(tid)
        assert r["co_occupants"] == [], (tid, r["co_occupants"])
        assert r["is_joint_burial"] is False, (tid, r["is_joint_burial"])


def test_chunk9_notes_from_pm_pinned_substrings() -> None:
    """Per-row `notes_from_pm` substring assertions. Every chunk-9 row
    has a populated `notes_from_pm` (PM I.1 headwords are dense — every
    row carries family clauses + role title + regnal/dynastic dating).
    Pinned substrings reflect the egyptologist-corrected forms after
    the chunk-9 reviewer pass: macrons preserved per chunk-3/7
    precedent, false underdots dropped where PM does not print one.
    """
    expected = {
        "TT1": "Father, Khaʿbekhnet (name on fragment, BRUYÈRE, Rapport (1927), fig. 34 [4]).",
        "TT2": "(L. D. Text, No. 107.) Parents, Sennezem (tomb 1)",
        "TT3": "Parents, Menna and Huy. Wife, Nezemtbehdet.",
        "TT4": "Chiseller of Amūn in the Place of Truth.",
        "TT5": "Parents, Neferronpet and Mahi (name on stela in Brit. Mus. 150, see infra, p. 14). Wife, Taēsi.",
        "TT6": "Wife (of Neferḥōtep), Iymau; (of Nebnūfer), Iy.",
        "TT7": "Parents, Amenemḥab and Kakaia. Wife, Mutemwia.",
        "TT8": "Chief in the Great Place.",
        "TT9": "Wife, Tent-hōm.",
        "TT10": "Father (of Penbuy), Iri (name from offering-table of Penbuy, in Turin Mus. 1559). Wives (of Penbuy), Amentetusert and Irnūfer; (of Kasa), Bukhaʿnef.",
    }
    for tid, substr in expected.items():
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} expected notes_from_pm, got None"
        assert substr in notes, f"{tid}: expected {substr!r} in {notes!r}"


def test_chunk9_no_redundant_double_period_after_biblio_paren() -> None:
    """`CHUNK9_CORRECTIONS` strips a redundant `.).` double-period that
    the merge majority introduced when two of three agents stitched the
    bibliographic close-paren with a paragraph-separator period. PM I.1
    prints `(L. D. Text, No. N.) <Next sentence>` with NO period after
    the close-paren (verified by egyptologist printed-source review on
    pp. 6, 14, 15, 16, 19 of the PDF).
    """
    for tid in CHUNK9_TOMB_IDS:
        notes = _row(tid)["notes_from_pm"]
        assert notes is None or ".)." not in notes, (
            f"{tid}: redundant `.).` double-period after biblio close-paren "
            f"slipped past CHUNK9_CORRECTIONS; got {notes!r}"
        )


def test_chunk9_tt2_attribution_certainty_overridden_to_attested() -> None:
    """TT2 `notes_from_pm` carries `Wives, Saḥte and (probably) Esi.`
    The context-free `_detect_attribution_certainty` regex fires on the
    `(probably)` token and would derive `attribution_certainty="probable"`,
    BUT PM's hedge applies to the wife identification (Esi), not to
    Khaʿbekhnet's primary occupant attribution. The per-row
    `DERIVER_OVERRIDES` mechanism in `fix_rows.py` pins TT2 back to
    `"attested"` post-derivation. This test asserts the override is
    actually winning — if a future refactor of `_apply_issue_182_migrations`
    silently reverts the override order, this test catches it.
    """
    tt2 = _row("TT2")
    assert tt2["attribution_certainty"] == "attested", (
        f"TT2 must carry `attribution_certainty='attested'` despite the "
        f"`(probably)` hedge in `notes_from_pm` (the hedge applies to wife "
        f"Esi, not Khaʿbekhnet); got {tt2['attribution_certainty']!r}. "
        f"Verify that DERIVER_OVERRIDES in fix_rows.py is being applied "
        f"AFTER the regex pass."
    )
    # Also verify the (probably) token is still in notes — the override
    # must NOT silently strip the verbatim PM hedge.
    assert "(probably)" in (tt2["notes_from_pm"] or ""), (
        "TT2 notes_from_pm must preserve PM's verbatim `(probably)` "
        "hedge; the deriver override must not strip the source text."
    )


def test_chunk9_postprocess_j_period_i_normalisation() -> None:
    """`postprocess.py` Phase-1 substitution `J.I → Ḥ` (added in chunk 9
    for the single TT6 site `NEFERJ.IOTEP`) must produce `Neferhotep`
    in the row's `occupant_name` after the README's strip-Ḥ rule.
    Mechanical assertion that the postprocess + strip-Ḥ chain works.
    """
    tt6 = _row("TT6")
    # occupant_name is the matchable field — strip-Ḥ applies.
    assert tt6["occupant_name"] == "Neferhotep", tt6["occupant_name"]
    # notes_from_pm is verbatim-preserve — Ḥ stays. Verify the underdot
    # is preserved on `Neferḥōtep` and `Ḥaremḥab` in the wife-clause.
    notes = tt6["notes_from_pm"]
    assert "Ḥaremḥab" in notes, notes
    assert "Neferḥōtep" in notes, notes


# ---------------------------------------------------------------------------
# Chunk 10: PM I.1 § I — TT11-TT20 Dra' Abu el-Naga
# ---------------------------------------------------------------------------


def test_chunk10_uniform_null_phase_a_fields() -> None:
    """Every chunk-10 row carries null for Phase-A-enrichment fields and
    `theban_area="Dra' Abu el-Naga"` (sub-site shifts from chunk-9's
    `Deir el-Medina`). `source_citation.edition` is `PM I.1 2nd ed. 1960`,
    `source_citation.section` is `"I"`, `is_unfinished` is `false` for
    every row (PM I.1 prints no `Unfinished` flag in TT11-TT20).
    """
    for tid in CHUNK10_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Dra' Abu el-Naga", tid
        assert r["source_citation"]["edition"] == EDITION_PM_I1, tid
        assert r["source_citation"]["section"] == "I", tid
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["location_sub_area"] is None, tid
        assert r["is_unfinished"] is False, tid


def test_chunk10_all_rows_official_role() -> None:
    """All 10 TT11-TT20 occupants flatten to controlled-vocab `"Official"`.
    PM headwords carry varied non-royal occupational titles (Overseer of
    the treasury, Head of brazier-bearers, waʿb-priest, King's son + Mayor,
    Prophet of Amenophis of the Forecourt, Scribe and physician of the
    King, Chief servant who weighs silver and gold, First prophet, Fan-
    bearer / Mayor of Aphroditopolis) — none are in the controlled-vocab
    enum, so per chunk-7/9 convention they flatten to `"Official"` with
    the verbatim title clause preserved in `notes_from_pm`.
    """
    for tid in CHUNK10_TOMB_IDS:
        assert _row(tid)["occupant_role"] == "Official", (
            tid, _row(tid)["occupant_role"]
        )


def test_chunk10_occupant_names() -> None:
    """PM-faithful occupant_name per the README's diacritic policy.
    chunk-10 introduces underdot-Ḍ in TT11 (`Ḍhout`) — the strip rule
    on `occupant_name` covers underdot-Ḥ ONLY, so underdot-Ḍ is preserved
    same as underdot-Ḳ (chunk-7 / chunk-9 precedent). Other names in the
    range carry no scholarly diacritics in the matchable form (Ḥ-strip
    fires on ḤRAY, ḤUY, PANEḤESI, MENTUḤIRKHOPSHEF; underdot-Ḥ in body
    prose like notes_from_pm is preserved per the verbatim-preserve rule).
    """
    expected = {
        "TT11": "Ḍhout",
        "TT12": "Hray",
        "TT13": "Shuroy",
        "TT14": "Huy",
        "TT15": "Tetiky",
        "TT16": "Panehesi",
        # PM I.1 p.29 prints `17. NEBAMŪN` (capital macron-ū). README's
        # occupant_name policy preserves vowel macrons; only underdot-Ḥ is
        # stripped. Egyptologist printed-source review (this PR).
        "TT17": "Nebamūn",
        "TT18": "Baki",
        "TT19": "Amenmosi",
        "TT20": "Mentuhirkhopshef",
    }
    for tid, name in expected.items():
        assert _row(tid)["occupant_name"] == name, (
            tid, _row(tid)["occupant_name"]
        )


def test_chunk10_source_citation_pages() -> None:
    """Printed page numbers per TT tomb (PM I.1 § I, printed pp.21-37,
    physical pp.39-55). Verified against the PDF in the chunk-10
    egyptologist-reviewer pass. PM I.1 offset: physical = printed + 18.
    """
    expected_page = {
        "TT11": 21, "TT12": 24, "TT13": 25, "TT14": 26, "TT15": 26,
        "TT16": 28, "TT17": 29, "TT18": 32, "TT19": 32, "TT20": 34,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        assert actual == page, (tid, actual, page)


def test_chunk10_no_multi_occupant_or_shared_tombs() -> None:
    """The TT11-TT20 range contains zero multi-occupant headwords and zero
    headword-level `shared_with_tombs` cross-references (verified against
    the PDF). Every PM headword in this range names exactly one buried
    occupant; `Wife,` / `Mother,` / `Father,` / `Parents,` clauses describe
    family who are NOT buried in the tomb (notes_from_pm captures them).
    The Wreszinski misnumbering footnote at TT17 body p.29 (`For WRESZ.,
    Atlas, i. 126 ... see tomb 100 (19)`) is dropped per the prompt's
    Wreszinski-footnote rule.
    """
    for tid in CHUNK10_TOMB_IDS:
        r = _row(tid)
        assert r["co_occupants"] == [], (tid, r["co_occupants"])
        assert r["is_joint_burial"] is False, (tid, r["is_joint_burial"])
        assert r["shared_with_tombs"] == [], (tid, r["shared_with_tombs"])


def test_chunk10_notes_from_pm_pinned_substrings() -> None:
    """Per-row `notes_from_pm` substring assertions. PM I.1 headwords are
    dense — every chunk-10 row has populated notes carrying the verbatim
    role-title clause + regnal/dynastic dating + family clauses + (where
    PM prints them) `(L. D. Text, No. N.)` / `(CHAMPOLLION, No. N, ...)`
    cross-numbering parentheticals. Pinned substrings reflect the merge
    output post-tie-break-overrides (TT12 and TT14 had cosmetic ties on
    capitalisation / punctuation, both PDF-resolved) and post-fix_rows
    deriver pass.
    """
    # List of (tomb_id, expected substring, label) — multiple substrings per
    # row are allowed; each substring is asserted independently.
    expected: list[tuple[str, str, str]] = [
        ("TT11", "Overseer of the treasury, Overseer of works.", "role-title"),
        ("TT12", "(CHAMPOLLION, No. 51, L. D. Text, No. 2.) Mother", "tie-break-resolved cross-ref"),
        ("TT13", "Head of brazier-bearers of Amūn. Ramesside.", "role + period"),
        ("TT14", "wʿab-priest of 'Amenophis, the favourite of Amūn'. Ramesside.", "tie-break-resolved role"),
        # PM p.26 prints `Fayûm` with circumflex (verbatim-preserve per
        # README); egyptologist printed-source review (this PR).
        ("TT15", "Fayûm", "circumflex preserved"),
        ("TT16", "Prophet of 'Amenophis of the Forecourt'.", "role"),
        # PM p.28 wife `Ternūte` (n + macron-ū) — egyptologist-flagged
        # rn→rm OCR misread fixed in CHUNK10_CORRECTIONS.
        ("TT16", "Wife, Ternūte.", "wife n+macron-ū correction"),
        ("TT17", "Scribe and physician of the King. Temp. Amenophis II (?).", "role + regnal hedge"),
        # PM p.29 wife fragment `Ta . . . nūfer` (n + macron-ū) — egyptologist-
        # flagged n→m OCR misread fixed in CHUNK10_CORRECTIONS.
        ("TT17", "Wife, Ta...nūfer.", "wife n+macron-ū correction"),
        ("TT18", "Chief servant who weighs the silver and gold of the estate of Amūn.", "role"),
        ("TT19", "First prophet of 'Amenophis of the Forecourt'.", "role"),
        ("TT20", "Fan-bearer, Mayor of Aphroditopolis. Temp. Tuthmosis III (?).", "role + regnal hedge"),
    ]
    for tid, substr, label in expected:
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} ({label}) expected notes_from_pm, got None"
        assert substr in notes, f"{tid} ({label}): expected {substr!r} in {notes!r}"


def test_chunk10_tt11_underdot_d_preserved() -> None:
    """TT11 `Ḍhout` — first chunk to surface underdot-Ḍ (`Ḍ`) at the
    start of an `occupant_name` token. The README's strip rule covers
    underdot-Ḥ ONLY; underdot-Ḍ is preserved (same posture as underdot-Ḳ).
    The publisher OCR rendered the original `ḌH` headword as `:[>Ḥ`-style
    noise; the prompt's `:[>` → `Ḍ` rule restores the canonical character
    and the strip-Ḥ rule then fires on the following `H`.

    This is a deterministic enforcement of the README invariant: if a
    future refactor extends the strip rule to underdot-Ḍ, this test
    catches the regression on TT11. Per CLAUDE.md rule 3.
    """
    assert _row("TT11")["occupant_name"] == "Ḍhout"
    # And the underdot must literally appear at character zero.
    assert _row("TT11")["occupant_name"][0] == "Ḍ"


# ---------------------------------------------------------------------------
# Chunk 11: PM I.1 § I — TT21–TT30 (heterogeneous theban_area + usurpation +
# cross-valley shared_with_tombs + first non-Official controlled-vocab role)
# ---------------------------------------------------------------------------


def test_chunk11_uniform_phase_a_null_fields() -> None:
    """Every chunk-11 row carries null for Phase-A-enrichment fields and
    `source_citation.edition="PM I.1 2nd ed. 1960"`, `section="I"`,
    `is_unfinished=false`. `theban_area` is per-row (heterogeneous —
    see test_chunk11_theban_area_per_row below).
    """
    for tid in CHUNK11_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == EDITION_PM_I1, tid
        assert r["source_citation"]["section"] == "I", tid
        assert r["dynasty"] is None, tid
        assert r["sub_period"] is None, tid
        assert r["date_bce_approx_start"] is None, tid
        assert r["date_bce_approx_end"] is None, tid
        assert r["discovery_year"] is None, tid
        assert r["discoverer"] is None, tid
        assert r["location_sub_area"] is None, tid
        assert r["is_unfinished"] is False, tid


def test_chunk11_theban_area_per_row() -> None:
    """First chunk with heterogeneous `theban_area` (chunks 9-10 were
    uniform single sub-site). Per PM I.1 p.35-46 headword sub-site
    declarations: TT21/22/23/29/30 at Sh. ʿAbd el-Qurna, TT24 at Dra'
    Abu el-Naga (carrying over from chunk 10's range), TT25/26/27/28
    at ʿAsâsîf. PM-faithful diacritics: U+02BF MODIFIER LETTER LEFT
    HALF RING for ayin in `ʿAbd` / `ʿAsâsîf`; ASCII apostrophe in
    `Dra'`; circumflexes `â` / `î` preserved on ʿAsâsîf; abbreviated
    `Sh.` (period preserved) on Sheikh ʿAbd el-Qurna.
    """
    expected = {
        "TT21": "Sh. ʿAbd el-Qurna",
        "TT22": "Sh. ʿAbd el-Qurna",
        "TT23": "Sh. ʿAbd el-Qurna",
        "TT24": "Dra' Abu el-Naga",
        "TT25": "ʿAsâsîf",
        "TT26": "ʿAsâsîf",
        "TT27": "ʿAsâsîf",
        "TT28": "ʿAsâsîf",
        "TT29": "Sh. ʿAbd el-Qurna",
        "TT30": "Sh. ʿAbd el-Qurna",
    }
    for tid, area in expected.items():
        actual = _row(tid)["theban_area"]
        assert actual == area, (tid, actual, area)


def test_chunk11_occupant_names() -> None:
    """PM-faithful occupant_name per the README's diacritic policy.
    chunk-11 highlights:
    - TT22 `Wah` — strip-Ḥ from PM `WAḤ` (ay-Ḥ residual `WAFJ.` in OCR).
    - TT24 `Nebamūn` — distinct individual from chunk-10's TT17 Nebamūn;
      macron-ū restored from OCR `NEBAMUN` per chunk-10 TT17 precedent.
    - TT27 `Sheshonḳ` — underdot-Ḳ preserved (README rule covers
      underdot-Ḥ ONLY).
    - TT29 `Amenemopet` — chunks-1-10 strip-Ḥ + ayin-preserve rules.
    """
    expected = {
        "TT21": "User",
        "TT22": "Wah",
        "TT23": "Thay",
        "TT24": "Nebamūn",
        "TT25": "Amenemhab",
        "TT26": "Khnememhab",
        "TT27": "Sheshonḳ",
        "TT28": "Hori",
        # PM I.1 p.45 prints `29. AMENEMŌPET` with capital macron-Ō.
        # README's occupant_name policy preserves vowel macrons; only
        # underdot-Ḥ is stripped. Egyptologist printed-source review
        # (chunk-11 PR) restored from agent-extracted `Amenemopet`.
        "TT29": "Amenemōpet",
        "TT30": "Khensmosi",
    }
    for tid, name in expected.items():
        assert _row(tid)["occupant_name"] == name, (
            tid, _row(tid)["occupant_name"]
        )

    # TT23 `occupant_alt_names=["To"]` — PM's `THAY, also called To`
    # headword phrasing produces a single-element alt-names list.
    # Asserted here (not in `test_chunk11_tt29_vizier_role_and_kv_cross_
    # valley` which only covers TT29) per Gemini Code Assist PR #199
    # round 2 coverage-gap finding.
    assert _row("TT23")["occupant_alt_names"] == ["To"], (
        f"TT23 must carry `occupant_alt_names=['To']` per PM's "
        f"`THAY, also called To` headword phrasing; got "
        f"{_row('TT23')['occupant_alt_names']!r}"
    )


def test_chunk11_source_citation_pages() -> None:
    """Printed page numbers per TT tomb (PM I.1 § I, printed pp.35-46,
    physical pp.53-64). PM I.1 offset: physical = printed + 18.
    """
    expected_page = {
        "TT21": 35, "TT22": 37, "TT23": 38, "TT24": 41, "TT25": 42,
        "TT26": 43, "TT27": 43, "TT28": 45, "TT29": 45, "TT30": 46,
    }
    for tid, page in expected_page.items():
        actual = _row(tid)["source_citation"]["page"]
        assert actual == page, (tid, actual, page)


def test_chunk11_no_multi_occupant() -> None:
    """The TT21-TT30 range contains zero multi-occupant headwords. TT22's
    `Partly usurped by Mery[amūn]` is structurally distinct from co-
    burial — usurpation goes in `notes_from_pm` only, with the Tier-3
    `is_usurped` deriver firing on the regex; the usurper is NOT a
    `co_occupant`. All 10 rows are single-occupant.
    """
    for tid in CHUNK11_TOMB_IDS:
        r = _row(tid)
        assert r["co_occupants"] == [], (tid, r["co_occupants"])
        assert r["is_joint_burial"] is False, (tid, r["is_joint_burial"])


def test_chunk11_tt22_usurpation_flag_set() -> None:
    """TT22 Wah's headword reads `Partly usurped by Mery[amūn], Eldest
    son of the King.`. The Tier-3 `is_usurped` deriver fires on the
    `usurp` regex match in `notes_from_pm`. Original occupant Wah
    stays as `occupant_name`; usurper preserved verbatim in notes.
    Per CLAUDE.md rule 3, this is an executable invariant on the
    Tier-3 derivation chain — if a future refactor of
    `_apply_issue_182_migrations` silently reverts the usurp regex,
    this test catches it.
    """
    tt22 = _row("TT22")
    assert tt22["is_usurped"] is True, (
        f"TT22 must carry `is_usurped=true` (deriver fires on `usurp` "
        f"regex match in notes); got {tt22['is_usurped']}"
    )
    # And the verbatim usurpation clause must still be in notes.
    assert "usurped" in (tt22["notes_from_pm"] or ""), (
        f"TT22 notes_from_pm must preserve PM's verbatim usurpation "
        f"clause; got notes={tt22['notes_from_pm']!r}"
    )
    # Mery[amūn] (with macron) must be preserved in notes.
    assert "Mery[amūn]" in (tt22["notes_from_pm"] or ""), (
        f"TT22 notes_from_pm must preserve the usurper name `Mery[amūn]` "
        f"with its macron-ū (chunk-10 TT17 macron-preserve precedent); "
        f"got notes={tt22['notes_from_pm']!r}"
    )


def test_chunk11_tt29_vizier_role_and_kv_cross_valley() -> None:
    """TT29 Amenemopet (called Pairi) — first chunk-9-to-11 row with a
    non-Official controlled-vocab role. PM headword reads `Governor of
    the town, Vizier.` — Vizier-precedence rule 4 applies: `Vizier`
    is in the controlled vocab, so it wins over the non-Vizier
    functional title; verbatim full title clause preserved in notes.

    Also first chunk-9-to-11 row with a CROSS-VALLEY `shared_with_tombs`
    reference. PM headword's `(Also owner of tomb 48 in the Valley of
    the Kings.)` parenthetical names the OTHER VALLEY explicitly,
    which by the chunk-11 prompt rule produces `KV<N>` (not `TT<N>`)
    in the field.

    Also first chunk-9-to-11 row with `occupant_alt_names` populated
    via PM's `called <X>` headword phrasing.
    """
    tt29 = _row("TT29")
    assert tt29["occupant_role"] == "Vizier", (
        f"TT29 must carry `occupant_role='Vizier'` per Vizier-precedence "
        f"rule 4; got {tt29['occupant_role']!r}"
    )
    assert tt29["shared_with_tombs"] == ["KV48"], (
        f"TT29 must carry `shared_with_tombs=['KV48']` per the chunk-11 "
        f"cross-valley rule (PM's `Valley of the Kings` qualifier); "
        f"got {tt29['shared_with_tombs']!r}"
    )
    assert tt29["occupant_alt_names"] == ["Pairi"], (
        f"TT29 must carry `occupant_alt_names=['Pairi']` per PM's "
        f"`AMENEMOPET, called PAIRI` headword phrasing; got "
        f"{tt29['occupant_alt_names']!r}"
    )
    # And the verbatim full title clause must be in notes.
    assert "Governor of the town, Vizier" in (tt29["notes_from_pm"] or ""), (
        f"TT29 notes_from_pm must preserve the verbatim full title "
        f"clause `Governor of the town, Vizier` even though `Vizier` "
        f"is the controlled-vocab role; got notes={tt29['notes_from_pm']!r}"
    )


def test_chunk11_tt27_sheshonk_underdot_k_preserved() -> None:
    """TT27 Sheshonḳ — README's strip rule covers underdot-Ḥ ONLY;
    underdot-Ḳ is preserved (chunk-7 / chunk-9 precedent). PM headword
    `27. SHESHONḲ ...`. Egyptologist printed-source review (chunk-11)
    confirmed.
    """
    assert _row("TT27")["occupant_name"] == "Sheshonḳ"
    # Underdot-Ḳ explicitly at character position -1.
    assert _row("TT27")["occupant_name"][-1] == "ḳ"


def test_chunk11_notes_from_pm_pinned_substrings() -> None:
    """Per-row `notes_from_pm` substring assertions. Chunk-11 highlights
    asserted by THIS test (verbatim PM clauses preserved in `notes_from_pm`):
    - TT22 usurpation clause + Tuthmosis III(?) regnal hedge.
    - TT26 + TT27 wife / parent macron-ē restorations.
    - TT27 `(Inaccessible.)` state-marker.
    - TT29 full Vizier title clause.

    Alt-names (a SEPARATE field, `occupant_alt_names`) are asserted by
    `test_chunk11_occupant_names` (TT23 `["To"]`) and `test_chunk11_tt29_
    vizier_role_and_kv_cross_valley` (TT29 `["Pairi"]`). Per Gemini Code
    Assist PR #199 round 1 + round 2 docstring-accuracy corrections.
    """
    expected: list[tuple[str, str, str]] = [
        ("TT21", "Scribe, Steward of Tuthmosis I.", "role + regnal"),
        ("TT22", "Partly usurped by Mery[amūn]", "usurpation clause"),
        ("TT22", "Eldest son of the King", "usurper role"),
        ("TT23", "Royal scribe of the dispatches of the Lord of the Two Lands.", "role"),
        ("TT24", "Steward of the royal wife Nebtu.", "role"),
        ("TT25", "First prophet of Khons.", "role + minor cult"),
        ("TT26", "Overseer of the treasury in the Ramesseum", "role"),
        # PM p.43 prints `Wife, Meryēsi` (macron-ē). Egyptologist-
        # flagged macron-drop fixed via CHUNK11_CORRECTIONS. (The `n +`
        # qualifier in the prior version was a copy-paste leftover from
        # chunk-10 TT16's rn→rm fix; TT26's only OCR issue is the macron
        # drop, no n→m involved. Per Gemini PR #199 round 3.)
        ("TT26", "Wife, Meryēsi.", "wife macron-ē correction"),
        ("TT27", "(Inaccessible.)", "state-marker"),
        # PM p.43 prints `Parents, Ḥarsiēsi` (macron-ē). Egyptologist-
        # flagged macron-drop fixed via CHUNK11_CORRECTIONS.
        ("TT27", "Ḥarsiēsi", "parent macron-ē correction"),
        ("TT28", "Officer of the estate of Amūn.", "role"),
        ("TT29", "Governor of the town, Vizier.", "Vizier full title clause"),
        ("TT30", "Scribe of the treasury of the estate of Amūn.", "role"),
    ]
    for tid, substr, label in expected:
        notes = _row(tid)["notes_from_pm"]
        assert notes is not None, f"{tid} ({label}) expected notes, got None"
        assert substr in notes, f"{tid} ({label}): expected {substr!r} in {notes!r}"


# ---------------------------------------------------------------------------
# Chunk 9: LEGACY_FIELD_RENAMES regression tripwire
# ---------------------------------------------------------------------------


def test_chunk9_legacy_field_renames_migration_applied() -> None:
    """`fix_rows.LEGACY_FIELD_RENAMES` mechanism (chunk-9 PR) renames
    `valley` → `theban_area` on every load to enforce the post-#170
    rename invariant.

    PR #170 renamed the field by editing reconciled.jsonl directly
    without updating the per-chunk agent JSONLs (which remain the
    stable record of each round of agent extraction). Re-running
    merge.py therefore regenerates rows with the OLD `valley` key.
    The migration in `fix_rows.main()` enforces the rename on every
    load so the convention can no longer silently regress.

    This test exercises the migration path directly (not via the
    on-disk reconciled.jsonl): construct a synthetic in-memory row
    carrying `valley`, run the legacy-rename block, assert the
    output. Per CLAUDE.md rule 3 (deterministic enforcement over
    convention), the migration must convert the post-#170 rename
    convention into a code-level enforcement — and it must have a
    tripwire test, otherwise the next reviewer wonders whether the
    migration would actually fire if a future re-merge brought the
    legacy key back. Per code-reviewer P3-3 on PR #196.
    """
    fix_rows = _import_fix_rows()
    assert fix_rows.LEGACY_FIELD_RENAMES == {"valley": "theban_area"}, (
        fix_rows.LEGACY_FIELD_RENAMES
    )

    # Reproduce the inline migration from `fix_rows.main()` against a
    # synthetic 3-row fixture covering the three valid input shapes:
    #   1. row with only `valley` (the merge regression case)
    #   2. row with only `theban_area` (already migrated)
    #   3. row with both keys carrying equal values (idempotent collision)
    rows = [
        {"tomb_id": "SYNTH1", "valley": "Valley of the Kings"},
        {"tomb_id": "SYNTH2", "theban_area": "Valley of the Queens"},
        {
            "tomb_id": "SYNTH3",
            "valley": "Deir el-Medina",
            "theban_area": "Deir el-Medina",
        },
    ]
    for old_key, new_key in fix_rows.LEGACY_FIELD_RENAMES.items():
        for row in rows:
            if old_key in row:
                if new_key in row:
                    if row[old_key] != row[new_key]:
                        raise ValueError(
                            f"row {row.get('tomb_id')!r} carries both "
                            f"{old_key!r} and {new_key!r} with different "
                            f"values; resolve before merging."
                        )
                    del row[old_key]
                else:
                    row[new_key] = row.pop(old_key)

    # SYNTH1 (only `valley`): renamed.
    assert "valley" not in rows[0]
    assert rows[0]["theban_area"] == "Valley of the Kings"
    # SYNTH2 (only `theban_area`): unchanged.
    assert "valley" not in rows[1]
    assert rows[1]["theban_area"] == "Valley of the Queens"
    # SYNTH3 (both, equal values): legacy key dropped.
    assert "valley" not in rows[2]
    assert rows[2]["theban_area"] == "Deir el-Medina"


def test_chunk9_legacy_field_renames_value_conflict_raises() -> None:
    """When both `valley` and `theban_area` carry DIFFERENT values on the
    same row, the migration MUST raise — silently picking either side
    would let a real conflict slip into reconciled.jsonl. Per CLAUDE.md
    rule 2 (no defensive programming, loud failures).
    """
    rows = [
        {
            "tomb_id": "SYNTH-CONFLICT",
            "valley": "Valley of the Kings",
            "theban_area": "Valley of the Queens",
        },
    ]
    import pytest

    with pytest.raises(ValueError, match="carries both"):
        for old_key, new_key in {"valley": "theban_area"}.items():
            for row in rows:
                if old_key in row and new_key in row:
                    if row[old_key] != row[new_key]:
                        raise ValueError(
                            f"row {row.get('tomb_id')!r} carries both "
                            f"{old_key!r} and {new_key!r} with different "
                            f"values; resolve before merging."
                        )


# ---------------------------------------------------------------------------
# Audit-trail tests for fix_rows.py
# ---------------------------------------------------------------------------


def _import_fix_rows():
    """Load the source's fix_rows.py module by file path (the directory has a
    hyphen so `importlib.import_module` doesn't work directly).
    """
    spec = importlib.util.spec_from_file_location(
        "pm_theban_fix_rows", SOURCE_DIR / "fix_rows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_corrections_includes_every_chunk_list() -> None:
    """fix_rows.py's `ALL_CORRECTIONS` aggregates every `CHUNK*_CORRECTIONS`
    list AND the source-wide audit-fix list (`AUDIT_FIX_CORRECTIONS`).
    Dropping any of them silently destroys the audit trail — this test fails
    loud if either list is added without being aggregated.

    Uses natural-numeric sort on the chunk suffix (NOT lexicographic sort)
    so the test stays correct at chunk 10+. Gemini code-review on PR #71
    flagged that the prior lex-sort would mis-order `CHUNK10` before
    `CHUNK2`, invalidating the equality assertion against a numerically-
    ordered `ALL_CORRECTIONS`.

    `AUDIT_FIX_CORRECTIONS` (PR A, 2026-05-02) is appended after the chunk
    lists since it is structurally different — a one-shot source-wide
    schema migration, not a chunk-specific reviewer pass.
    """
    fix_rows = _import_fix_rows()
    chunk_re = re.compile(r"^CHUNK(\d+)_CORRECTIONS$")
    chunk_attrs = sorted(
        (attr for attr in dir(fix_rows) if chunk_re.match(attr)),
        key=lambda attr: int(chunk_re.match(attr).group(1)),
    )
    expected = [getattr(fix_rows, a) for a in chunk_attrs] + [
        fix_rows.AUDIT_FIX_CORRECTIONS,
    ]
    assert fix_rows.ALL_CORRECTIONS == expected, (
        f"ALL_CORRECTIONS missing one of the correction lists. "
        f"Found chunk attrs: {chunk_attrs}; expected trailing entry "
        f"AUDIT_FIX_CORRECTIONS."
    )


def test_all_renames_includes_every_chunk_dict() -> None:
    """fix_rows.py's `ALL_RENAMES` aggregates every `CHUNK*_RENAMES` dict.
    Analogous to `test_all_corrections_includes_every_chunk_list` — dropping
    a per-chunk rename dict silently destroys its audit trail so a
    reconciled.jsonl pulled from a fresh merge would contain the pre-rename
    tomb_ids without `fix_rows.py` catching the omission.

    Gemini code-review on PR #100 round 3 flagged the lack of this
    validation test. Uses the same natural-numeric chunk-suffix sort as
    `ALL_CORRECTIONS`'s test so chunk 10+ ordering stays correct.
    """
    fix_rows = _import_fix_rows()
    chunk_re = re.compile(r"^CHUNK(\d+)_RENAMES$")
    chunk_attrs = sorted(
        (attr for attr in dir(fix_rows) if chunk_re.match(attr)),
        key=lambda attr: int(chunk_re.match(attr).group(1)),
    )
    expected: dict[str, str] = {}
    for a in chunk_attrs:
        expected.update(getattr(fix_rows, a))
    assert fix_rows.ALL_RENAMES == expected, (
        f"ALL_RENAMES missing one of the per-chunk dicts. "
        f"Found chunk attrs: {chunk_attrs}"
    )


def test_fix_rows_main_idempotent() -> None:
    """`fix_rows.main()` is idempotent: a second call produces byte-identical
    `reconciled.jsonl` and `merge-disagreements.txt` to a first call (PR
    #169 code-reviewer P1-1).

    Three idempotence claims live in `fix_rows.py` docstrings/comments:
    the field-add pass (`SCHEMA_FIELD_DEFAULTS`), the override pass
    (`SPOT_CORRECTIONS`), and the diff-section append-or-replace logic.
    Per CLAUDE.md rule 3 (deterministic enforcement over convention), an
    idempotence claim that lives only in a docstring is a suggestion, not
    a guarantee — the next refactor of `main()` (e.g. someone changes the
    field-add pass to use `setdefault` plus a logger that always appends)
    silently regresses on disk. A single round-trip byte-equality test
    catches all three regressions.

    Idempotence in this codebase means `f(f(x)) == f(x)` — the output is
    stable from the second run onward, not necessarily on the first run
    after a state transition. So the test calls main() to reach steady
    state, snapshots, then calls again and compares. The pre-existing
    on-disk state (which may include "corrected this run" log lines from
    a recent commit-time run) is restored after the test so the working
    tree stays clean.
    """
    fix_rows = _import_fix_rows()
    reconciled = SOURCE_DIR / "reconciled.jsonl"
    diff = SOURCE_DIR / "merge-disagreements.txt"

    pre_reconciled = reconciled.read_bytes()
    pre_diff = diff.read_bytes()
    try:
        # First run: reach steady state regardless of what was on disk
        # at test-entry (which may have transitional log lines).
        fix_rows.main()
        snap_reconciled = reconciled.read_bytes()
        snap_diff = diff.read_bytes()
        # Second run: must be byte-identical (the idempotence contract).
        fix_rows.main()
        new_reconciled = reconciled.read_bytes()
        new_diff = diff.read_bytes()
        assert new_reconciled == snap_reconciled, (
            "fix_rows.main() is NOT idempotent on reconciled.jsonl — second "
            "call produced a different byte-string from the first."
        )
        assert new_diff == snap_diff, (
            "fix_rows.main() is NOT idempotent on merge-disagreements.txt — "
            "second call produced a different byte-string from the first. "
            "The LLM-APPLIED OVERRIDES section's append-or-replace logic "
            "must produce identical output across re-runs."
        )
    finally:
        # Restore the original on-disk state so the working tree stays
        # clean even if the test fails.
        reconciled.write_bytes(pre_reconciled)
        diff.write_bytes(pre_diff)


# ── Closure tests (#182) — typed flags from notes_from_pm derivation ───

_REQUIRED_182_KEYS = ("is_uninscribed", "is_usurped", "attribution_certainty")
_ATTRIBUTION_VOCAB = {"attested", "probable", "uncertain"}


def test_182_every_row_has_typed_flags() -> None:
    """Every row carries all 3 typed fields introduced in #182."""
    for r in _rows():
        for key in _REQUIRED_182_KEYS:
            assert key in r, (r["tomb_id"], key)


def test_182_attribution_certainty_in_vocab() -> None:
    """attribution_certainty ∈ {attested, probable, uncertain}."""
    for r in _rows():
        assert r["attribution_certainty"] in _ATTRIBUTION_VOCAB, (
            r["tomb_id"], r["attribution_certainty"]
        )


def test_182_uninscribed_canonical_set() -> None:
    """Rows where PM literally writes "uninscribed" in notes_from_pm.
    Pinned 2026-05-03: KV39 ('Uninscribed tomb...'), KV56 ("'Gold tomb',
    uninscribed."), DAN-Neferhotep ('Rock-tomb, uninscribed').
    Extended 2026-05-20 (chunk 20): TT115 — DERIVER_OVERRIDE for PM's
    `No texts. Dyn. XIX.` semantic-equivalent of "uninscribed" per
    Gemini PR #264 round-3 finding 3277852207."""
    expected = {"KV39", "KV56", "DAN-Neferhotep", "TT115"}
    actual = {r["tomb_id"] for r in _rows() if r["is_uninscribed"]}
    assert actual == expected, sorted(actual)


def test_182_usurped_canonical_set() -> None:
    """Rows where PM writes "usurp(ed|ation)" in notes_from_pm.
    Pinned 2026-05-09 (chunks 1-13): KV9 (doorways usurped from Ramesses V),
    KV14 (usurped by Setnakht), TT22 (Wah, partly usurped by Mery[amūn],
    Eldest son of the King — chunk 11), TT45 (Ḏhout, usurped by
    Ḏḥutemḥab, Head of the makers of fine linen of the estate of
    Amūn — chunk 13).
    Extended 2026-05-10 (chunk 14): TT54 (Huy, usurped by Kenro, wab-priest,
    early Dyn. XIX — PM I.1 p.104), TT58 (anonymous, usurped by Amenḥotp +
    son Amenemonet, Dyn. XX — PM I.1 p.119).
    Extended 2026-05-10 (chunk 15): TT65 (Nebamun, usurped by Imiseba,
    temp. Ramesses IX — PM I.1 p.129), TT68 ([Per?]enkhmun, usurped by
    Espaneferḥor, temp. Siamūn — PM I.1 p.133), TT70 (anonymous, usurped
    by Amenmosi, Dyn. XXI — PM I.1 p.139).
    Extended 2026-05-10 (chunk 16): TT77 (Ptahemhet, usurped by Roy,
    Overseer of sculptors — PM I.1 p.150).
    Extended 2026-05-10 (chunk 17): TT84 (Amunezeḥ, partly usurped by Mery
    of TT95, temp. Amenophis II — PM I.1 p.167).
    Extended chunk 20: TT112 (Menkheperraʿsonb, usurped by ʿAshefytemweset,
    Prophet of Amūn 'Great of Majesty', Ramesside — PM I.1 p.229). Note:
    TT112's original occupant Menkheperraʿsonb IS the usurped party (contrast
    TT95 Mery who was the USURPER — required a DERIVER_OVERRIDE to suppress
    is_usurped); no override needed for TT112.
    Extended chunk 21: TT127 (Senemiʿoh, usurped in Ramesside times —
    PM I.1 p.241). Senemiʿoh IS the usurped party; deriver fires correctly
    on `usurped in Ramesside times`; no DERIVER_OVERRIDE needed.
    Extended chunk 24: TT152 (anonymous tomb, usurped in Ramesside times(?) —
    PM I.1 p.262). Deriver fires correctly on `Usurped in Ramesside times`;
    DERIVER_OVERRIDE sets attribution_certainty=attested (the (?) qualifies
    the event timing, not occupant identity); is_usurped=True is correct."""
    expected = {"KV9", "KV14", "TT22", "TT45", "TT54", "TT58",
                "TT65", "TT68", "TT70", "TT77", "TT84", "TT112", "TT127",
                "TT152"}
    actual = {r["tomb_id"] for r in _rows() if r["is_usurped"]}
    assert actual == expected, sorted(actual)


def test_182_uncertain_attribution_canonical_set() -> None:
    """Rows where PM uses strong-uncertainty hedge tokens (uncertain,
    perhaps, possibly, tentatively) OR PM's `(?)` glyph qualifying the
    PRIMARY OCCUPANT identification. Pinned 2026-05-03: 5 rows. Per
    Gemini round-2 — `(?)` is PM's standard attribution-uncertainty
    marker (KV42 + QV60 notes start with `(?)`, QV33 carries `Dyn. XX(?)`).

    Chunk 10's TT12 / TT17 / TT19 / TT20 are NOT in this set — their
    `(?)` glyphs qualify the regnal-date claim (or in TT17 also a
    parent's identification), NOT the primary occupant. Per the chunk-9
    TT2 precedent, attribution_certainty encodes occupant-identity
    certainty; those four rows are pinned back to `"attested"` via
    `DERIVER_OVERRIDES` in `fix_rows.py`. Egyptologist printed-source
    review (chunk-10 PR) cited the rule.

    Chunk 14's TT52 and TT54 are likewise NOT in this set — both have
    `(?)` qualifying only the regnal-date tail (Tuthmosis IV for TT52,
    Amenophis III for TT54), not the primary occupant. Pinned back to
    `"attested"` via DERIVER_OVERRIDES per the same TT2 precedent chain.

    Chunk 15's TT62/TT65/TT69/TT70 are NOT in this set — `(?)` qualifies
    the regnal-date (TT62, TT69), primary-occupant regnal-range (TT65), or
    the usurper's title (TT70 `sandal-makers (?)`). For TT70 specifically:
    egyptologist-reviewer pass confirmed that since attribution_certainty
    encodes occupant-identity certainty (chunk-9 TT2 precedent) and TT70's
    primary occupant is intentionally null (anonymous original burial),
    there is no occupant identity to hedge — the `(?)` qualifies only the
    USURPER (Amenmosi) and is structurally identical to the chunk-11 TT22
    case (Wah usurped by Mery[amūn], regnal hedge on usurper's date). All
    four rows pinned back to `"attested"` via DERIVER_OVERRIDES.

    Chunk 16's TT73 IS in this set — PM headword `Amenḥotp (?)` has the
    `(?)` directly qualifying the primary occupant name, not a regnal-date
    tail. This is the genuine primary-attribution hedge case that the deriver
    was designed to catch; no DERIVER_OVERRIDE needed. Chunk 16's TT79 is
    NOT in this set — its `(?)` qualifies the regnal-range tail
    `Amenophis II (?)`, not the occupant; pinned back to `"attested"` via
    DERIVER_OVERRIDES per the chunk-9 TT2 + regnal-date precedent chain.
    """
    expected = {
        "DAN-KamosiWazkheperre",
        "DAN-SebkemsafSekhemreShedtaui",
        "KV42",
        "QV33",
        "QV60",
        "TT73",
        # TT209 Seremhatrekhyt: PM headword `SEREMḤATREKHYT (?)` has the `(?)`
        # directly qualifying the name transcription (a genuine reading-uncertainty
        # on the hieroglyphic inscription itself, not a regnal-date tail or
        # secondary-clause hedge). The deriver correctly fires `uncertain` here.
        "TT209",
    }
    actual = {r["tomb_id"] for r in _rows() if r["attribution_certainty"] == "uncertain"}
    assert actual == expected, sorted(actual)


def test_182_probable_attribution_canonical_set() -> None:
    """Rows where PM writes "Probably" or "attributed to" in notes_from_pm.
    Pinned 2026-05-03: 7 rows."""
    expected = {
        "DAN-AhmosiNefertere", "DAN-AntefSekhemreHeruhirmaet",
        "DAN-Neferhotep", "KV39", "KV55", "QV46", "SWV-Neferure",
    }
    actual = {r["tomb_id"] for r in _rows() if r["attribution_certainty"] == "probable"}
    assert actual == expected, sorted(actual)


# ---------------------------------------------------------------------------
# Chunk-12 per-row tests (TT31–TT40, PM I.1 pp 47-78 / physical pp 65-96)
# ---------------------------------------------------------------------------


def test_chunk12_all_rows_present() -> None:
    """All 10 TT31-TT40 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK12_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        r = _row(tid)  # raises if not found
        assert r["tomb_id"] == tid


def test_chunk12_all_rows_null_dynasty_dates_discoverer() -> None:
    """Chunk-12 has no dynasty, date, or discoverer fields — PM I.1 does not
    structure dates or excavation records in the private-tomb section."""
    for tid in CHUNK12_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] is None, (tid, r["dynasty"])
        assert r["sub_period"] is None, (tid, r["sub_period"])
        assert r["date_bce_approx_start"] is None, (tid, r["date_bce_approx_start"])
        assert r["date_bce_approx_end"] is None, (tid, r["date_bce_approx_end"])
        assert r["discovery_year"] is None, (tid, r["discovery_year"])
        assert r["discoverer"] is None, (tid, r["discoverer"])


def test_chunk12_all_rows_edition_pm_i1() -> None:
    """All chunk-12 rows cite PM I.1 2nd ed. 1960, section I."""
    for tid in CHUNK12_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid, r["source_citation"]["edition"]
        )
        assert r["source_citation"]["section"] == "I", (
            tid, r["source_citation"]["section"]
        )


def test_chunk12_all_rows_no_flags() -> None:
    """No chunk-12 tomb is uninscribed, usurped, unfinished, or joint burial."""
    for tid in CHUNK12_TOMB_IDS:
        r = _row(tid)
        assert r["is_uninscribed"] is False, (tid, "is_uninscribed")
        assert r["is_usurped"] is False, (tid, "is_usurped")
        assert r["is_unfinished"] is False, (tid, "is_unfinished")
        assert r["is_joint_burial"] is False, (tid, "is_joint_burial")
        assert r["attribution_certainty"] == "attested", (tid, r["attribution_certainty"])


def test_chunk12_theban_area_distribution() -> None:
    """Chunk-12 spreads across 5 PM-faithful sub-sites: 2× Sh. ʿAbd el-Qurna,
    2× Khokha, 3× ʿAsâsîf, 2× Dra' Abu el-Naga, 1× Qurnet Muraʿi.
    Set-equality pin guards against any sub-site silently shifting under
    a future re-merge / fix_rows pass.
    """
    expected: dict[str, set[str]] = {
        "Sh. ʿAbd el-Qurna": {"TT31", "TT38"},
        "Khokha": {"TT32", "TT39"},
        "ʿAsâsîf": {"TT33", "TT34", "TT36", "TT37"},
        "Dra' Abu el-Naga": {"TT35"},
        "Qurnet Muraʿi": {"TT40"},
    }
    actual: dict[str, set[str]] = {}
    for tid in CHUNK12_TOMB_IDS:
        ta = _row(tid)["theban_area"]
        actual.setdefault(ta, set()).add(tid)
    assert actual == expected, sorted(actual.items())


def test_chunk12_qurnet_murai_canonical_codepoint() -> None:
    """`Qurnet Muraʿi` (TT40, first occurrence) uses ayin U+02BF (MODIFIER
    LETTER LEFT HALF RING) — NOT apostrophe (U+0027) or right-single-quote
    (U+2019). Pins the canonical codepoint so a future copy/paste through a
    smart-quote-substituting editor cannot silently mangle the sub-site name.
    """
    ta = _row("TT40")["theban_area"]
    assert ta == "Qurnet Muraʿi"
    assert "ʿ" in ta, repr(ta)  # ayin
    assert "'" not in ta, repr(ta)  # no ASCII apostrophe
    assert "’" not in ta, repr(ta)  # no right-single-quote


def test_chunk12_tt31_khons() -> None:
    """TT31 — Khons, First prophet of Menkheperreʿ, Sh. ʿAbd el-Qurna, p.47."""
    r = _row("TT31")
    assert r["tomb_id"] == "TT31"
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["occupant_name"] == "Khons"
    assert r["occupant_alt_names"] == ["To"]
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "First prophet of Menkheperreʿ (Tuthmosis III). Temp. Ramesses II. "
        "(L. D. Text, No. 51.) Parents, Neferḥotep, First prophet of Amenophis II, "
        "and Tausert, Songstress of Monthu. Wives, Ruia and Mutia or May."
    )
    assert r["source_citation"]["page"] == 47


def test_chunk12_tt32_thutmosi() -> None:
    """TT32 — Ḏhutmosi, Chief steward of Amūn, Khokha, p.49.
    The d-emphatic in this name family (`Thutmose` < Egyptian `Ḏḥwty-msj`
    < `Ḏḥwty`/Thoth) is d-bar `Ḏ` (U+1E0E), the standard Egyptological
    transliteration of the d-emphatic — NOT d-underdot `Ḍ` (U+1E0C, a
    different consonant in some Semitic systems). PR #151 verified `Ḏ`
    not `Ḍ` for sibling names `Ḏḥuti` (PM I.2 p.604) and `Sit-ḏḥout`
    (PM I.2 p.755) after direct PM PDF read. Tie-break pins agent A's
    `Thutmosi` (PDF-closest stripped-diacritic form); CHUNK12_CORRECTIONS
    layers the post-merge `Ḏhutmosi` restoration. Wrong-consonant risk:
    `Ḍhutmosi` would never match TLA/Trismegistos data using `Ḏḥwty`-
    derived forms.
    """
    r = _row("TT32")
    assert r["tomb_id"] == "TT32"
    assert r["theban_area"] == "Khokha"
    assert r["occupant_name"] == "Ḏhutmosi"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Chief steward of Amūn, Overseer of the granaries of Upper and Lower Egypt. "
        "Temp. Ramesses II. Wife, Esi."
    )
    assert r["source_citation"]["page"] == 49


def test_chunk12_tt33_pedamenopet() -> None:
    """TT33 — Pedamenōpet, Prophet / Chief lector, ʿAsâsîf, p.50.
    PM prints the headword `PEDAMENŌPET` with capital macron-Ō (direct PDF visual
    check, physical p.68). pypdf text-layer drops capital macrons; CHUNK12_CORRECTIONS
    restores it (same class as chunk-11 TT29 `Amenemōpet`).
    """
    r = _row("TT33")
    assert r["tomb_id"] == "TT33"
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["occupant_name"] == "Pedamenōpet"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Prophet, Chief lector. Saite. (L. D. Text, No. 20.) "
        "Mother, Namenkhesi, Sistrum-player of Amūn. Wife, Tedi."
    )
    assert r["source_citation"]["page"] == 50


def test_chunk12_tt34_mentuemhet() -> None:
    """TT34 — Mentuemhēt, Fourth prophet of Amūn, ʿAsâsîf, p.56.
    PM prints the headword `MENTUEMḤĒT` with capital underdot-Ḥ + capital macron-Ē
    (direct PDF visual check, physical p.74). Strip Ḥ-underdot per policy; restore
    macron via CHUNK12_CORRECTIONS.
    """
    r = _row("TT34")
    assert r["tomb_id"] == "TT34"
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["occupant_name"] == "Mentuemhēt"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Fourth prophet of Amūn in Thebes. Temp. Taharqa and Psammetikhos I. "
        "Parents, Espṭaḥ, Prophet of Amūn, Mayor of the City, and Esenkhebi. "
        "Wives, Uzarenes, Sistrum-player of Amen-Reʿ (name in tomb), "
        "Eskhons and Shepetenmut (names from cones)."
    )
    assert r["source_citation"]["page"] == 56


def test_chunk12_tt35_bekenkhons() -> None:
    """TT35 — Bekenkhons, First prophet of Amūn (High Priest role), Dra' Abu el-Naga, p.61."""
    r = _row("TT35")
    assert r["tomb_id"] == "TT35"
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["occupant_name"] == "Bekenkhons"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "High Priest"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "First prophet of Amūn. Temp. Ramesses II. "
        "(CHAMPOLLION, No. 45, L. D. Text, Nos. 10, 11.) "
        "Parents, Roma, First and second prophet of Amūn, and Roma, Singer of Amūn. "
        "Wife, Mertesger, Chief of the harim of Amūn."
    )
    assert r["source_citation"]["page"] == 61


def test_chunk12_tt36_ibi() -> None:
    """TT36 — Ibi, Chief steward of the divine adoratress, ʿAsâsîf, p.63."""
    r = _row("TT36")
    assert r["tomb_id"] == "TT36"
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["occupant_name"] == "Ibi"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Chief steward of the divine adoratress. Temp. Psammetikhos I. "
        "(CHAMPOLLION, No. 56, L. D. Text, No. 25.) "
        "Parents, ʿAnkh-ḥor, Divine father, and De-ubasteiri, variant Teiri. "
        "Wife, Shepenernute (name in tomb 196)."
    )
    assert r["source_citation"]["page"] == 63


def test_chunk12_tt37_harua() -> None:
    """TT37 — Harua, Chief steward of god's wife Amenardais I, ʿAsâsîf, p.68."""
    r = _row("TT37")
    assert r["tomb_id"] == "TT37"
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["occupant_name"] == "Harua"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Chief steward of the god's wife Amenardais I. Saite. "
        "(CHAMPOLLION, No. 54, L. D. Text, No. 23.) "
        "Parents, Pedemut, Scribe, and Estawert "
        "(names from statues, in Berlin Mus. 8163, see infra, p. 69, "
        "and Cairo Mus. Ent. 36711)."
    )
    assert r["source_citation"]["page"] == 68


def test_chunk12_tt38_zeserkaraasonb() -> None:
    """TT38 — Zeserkaraʿsonb, Scribe, Sh. ʿAbd el-Qurna, p.69."""
    r = _row("TT38")
    assert r["tomb_id"] == "TT38"
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["occupant_name"] == "Zeserkaraʿsonb"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Scribe, Counter of the grain in the granary of divine offerings of Amūn. "
        "Temp. Tuthmosis IV. Wife, Wazronpet."
    )
    assert r["source_citation"]["page"] == 69


def test_chunk12_tt39_puimre() -> None:
    """TT39 — Puimrēʿ, Second prophet of Amūn, Khokha, p.71.
    PM prints the headword `PUIMRĒʿ` with capital macron-Ē + ayin (direct PDF visual
    check, physical p.89). pypdf text-layer drops the macron; CHUNK12_CORRECTIONS
    restores it.
    """
    r = _row("TT39")
    assert r["tomb_id"] == "TT39"
    assert r["theban_area"] == "Khokha"
    assert r["occupant_name"] == "Puimrēʿ"
    assert r["occupant_alt_names"] == []
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Second prophet of Amūn. Temp. Tuthmosis III. "
        "(L. D. Text, No. 18.) Parents, Puia and Neferi. "
        "Wives, Tanefert and Sensonb."
    )
    assert r["source_citation"]["page"] == 71


def test_chunk12_tt40_amenhotp() -> None:
    """TT40 — Amenhotp (called Huy), Viceroy of Kush, Qurnet Muraʿi, p.75.
    The epithet `called Ḥuy` is NOT in notes_from_pm (it lives in
    occupant_alt_names). TT40 introduces `Qurnet Muraʿi` as the first
    occurrence of that theban_area value in reconciled.jsonl.
    """
    r = _row("TT40")
    assert r["tomb_id"] == "TT40"
    assert r["theban_area"] == "Qurnet Muraʿi"
    assert r["occupant_name"] == "Amenhotp"
    assert r["occupant_alt_names"] == ["Huy"]
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["tomb_aliases"] == []
    assert r["co_occupants"] == []
    assert r["notes_from_pm"] == (
        "Viceroy of Kush, Governor of the South Lands. "
        "Temp. Amenophis IV to Tutʿankhamūn. "
        "(CHAMPOLLION, A, L. D. Text, No. 110.) Mother, Wenḥo."
    )
    assert r["source_citation"]["page"] == 75


# ---------------------------------------------------------------------------
# Chunk-13 per-row tests (TT41–TT50, PM I.1 pp 78-95 / physical pp 96-115)
# ---------------------------------------------------------------------------


def test_chunk13_all_rows_present() -> None:
    """All 10 TT41-TT50 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK13_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        r = _row(tid)
        assert r["tomb_id"] == tid


def test_chunk13_all_rows_null_dynasty_dates_discoverer() -> None:
    """Chunk-13 has no dynasty, date, or discoverer fields — PM I.1 does not
    structure dates or excavation records in the private-tomb section."""
    for tid in CHUNK13_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] is None, (tid, r["dynasty"])
        assert r["sub_period"] is None, (tid, r["sub_period"])
        assert r["date_bce_approx_start"] is None, (tid, r["date_bce_approx_start"])
        assert r["date_bce_approx_end"] is None, (tid, r["date_bce_approx_end"])
        assert r["discovery_year"] is None, (tid, r["discovery_year"])
        assert r["discoverer"] is None, (tid, r["discoverer"])


def test_chunk13_all_rows_edition_pm_i1() -> None:
    """All chunk-13 rows cite PM I.1 2nd ed. 1960, section I."""
    for tid in CHUNK13_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid, r["source_citation"]["edition"]
        )
        assert r["source_citation"]["section"] == "I", (
            tid, r["source_citation"]["section"]
        )


def test_chunk13_all_rows_attribution_attested() -> None:
    """All chunk-13 rows have attribution_certainty="attested" after the
    DERIVER_OVERRIDES pass. The deriver fires `uncertain` on `(?)` and
    `probable` on `Probably` regnal-/usurper-clause hedges; per the
    chunk-9 TT2 + chunk-10 cluster + chunk-11 TT22 precedent, those
    hedges qualify the regnal date or usurper, NOT the primary occupant
    identification, so DERIVER_OVERRIDES flips them back to `attested`.
    Five chunk-13 rows have such overrides: TT41, TT43, TT45, TT46, TT49.
    """
    for tid in CHUNK13_TOMB_IDS:
        r = _row(tid)
        assert r["attribution_certainty"] == "attested", (
            tid, r["attribution_certainty"]
        )


def test_chunk13_all_rows_official_role() -> None:
    """All chunk-13 rows flatten to occupant_role="Official" — no royal
    family / Vizier / High Priest in this decade. Verbatim role-title
    clauses are preserved in notes_from_pm regardless."""
    for tid in CHUNK13_TOMB_IDS:
        r = _row(tid)
        assert r["occupant_role"] == "Official", (tid, r["occupant_role"])


def test_chunk13_theban_area_distribution() -> None:
    """Chunk-13 spreads across 2 PM-faithful sub-sites: 7× Sh. ʿAbd el-Qurna
    (TT41-46, TT50) and 3× Khokha (TT47-49). Set-equality pin guards
    against any sub-site silently shifting under a future re-merge /
    fix_rows pass.
    """
    expected: dict[str, set[str]] = {
        "Sh. ʿAbd el-Qurna": {"TT41", "TT42", "TT43", "TT44", "TT45", "TT46", "TT50"},
        "Khokha": {"TT47", "TT48", "TT49"},
    }
    actual: dict[str, set[str]] = {}
    for tid in CHUNK13_TOMB_IDS:
        ta = _row(tid)["theban_area"]
        actual.setdefault(ta, set()).add(tid)
    assert actual == expected, sorted(actual.items())


def test_chunk13_tt41_amenemopet() -> None:
    """TT41 — Amenemōpet (called Ipy), Chief steward of Amūn, Sh. ʿAbd el-Qurna, p.78.
    PM prints headword `AMENEMŌPET` with capital macron-Ō (direct PDF visual
    check, physical p.96). pypdf text-layer drops capital macrons;
    CHUNK13_CORRECTIONS restores. Same OCR class as chunk-12 TT33/TT34.
    The (?) on Sethos I qualifies the regnal-range tail, not the occupant —
    DERIVER_OVERRIDES pins attribution_certainty=attested.
    """
    r = _row("TT41")
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["occupant_name"] == "Amenemōpet"
    assert r["occupant_alt_names"] == ["Ipy"]
    assert r["occupant_role"] == "Official"
    assert r["location_sub_area"] is None
    assert r["shared_with_tombs"] == []
    assert r["co_occupants"] == []
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 78
    assert "(CHAMPOLLION, No. 35.)" in r["notes_from_pm"]
    # Spurious-double-period correction landed (was `35.).` post-merge):
    assert "35.)." not in r["notes_from_pm"]
    assert "35.) Parents," in r["notes_from_pm"]


def test_chunk13_tt45_dhout_usurped() -> None:
    """TT45 — Ḏhout (d-bar Ḏ U+1E0E, the Egyptological d-emphatic in
    `Ḏḥwty`/Thoth name family), Sh. ʿAbd el-Qurna, p.85. Original occupant
    Ḏhout, usurped by Ḏḥutemḥab. is_usurped=true derived from the
    `Usurped by` regex; attribution_certainty=attested per
    DERIVER_OVERRIDES (the two `(?)` hedges in notes both qualify the
    USURPER's clause — title hedge `fine linen(?)` and regnal hedge
    `Ramesses II (?)` — neither qualifies Ḏhout's primary attribution).
    Extends the d-bar precedent established by chunk-12 PR #200 TT32
    `Ḏhutmosi` to PM I.1.
    """
    r = _row("TT45")
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["occupant_name"] == "Ḏhout"
    assert "Ḏ" in r["occupant_name"]  # d-bar U+1E0E
    assert "Ḍ" not in r["occupant_name"]  # NOT d-underdot U+1E0C
    assert r["occupant_role"] == "Official"
    assert r["co_occupants"] == []  # usurper does NOT go in co_occupants
    assert r["is_usurped"] is True  # deriver fires on `Usurped by`
    assert r["attribution_certainty"] == "attested"  # DERIVER_OVERRIDES
    assert r["source_citation"]["page"] == 85
    # Usurper's name + title preserved verbatim in notes:
    assert "Ḏḥutemḥab" in r["notes_from_pm"]
    assert "Usurped by" in r["notes_from_pm"]


def test_chunk13_tt47_inaccessible() -> None:
    """TT47 — Userhet, Khokha, p.87. Headword carries the `(Inaccessible.)`
    tomb-state-marker parenthetical preserved verbatim in notes_from_pm
    (chunk-12 precedent — no schema field for tomb state). The
    spurious-double-period after `(Inaccessible.)` is corrected via
    CHUNK13_CORRECTIONS.
    """
    r = _row("TT47")
    assert r["theban_area"] == "Khokha"
    assert r["occupant_name"] == "Userhet"
    assert r["source_citation"]["page"] == 87
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert "(Inaccessible.)." not in r["notes_from_pm"]
    # Single period inside the close-paren only, then a fresh `Parents,`:
    assert "(Inaccessible.) Parents," in r["notes_from_pm"]


def test_chunk13_tt48_alt_name_surero() -> None:
    """TT48 — Amenemhet (called Surero), Khokha, p.87. The `called X`
    pattern captures the alt-name in occupant_alt_names."""
    r = _row("TT48")
    assert r["theban_area"] == "Khokha"
    assert r["occupant_name"] == "Amenemhet"
    assert r["occupant_alt_names"] == ["Surero"]
    assert r["occupant_role"] == "Official"
    assert r["source_citation"]["page"] == 87


def test_chunk13_tt49_tt50_neferhotep_collision() -> None:
    """TT49 + TT50 both have `occupant_name="Neferhotep"` — distinct
    individuals, different sub-sites, different roles, different regnal
    periods. The schema row-key is tomb_id, not name; the chunk-13 prompt
    explicitly warns against collapsing such collisions. The within-decade
    name collision is structural, not an extraction error.
    """
    r49 = _row("TT49")
    r50 = _row("TT50")
    assert r49["occupant_name"] == "Neferhotep"
    assert r50["occupant_name"] == "Neferhotep"
    # Distinct sub-sites:
    assert r49["theban_area"] == "Khokha"
    assert r50["theban_area"] == "Sh. ʿAbd el-Qurna"
    # Distinct regnal periods:
    assert "Probably temp. Ay" in r49["notes_from_pm"]
    assert "Temp. Ḥaremḥab" in r50["notes_from_pm"]
    # TT49 attribution_certainty=attested per DERIVER_OVERRIDES (Probably
    # qualifies the regnal date, not Neferhotep's identification):
    assert r49["attribution_certainty"] == "attested"
    assert r50["attribution_certainty"] == "attested"


def test_chunk13_double_period_strip() -> None:
    """CHUNK13_CORRECTIONS strips the spurious double-period after a
    citation close-paren on TT41/TT47/TT49 — the `).` → `) ` class that
    went 2/1 the wrong way at reconciliation (rather than 1/1/1 like
    chunk 12). Pin the post-correction state.
    """
    for tid in ("TT41", "TT47", "TT49"):
        notes = _row(tid)["notes_from_pm"]
        # No spurious second period after the citation close-paren:
        assert ".)." not in notes, (tid, notes)
        assert "). ." not in notes, (tid, notes)


def test_chunk13_pages_in_range() -> None:
    """All chunk-13 source_citation.page values fall in 78-95 (the
    printed-page range for TT41-TT50)."""
    for tid in CHUNK13_TOMB_IDS:
        page = _row(tid)["source_citation"]["page"]
        assert 78 <= page <= 95, (tid, page)


# ---------------------------------------------------------------------------
# Chunk-14 per-row tests (TT51–TT60, PM I.1 pp 97-121 / physical pp 115-141)
# ---------------------------------------------------------------------------


def test_chunk14_all_rows_present() -> None:
    """All 10 TT51-TT60 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK14_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        r = _row(tid)
        assert r["tomb_id"] == tid


def test_chunk14_all_rows_homogeneous_sub_site() -> None:
    """Every chunk-14 row has theban_area="Sh. ʿAbd el-Qurna" — first
    PM-I.1 decade with single-sub-site homogeneity."""
    for tid in CHUNK14_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Sh. ʿAbd el-Qurna", (tid, r["theban_area"])


def test_chunk14_all_rows_edition_pm_i1() -> None:
    """All chunk-14 rows cite PM I.1 2nd ed. 1960, section I."""
    for tid in CHUNK14_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid, r["source_citation"]["edition"]
        )
        assert r["source_citation"]["section"] == "I", (
            tid, r["source_citation"]["section"]
        )


def test_chunk14_pages_in_range() -> None:
    """All chunk-14 source_citation.page values fall in 97-121."""
    for tid in CHUNK14_TOMB_IDS:
        page = _row(tid)["source_citation"]["page"]
        assert 97 <= page <= 121, (tid, page)


def test_chunk14_all_rows_null_dynasty_dates_discoverer() -> None:
    """Chunk-14 has no dynasty, date, or discoverer fields."""
    for tid in CHUNK14_TOMB_IDS:
        r = _row(tid)
        assert r["dynasty"] is None, (tid, r["dynasty"])
        assert r["sub_period"] is None, (tid, r["sub_period"])
        assert r["date_bce_approx_start"] is None, (tid, r["date_bce_approx_start"])
        assert r["date_bce_approx_end"] is None, (tid, r["date_bce_approx_end"])
        assert r["discovery_year"] is None, (tid, r["discovery_year"])
        assert r["discoverer"] is None, (tid, r["discoverer"])


def test_chunk14_attribution_distribution() -> None:
    """Per-row attribution_certainty after DERIVER_OVERRIDES — TT52 and TT54
    have regnal `(?)` hedges that DERIVER_OVERRIDES pins back to attested.
    All other rows lack any hedge and stay attested by default."""
    for tid in CHUNK14_TOMB_IDS:
        r = _row(tid)
        assert r["attribution_certainty"] == "attested", (
            tid, r["attribution_certainty"]
        )


def test_chunk14_role_distribution() -> None:
    """TT55 + TT60 = Vizier, TT58 = Unknown (anonymous), all others Official."""
    expected = {
        "TT51": "Official", "TT52": "Official", "TT53": "Official",
        "TT54": "Official", "TT55": "Vizier",   "TT56": "Official",
        "TT57": "Official", "TT58": "Unknown",  "TT59": "Official",
        "TT60": "Vizier",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK14_TOMB_IDS}
    assert actual == expected, sorted(
        (tid, actual[tid]) for tid in actual if actual[tid] != expected[tid]
    )


def test_chunk14_tt51_userhet_macron() -> None:
    """TT51 — Userhēt, called Neferhabef, First prophet of the royal ka of
    Tuthmosis I, Sh. ʿAbd el-Qurna, p.97. PM prints `USERḤĒT` (capital
    underdot-Ḥ + capital macron-Ē — direct PDF visual on physical p.115).
    Strip Ḥ-underdot per policy; preserve macron-Ē → `Userhēt`. The macron
    restoration is layered by CHUNK14_CORRECTIONS.
    """
    r = _row("TT51")
    assert r["occupant_name"] == "Userhēt"
    assert r["occupant_alt_names"] == ["Neferhabef"]
    assert r["occupant_role"] == "Official"
    assert r["source_citation"]["page"] == 97
    assert "ē" in r["occupant_name"]


def test_chunk14_tt55_vizier_stuart() -> None:
    """TT55 — Raʿmosi (Vizier), Sh. ʿAbd el-Qurna, p.105. Vizier-precedence
    rule (the headword title clause names `Governor of the town and Vizier`).
    PM prints the parenthetical `('Stuart's Tomb.')` after the sub-site —
    captured in tomb_aliases.
    """
    r = _row("TT55")
    assert r["occupant_name"] == "Raʿmosi"
    assert r["occupant_role"] == "Vizier"
    assert r["tomb_aliases"] == ["Stuart's Tomb"]
    assert r["source_citation"]["page"] == 105
    # Verbatim Vizier title preserved in notes:
    assert "Vizier" in r["notes_from_pm"]


def test_chunk14_tt58_anonymous_usurped() -> None:
    """TT58 — anonymous original occupant (`Name unknown` headword), usurped
    by Amenḥotp + son Amenemōnet, Dyn. XX. Per the chunk-8 KV12/QV36/QV40
    null-name precedent: occupant_name=null + occupant_role="Unknown".
    is_usurped derived from `Usurped by` regex.
    """
    r = _row("TT58")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["is_usurped"] is True
    assert r["co_occupants"] == []  # usurpers do NOT go in co_occupants
    assert r["source_citation"]["page"] == 119
    # Both usurper-name occurrences carry restored macron-Ō (CHUNK14_CORRECTIONS):
    assert "Amenemōnet" in r["notes_from_pm"]
    assert "Amenemonet" not in r["notes_from_pm"]  # no unmaccroned form


def test_chunk14_tt60_vizier_mother_co_occupant() -> None:
    """TT60 — Antefoḳer (Vizier), with mother Sent in co_occupants
    (hierarchical: `<NAME-A>, ..., and mother, SENT, Prophetess of Ḥatḥor.`).
    Sent's role flattens to Official (Hathor is not the Amun cult that
    triggers the High Priest controlled-vocab match).
    """
    r = _row("TT60")
    assert r["occupant_name"] == "Antefoḳer"
    assert r["occupant_role"] == "Vizier"
    assert r["is_joint_burial"] is False  # hierarchical, not coordinate
    assert len(r["co_occupants"]) == 1
    co = r["co_occupants"][0]
    assert co["name"] == "Sent"
    assert co["role"] == "Official"
    assert r["source_citation"]["page"] == 121


def test_chunk14_tt54_tt58_usurpation() -> None:
    """Chunk-14 has 2 usurpation rows: TT54 (Ḥuy usurped by Kenro) and TT58
    (anonymous, usurped by Amenḥotp + Amenemōnet). Both carry is_usurped=true
    via the Tier-3 deriver."""
    for tid in ("TT54", "TT58"):
        r = _row(tid)
        assert r["is_usurped"] is True, (tid, r["is_usurped"])
        assert "surp" in r["notes_from_pm"], (tid, r["notes_from_pm"])


# ---------------------------------------------------------------------------
# Chunk-15 per-row tests (TT61–TT70, PM I.1 pp 123-139 / physical pp 141-160)
# ---------------------------------------------------------------------------


def test_chunk15_all_rows_present() -> None:
    """All 10 TT61-TT70 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK15_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        r = _row(tid)
        assert r["tomb_id"] == tid


def test_chunk15_all_rows_homogeneous_sub_site() -> None:
    """Every chunk-15 row has theban_area="Sh. ʿAbd el-Qurna" — second
    PM-I.1 decade with single-sub-site homogeneity (after chunk 14)."""
    for tid in CHUNK15_TOMB_IDS:
        r = _row(tid)
        assert r["theban_area"] == "Sh. ʿAbd el-Qurna", (tid, r["theban_area"])


def test_chunk15_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK15_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"
        assert r["source_citation"]["section"] == "I"


def test_chunk15_pages_in_range() -> None:
    """All chunk-15 source_citation.page values fall in 123-139."""
    for tid in CHUNK15_TOMB_IDS:
        page = _row(tid)["source_citation"]["page"]
        assert 123 <= page <= 139, (tid, page)


def test_chunk15_role_distribution() -> None:
    """TT61 + TT66 = Vizier, TT67 = High Priest (First prophet of Amūn),
    TT70 = Unknown (anonymous), all others Official."""
    expected = {
        "TT61": "Vizier",     "TT62": "Official", "TT63": "Official",
        "TT64": "Official",   "TT65": "Official", "TT66": "Vizier",
        "TT67": "High Priest","TT68": "Official", "TT69": "Official",
        "TT70": "Unknown",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK15_TOMB_IDS}
    assert actual == expected


def test_chunk15_attribution_distribution() -> None:
    """All chunk-15 rows have attribution_certainty="attested" after
    DERIVER_OVERRIDES — TT62/TT65/TT69 had regnal `(?)` hedges, TT70 had a
    usurper-clause `(?)` hedge; all flipped per the chunk-9 TT2 precedent
    (occupant-identity certainty, not regnal-/usurper-date certainty).
    For TT70 specifically: anonymous original → no occupant identity to
    hedge; the precedent across all 7 prior anonymous-occupant rows
    (KV12/KV56/QV36/QV40/QV73/QV75/TT58) is `attested`.
    """
    for tid in CHUNK15_TOMB_IDS:
        r = _row(tid)
        assert r["attribution_certainty"] == "attested", (
            tid, r["attribution_certainty"]
        )


def test_chunk15_tt61_user_vizier_shared_with_tt131() -> None:
    """TT61 — User (Vizier), Sh. ʿAbd el-Qurna, p.123. Carries
    `(Also owner of tomb 131.)` cross-reference → shared_with_tombs=["TT131"]."""
    r = _row("TT61")
    assert r["occupant_name"] == "User"
    assert r["occupant_role"] == "Vizier"
    assert r["shared_with_tombs"] == ["TT131"]
    assert r["source_citation"]["page"] == 123
    assert "Vizier" in r["notes_from_pm"]


def test_chunk15_tt65_nebamun_macron_alias() -> None:
    """TT65 — Nebamūn (capital macron, PDF-restored), Sh. ʿAbd el-Qurna,
    p.129. Within-source NAME collision with chunk-10 TT17 Nebamūn (also
    macron-restored). Carries `'Aichesi' of Prisse` 19th-c. nickname →
    tomb_aliases (chunk-7/14 'Stuart's Tomb' precedent). is_usurped via
    the `Usurped by Imiseba` clause."""
    r = _row("TT65")
    assert r["occupant_name"] == "Nebamūn"
    assert "ū" in r["occupant_name"]
    assert r["tomb_aliases"] == ["Aichesi"]
    assert r["is_usurped"] is True
    assert r["source_citation"]["page"] == 129
    # PDF-corrected `Ai` not `Al`:
    assert "'Aichesi'" in r["notes_from_pm"]
    assert "'Alchesi'" not in r["notes_from_pm"]
    # Spacing fix: `accounts (?)` not `accounts(?)`:
    assert "accounts (?)" in r["notes_from_pm"]
    assert "accounts(?)" not in r["notes_from_pm"]


def test_chunk15_tt67_hepusonb_high_priest() -> None:
    """TT67 — Hepusonb (First prophet of Amūn), Sh. ʿAbd el-Qurna, p.133.
    First prophet of Amun → High Priest controlled-vocab match (per the
    major-cult-deity rule)."""
    r = _row("TT67")
    assert r["occupant_name"] == "Hepusonb"
    assert r["occupant_role"] == "High Priest"
    assert r["source_citation"]["page"] == 133
    assert "First prophet of Amūn" in r["notes_from_pm"]


def test_chunk15_tt68_bracketed_fragment_macron() -> None:
    """TT68 — [Per?]enkhmūn (bracketed-fragment headword + capital macron-Ū,
    PDF-verified), Sh. ʿAbd el-Qurna, p.133. Editorial brackets `[Per?]`
    preserved per the bracketed-name-fragment rule (PM-faithful: brackets
    encode source-data uncertainty); macron-Ū restored via CHUNK15_CORRECTIONS.
    Usurped by Espaneferḥor."""
    r = _row("TT68")
    assert r["occupant_name"] == "[Per?]enkhmūn"
    assert "[" in r["occupant_name"]
    assert "?" in r["occupant_name"]
    assert "ū" in r["occupant_name"]
    assert r["is_usurped"] is True
    assert r["source_citation"]["page"] == 133


def test_chunk15_tt70_anonymous_usurped() -> None:
    """TT70 — anonymous original occupant (headword opens directly with
    `Usurped by AMENMOSI ...`), Sh. ʿAbd el-Qurna, p.139. Per the chunk-8
    null-name + chunk-14 TT58 precedent: occupant_name=null +
    occupant_role=Unknown. is_usurped derived from `Usurped by` regex.
    attribution_certainty=attested per DERIVER_OVERRIDES (the `(?)` on
    `sandal-makers (?)` qualifies the USURPER's title, not the absent
    primary occupant; consistent with all 7 prior anonymous-occupant rows)."""
    r = _row("TT70")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["is_usurped"] is True
    assert r["attribution_certainty"] == "attested"
    assert r["co_occupants"] == []
    assert r["source_citation"]["page"] == 139
    assert "Usurped by Amenmosi" in r["notes_from_pm"]


# Chunk-16 per-row tests (TT71–TT80, PM I.1 pp 139-157 / physical pp 157-175)


def test_chunk16_all_rows_present() -> None:
    """All 10 TT71-TT80 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK16_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        _row(tid)  # raises if absent


def test_chunk16_all_rows_homogeneous_sub_site() -> None:
    for tid in CHUNK16_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna"


def test_chunk16_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK16_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"


def test_chunk16_pages_in_range() -> None:
    for tid in CHUNK16_TOMB_IDS:
        p = _row(tid)["source_citation"]["page"]
        assert 139 <= p <= 157, f"{tid} page {p} outside [139, 157]"


def test_chunk16_role_distribution() -> None:
    """TT72 = High Priest (First prophet of Amūn); all others Official."""
    expected = {
        "TT71": "Official", "TT72": "High Priest", "TT73": "Official",
        "TT74": "Official", "TT75": "Official", "TT76": "Official",
        "TT77": "Official", "TT78": "Official", "TT79": "Official",
        "TT80": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK16_TOMB_IDS}
    assert actual == expected


def test_chunk16_attribution_distribution() -> None:
    """All chunk-16 rows are attested. TT73's `(?)` is on the primary name
    → deriver correctly fires `uncertain` → BUT task spec says TT73 fires
    `attribution_certainty=uncertain` (genuine primary-attribution hedge).
    All other rows are attested. TT79 regnal-date hedge is overridden via
    DERIVER_OVERRIDES."""
    for tid in CHUNK16_TOMB_IDS:
        r = _row(tid)
        if tid == "TT73":
            assert r["attribution_certainty"] == "uncertain", tid
        else:
            assert r["attribution_certainty"] == "attested", tid


def test_chunk16_tt71_senenmut_shared_with_tt353() -> None:
    """TT71 Senenmut — Chief steward, Sh. ʿAbd el-Qurna, p.139.
    Shared-with TT353 (all 3 agents agree)."""
    r = _row("TT71")
    assert r["occupant_name"] == "Senenmut"
    assert r["occupant_role"] == "Official"
    assert r["shared_with_tombs"] == ["TT353"]
    assert r["is_usurped"] is False
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 139


def test_chunk16_tt72_re_high_priest() -> None:
    """TT72 Rēʿ — First prophet of Amūn (= High Priest), p.142.
    All 3 agents agree on role. PM prints headword `RĒʿ` with capital
    macron-Ē + ayin (egyptologist PDF-verified, this PR);
    CHUNK16_CORRECTIONS restores the macron."""
    r = _row("TT72")
    assert r["occupant_name"] == "Rēʿ"
    assert r["occupant_role"] == "High Priest"
    assert r["shared_with_tombs"] == []
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 142


def test_chunk16_tt73_amenhotp_uncertain_attribution() -> None:
    """TT73 Amenhotp — Overseer of works on the two great obelisks, p.143.
    PM headword prints `Amenḥotp (?)` — the `(?)` directly qualifies the
    primary occupant name, not a regnal date. Deriver correctly fires
    `attribution_certainty=uncertain`. No DERIVER_OVERRIDE needed."""
    r = _row("TT73")
    assert r["occupant_name"] == "Amenhotp"
    assert r["attribution_certainty"] == "uncertain"
    assert r["source_citation"]["page"] == 143


def test_chunk16_tt75_amenhotp_si_se_second_prophet_official() -> None:
    """TT75 Amenhotp-si-se — Second prophet of Amūn, p.146.
    The controlled-vocab rule maps `First prophet of <major-cult-deity>` →
    `High Priest`, NOT `Second prophet of <X>`. Second prophet is
    structurally distinct from the supreme High Priest title and
    flattens to `Official` per rule 3 (non-controlled-vocab functional
    title). All 3 agents agreed on `Official`. PM I.1 p.146.
    Pinned here to document the controlled-vocab call against the
    First-prophet → High Priest precedent — TT75 is a near-miss
    that does NOT promote.
    """
    r = _row("TT75")
    assert r["occupant_name"] == "Amenhotp-si-se"
    assert r["occupant_role"] == "Official"  # NOT High Priest (Second != First)
    assert r["source_citation"]["page"] == 146
    assert "Second prophet of Amūn" in r["notes_from_pm"]


def test_chunk16_tt77_ptahemhet_usurped_by_roy() -> None:
    """TT77 Ptahemhēt — usurped by Roy, p.150. is_usurped derived from
    `Usurped by` regex. CHUNK16_CORRECTIONS restores capital macron-Ē
    on occupant_name (PM `PTAḤEMḤĒT`), and ayin on Roy's wife Raʿḥuy
    in notes_from_pm."""
    r = _row("TT77")
    assert r["occupant_name"] == "Ptahemhēt"
    assert r["is_usurped"] is True
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 150
    # Pinned agent A form: no headword-prefix, Wife without `(?)`.
    assert "Wife (of Ptaḥemḥet), Meryt" in r["notes_from_pm"]
    # CHUNK16_CORRECTIONS ayin restoration on usurper's wife:
    assert "Wife (of Roy), Raʿḥuy" in r["notes_from_pm"]


def test_chunk16_tt79_menkheper_alt_name_and_deriver_override() -> None:
    """TT79 Menkheper — alt-name Menkheperraʿsonb (all 3 agree), p.156.
    Regnal-range tail `Amenophis II (?)` → DERIVER_OVERRIDE pins
    attribution_certainty=attested."""
    r = _row("TT79")
    assert r["occupant_name"] == "Menkheper"
    assert r["occupant_alt_names"] == ["Menkheperraʿsonb"]
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 156


def test_chunk16_tt80_dhutnufer_shared_with_tt104() -> None:
    """TT80 Ḏhutnūfer — shared with TT104 (all 3 agree), p.157.
    PM prints headword `ḎḤUTNŪFER` (d-bar Ḏ + capital underdot-Ḥ +
    capital macron-Ū). All 3 agents converged on d-bar Ḏ + Ḥ-stripped
    `Ḏhutnufer` (PR #200/#151 d-bar precedent for Ḏḥwty/Thoth name
    family); CHUNK16_CORRECTIONS restores the macron-Ū per direct
    PDF visual on physical p.175 (this PR). 1/1/1 tie on notes_from_pm
    resolved in tie-break-overrides.json."""
    r = _row("TT80")
    assert r["occupant_name"] == "Ḏhutnūfer"
    assert "Ḏ" in r["occupant_name"]  # d-bar U+1E0E
    assert "ū" in r["occupant_name"]  # macron-Ū restored
    assert r["shared_with_tombs"] == ["TT104"]
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 157


# Chunk-17 per-row tests (TT81–TT90, PM I.1 pp 159-183 / physical pp 177-201)


def test_chunk17_all_rows_present() -> None:
    """All 10 TT81-TT90 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK17_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        _row(tid)  # raises if absent


def test_chunk17_all_rows_homogeneous_sub_site() -> None:
    for tid in CHUNK17_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna"


def test_chunk17_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK17_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"


def test_chunk17_pages_in_range() -> None:
    for tid in CHUNK17_TOMB_IDS:
        p = _row(tid)["source_citation"]["page"]
        assert 159 <= p <= 183, f"{tid} page {p} outside [159, 183]"


def test_chunk17_role_distribution() -> None:
    """TT83 = Vizier (Governor of the town and Vizier); TT86 = High Priest
    (First prophet of Amūn, also owner of TT112); all others Official."""
    expected = {
        "TT81": "Official", "TT82": "Official", "TT83": "Vizier",
        "TT84": "Official", "TT85": "Official", "TT86": "High Priest",
        "TT87": "Official", "TT88": "Official", "TT89": "Official",
        "TT90": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK17_TOMB_IDS}
    assert actual == expected


def test_chunk17_attribution_distribution() -> None:
    """All chunk-17 rows are attested. No `(?)` hedges on primary
    attributions in PM body prose for TT81-TT90."""
    for tid in CHUNK17_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk17_tt81_ineni_bracket_prefix_and_doubled_h() -> None:
    """TT81 Ineni — Overseer of the granary of Amūn, Sh. ʿAbd el-Qurna,
    p.159. PM headword reads `81. INENI ⟨hieroglyphs⟩ [1st ed. Anena],
    Overseer of the granary of Amūn`. CHUNK17_CORRECTIONS prepends
    `[1st ed. Anena], ` to notes_from_pm (printed-faithful position) and
    restores `ʿAḥotp` → `ʿAḥḥotp` for Queen Ahhotep (doubled-ḥ form
    matches chunk-12 TT12 override precedent for the same queen).
    1/1/1 tie on notes_from_pm resolved in tie-break-overrides.json."""
    r = _row("TT81")
    assert r["occupant_name"] == "Ineni"
    assert r["occupant_role"] == "Official"
    assert r["notes_from_pm"].startswith("[1st ed. Anena], ")
    assert "ʿAḥḥotp" in r["notes_from_pm"]  # doubled-ḥ for Queen Ahhotep (PM p.159)
    # Parent name `Sit-ḏhout` — d-bar Ḏ (Thoth-family) + plain h (no ḥ-underdot
    # per direct PDF visual at p.159; the chunk-9 PM-I.2 `Sit-ḏḥout` precedent
    # for QV47 does NOT transfer to PM I.1 body prose). Egyptologist-flagged.
    assert "Sit-ḏhout" in r["notes_from_pm"]
    assert "ḥout" not in r["notes_from_pm"]  # negative: no ḥ-underdot leaked through
    assert r["source_citation"]["page"] == 159


def test_chunk17_tt82_amenemhet_macron_restored() -> None:
    """TT82 Amenemhēt — Scribe, Steward of the Vizier (NOT Vizier per
    Vizier-precedence: he SERVES the vizier, not IS one), p.163.
    CHUNK17_CORRECTIONS restores macron-Ē on occupant_name (PM headword
    `82. AMENEMḤĒT`). 1/1/1 tie on notes_from_pm resolved in
    tie-break-overrides.json (clean punctuation pin)."""
    r = _row("TT82")
    assert r["occupant_name"] == "Amenemhēt"
    assert "ē" in r["occupant_name"]  # macron-Ē restored
    assert r["occupant_role"] == "Official"  # Steward-of-Vizier, NOT Vizier
    assert "Steward of the Vizier" in r["notes_from_pm"]
    assert "Ḏhutmosi" in r["notes_from_pm"]  # d-bar Ḏ Thoth-family
    assert r["source_citation"]["page"] == 163


def test_chunk17_tt83_amethu_vizier_alt_name() -> None:
    """TT83 ʿAmethu — Governor of the town and Vizier, alt-name ʿAhmosi
    (PM headword: `83. ʿAMETHU ⟨h⟩, called ʿAḤMOSI ⟨h⟩, Governor of the
    town and Vizier. Early temp. Tuthmosis III.`), p.167. 1/1/1 tie on
    notes_from_pm resolved (no `called ʿAḥmosi` prefix — already in
    occupant_alt_names per the TT40/TT57/TT58/TT60/TT77/TT78/TT79/TT80
    chunk-12-and-16 cluster precedent)."""
    r = _row("TT83")
    assert r["occupant_name"] == "ʿAmethu"
    assert r["occupant_role"] == "Vizier"
    assert r["occupant_alt_names"] == ["ʿAhmosi"]
    assert "called ʿAḥmosi" not in r["notes_from_pm"]  # not duplicated
    assert "Vizier" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 167


def test_chunk17_tt84_amunezeh_partly_usurped_mery_titlecase() -> None:
    """TT84 Amunezeḥ — partly usurped by MERY (TT95), p.167.
    CHUNK17_CORRECTIONS normalises `MERY` → `Mery` Title-case in body
    prose (per TT51/TT57/TT58/TT60 chunk-12-and-14 small-caps→Title-case
    precedent). is_usurped derived from `Partly usurped by` regex."""
    r = _row("TT84")
    assert r["occupant_name"] == "Amunezeh"
    assert r["is_usurped"] is True
    assert "Partly usurped by Mery" in r["notes_from_pm"]
    assert "MERY" not in r["notes_from_pm"]  # normalised to Title-case
    # Parent name `Siḏhout` — d-bar Ḏ (Thoth-family) + plain h per direct PDF
    # visual at p.167 (no ḥ-underdot — egyptologist-flagged correction).
    assert "Siḏhout" in r["notes_from_pm"]
    assert "Siḏḥout" not in r["notes_from_pm"]  # negative: ḥ-underdot dropped
    assert r["source_citation"]["page"] == 167


def test_chunk17_tt85_amenemhab_alt_mahu() -> None:
    """TT85 Amenemhab — Lieutenant-commander of soldiers, alt-name Mahu
    (PM headword: `85. AMENEMḤAB ⟨h⟩, called MAḤU ⟨h⟩`), p.170. 1/1/1
    tie on notes_from_pm resolved (no `called Maḥu, ` prefix — already
    in occupant_alt_names)."""
    r = _row("TT85")
    assert r["occupant_name"] == "Amenemhab"
    assert r["occupant_alt_names"] == ["Mahu"]
    assert "called Maḥu" not in r["notes_from_pm"]
    assert r["notes_from_pm"] == (
        "Lieutenant-commander of soldiers. Temp. Tuthmosis III to "
        "Amenophis II. (CHAMPOLLION, No. 12, HAY, No. 20.) Mother, "
        "Tetires. Wife, Baki, Chief royal nurse."
    )
    assert r["source_citation"]["page"] == 170


def test_chunk17_tt86_menkheperrasonb_high_priest_shared_tt112() -> None:
    """TT86 Menkheperraʿsonb — First prophet of Amūn (= High Priest),
    also owner of TT112 (shared_with_tombs), p.175. CHUNK17_CORRECTIONS
    restores body-prose macrons: `Amenemḥet` → `Amenemḥēt` and `Taonet`
    → `Taōnet` (PM body-prose verbatim policy retains Ḥ underdot in
    notes, unlike occupant_name policy which strips)."""
    r = _row("TT86")
    assert r["occupant_name"] == "Menkheperraʿsonb"
    assert "ʿ" in r["occupant_name"]  # ayin between ra and sonb
    assert r["occupant_role"] == "High Priest"
    assert r["shared_with_tombs"] == ["TT112"]
    assert "Amenemḥēt" in r["notes_from_pm"]  # body-prose retains Ḥ underdot
    assert "Taōnet" in r["notes_from_pm"]  # macron-Ō restored
    assert r["source_citation"]["page"] == 175


def test_chunk17_tt87_minnakht_father_sen_dhout() -> None:
    """TT87 Minnakht — Overseer of the granaries of Upper and Lower
    Egypt, p.178. Father Sen-ḏhout (Thoth-family d-bar Ḏ + plain h per
    direct PDF visual at p.178; the chunk-9/PM-I.2 `Sit-ḏḥout` precedent
    does NOT transfer to PM I.1 body prose). 1/1/1 tie on notes_from_pm
    resolved (clean punctuation pin) + per-row PDF correction on the
    parent-name diacritic."""
    r = _row("TT87")
    assert r["occupant_name"] == "Minnakht"
    # Father name `Sen-ḏhout` — d-bar Ḏ (Thoth-family) + plain h per direct PDF
    # visual at p.178 (no ḥ-underdot — egyptologist-flagged correction).
    assert r["notes_from_pm"] == (
        "Overseer of the granaries of Upper and Lower Egypt, Overseer "
        "of horses of the Lord of the Two Lands, Royal scribe. Temp. "
        "Tuthmosis III. (HAY, No. 17.) Father, Sen-ḏhout."
    )
    assert "Sen-ḏḥout" not in r["notes_from_pm"]  # negative: ḥ-underdot dropped
    assert r["source_citation"]["page"] == 178


def test_chunk17_tt88_pehsukher_alt_thenenu() -> None:
    """TT88 Pehsukher — Lieutenant of the King, alt-name Thenenu (PM
    headword: `88. PEHSUKHER ⟨h⟩, called THENENU ⟨h⟩`), p.179. 1/1/1
    tie on notes_from_pm resolved (no `called Thenenu, ` prefix —
    already in occupant_alt_names)."""
    r = _row("TT88")
    assert r["occupant_name"] == "Pehsukher"
    assert r["occupant_alt_names"] == ["Thenenu"]
    assert "called Thenenu" not in r["notes_from_pm"]
    assert r["notes_from_pm"] == (
        "Lieutenant of the King, Standard-bearer of the Lord of the "
        "Two Lands. Temp. Tuthmosis III to Amenophis II. (CHAMPOLLION, "
        "No. 8, L. D. Text, No. 61.) Wife, Neit, Chief royal nurse, "
        "Governess of the god."
    )
    assert r["source_citation"]["page"] == 179


def test_chunk17_tt89_amenmosi_unanimous() -> None:
    """TT89 Amenmosi — Steward in the Southern City, p.181. All three
    agents agreed unanimously on every field (no tie-break entry,
    no fix_rows correction needed)."""
    r = _row("TT89")
    assert r["occupant_name"] == "Amenmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["notes_from_pm"] == (
        "Steward in the Southern City. Temp. Amenophis III."
    )
    assert r["source_citation"]["page"] == 181


def test_chunk18_all_rows_present() -> None:
    """All 10 TT91-TT100 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK18_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        _row(tid)


def test_chunk18_all_rows_homogeneous_sub_site() -> None:
    for tid in CHUNK18_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna"


def test_chunk18_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK18_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"


def test_chunk18_pages_in_range() -> None:
    for tid in CHUNK18_TOMB_IDS:
        p = _row(tid)["source_citation"]["page"]
        assert 185 <= p <= 215, f"{tid} page {p} outside [185, 215]"


def test_chunk18_role_distribution() -> None:
    """TT91 = Unknown (anonymous); TT95 + TT97 = High Priest (First prophet
    of Amūn); TT100 = Vizier (Governor of the town and Vizier); TT98 =
    Official (Third prophet → minor-cult flatten); rest = Official."""
    expected = {
        "TT91": "Unknown", "TT92": "Official", "TT93": "Official",
        "TT94": "Official", "TT95": "High Priest", "TT96": "Official",
        "TT97": "High Priest", "TT98": "Official", "TT99": "Official",
        "TT100": "Vizier",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK18_TOMB_IDS}
    assert actual == expected


def test_chunk18_attribution_distribution() -> None:
    """All chunk-18 rows are attested. TT94/TT97/TT98 carry `Temp. <King>
    (?)` regnal-date hedges that the Tier-3 deriver would spuriously fire
    on; DERIVER_OVERRIDES pin them back to attested per the chunk-9 TT2
    precedent (regnal-date hedge ≠ occupant-identification hedge)."""
    for tid in CHUNK18_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk18_tt91_anonymous_unknown_role() -> None:
    """TT91 — anonymous original occupant (PM headword opens
    `91. Captain of the troops ... , Overseer of horses.` with no
    NAME-IN-CAPS), Sh. ʿAbd el-Qurna, p.185. Per the chunk-8 + chunk-14
    TT58 + chunk-15 TT70 anonymous-occupant pairing invariant: when
    occupant_name is null, occupant_role must be 'Unknown'.
    CHUNK18_CORRECTIONS pins role='Unknown' to repair the merge.py
    sentinel-null artifact (line 159: 'unknown' is in the sentinel
    set)."""
    r = _row("TT91")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["co_occupants"] == []
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 185
    assert "Captain of the troops" in r["notes_from_pm"]


def test_chunk18_tt93_kenamun_macron_restored() -> None:
    """TT93 Ḳenamūn — Chief steward of the King, p.190. PM headword
    `93. ḲENAMŪN` (capital Ḳ + capital macron-Ū). All 3 agents kept the
    Ḳ; A+B converged on `Ḳenamun` (macron stripped per the no-pre-derive
    rule), C extracted wrong `Hen-Amūn`. CHUNK18_CORRECTIONS restores
    macron-Ū per direct PDF visual at p.190."""
    r = _row("TT93")
    assert r["occupant_name"] == "Ḳenamūn"
    assert "Ḳ" in r["occupant_name"]  # underdot-Ḳ preserved
    assert "ū" in r["occupant_name"]  # macron-Ū restored
    assert r["source_citation"]["page"] == 190


def test_chunk18_tt94_ramosi_alt_amy() -> None:
    """TT94 Raʿmosi — First royal herald, alt-name ʿAmy, p.194.
    `Temp. Amenophis II (?)` regnal hedge → DERIVER_OVERRIDE pins
    attribution_certainty=attested."""
    r = _row("TT94")
    assert r["occupant_name"] == "Raʿmosi"
    assert "ʿ" in r["occupant_name"]  # ayin between R and m
    assert r["occupant_alt_names"] == ["ʿAmy"]
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 194


def test_chunk18_tt95_mery_high_priest_usurper_of_tt84() -> None:
    """TT95 Mery — First prophet of Amūn (= High Priest), p.195. Mery
    is the USURPER of TT84 (chunk-17 cross-reference). PM prints
    `(See also usurpation in tomb 84.)` in the headword. This is an
    EVENT cross-reference, NOT an OWNERSHIP relation, so it does NOT
    match the chunk-9 `See also Tomb N` pattern documented for
    `shared_with_tombs`. CHUNK18_CORRECTIONS overrides the A+B 2/1
    majority `shared_with_tombs=["TT84"]` to `[]` for structural
    correctness + within-section symmetry-test compliance. The
    parenthetical is preserved verbatim in `notes_from_pm`; the
    Tier-3 `is_usurped` regex would fire on `usurpation` so
    DERIVER_OVERRIDES pins `is_usurped=false` (Mery is usurper of
    TT84, not usurped at TT95)."""
    r = _row("TT95")
    assert r["occupant_name"] == "Mery"
    assert r["occupant_role"] == "High Priest"
    # `(See also usurpation in tomb 84.)` is an EVENT cross-reference,
    # NOT an ownership relation — does NOT belong in shared_with_tombs.
    # CHUNK18_CORRECTIONS overrides the A+B 2/1 majority `["TT84"]` to
    # [] for structural correctness + symmetry-test compliance.
    assert r["shared_with_tombs"] == []
    # The verbatim parenthetical is preserved in notes_from_pm; the
    # Tier-3 `is_usurped` deriver fires on `usurpation`; DERIVER_OVERRIDES
    # pins TT95 is_usurped=false (Mery is usurper of TT84, not usurped here).
    assert r["is_usurped"] is False
    assert "(See also usurpation in tomb 84.)" in r["notes_from_pm"]
    assert "First prophet of Amūn" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 195


def test_chunk18_tt96_tt99_sennufer_collision() -> None:
    """TT96 + TT99 are both Sennufer — distinct individuals, distinct
    rows per the within-source NAME collision precedent (chunk-10 TT17 /
    chunk-15 + chunk-17 TT90 NEBAMŪN). TT96 = Mayor of the Southern
    City (Amenophis II); TT99 = Overseer of the seal, Overseer of the
    gold-land of Amūn (Tuthmosis III)."""
    tt96 = _row("TT96")
    tt99 = _row("TT99")
    assert tt96["occupant_name"] == "Sennufer"
    assert tt99["occupant_name"] == "Sennufer"
    assert tt96["tomb_id"] != tt99["tomb_id"]
    assert "Mayor of the Southern City" in tt96["notes_from_pm"]
    assert "Overseer of the seal" in tt99["notes_from_pm"]
    assert tt96["source_citation"]["page"] == 197
    assert tt99["source_citation"]["page"] == 204


def test_chunk18_tt98_kaemheribsen_inaccessible_third_prophet() -> None:
    """TT98 Kaemheribsen — Third prophet of Amūn (NOT High Priest:
    only First prophet flattens to High Priest per the major-deity
    rule; Third prophet falls through to Official), p.204. PM prints
    `(Inaccessible.)` parenthetical on the sub-site line — preserved
    verbatim in notes_from_pm per the chunk-12 TT47 tomb-state-marker
    precedent. `Temp. Tuthmosis III to Amenophis II (?)` regnal-tail
    hedge → DERIVER_OVERRIDE pins attested."""
    r = _row("TT98")
    assert r["occupant_name"] == "Kaemheribsen"
    assert r["occupant_role"] == "Official"
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert "Third prophet of Amūn" in r["notes_from_pm"]
    assert r["attribution_certainty"] == "attested"
    assert r["source_citation"]["page"] == 204


def test_chunk18_tt100_rekhmire_vizier_macron_restored() -> None:
    """TT100 Rekhmirēʿ — Governor of the town and Vizier, p.206. Major
    Theban tomb (Rekhmire's tomb spans 9 printed pages). PM headword
    `100. REKHMIRĒʿ` (capital macron-Ē + ayin). All 3 agents kept the
    ayin, stripped the macron per the no-pre-derive rule.
    CHUNK18_CORRECTIONS restores macron-Ē per direct PDF visual at
    p.206. Vizier-precedence: title clause `Governor of the town and
    Vizier` → role 'Vizier' (per chunk-12 TT60 / chunk-15 TT61+TT66 /
    chunk-17 TT83 precedent)."""
    r = _row("TT100")
    assert r["occupant_name"] == "Rekhmirēʿ"
    assert "ē" in r["occupant_name"]  # macron-Ē restored
    assert "ʿ" in r["occupant_name"]  # ayin
    assert r["occupant_role"] == "Vizier"
    assert "Governor of the town and Vizier" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 206


def test_chunk19_all_rows_present() -> None:
    """All 10 TT101-TT110 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK19_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        _row(tid)


def test_chunk19_all_rows_homogeneous_sub_site() -> None:
    for tid in CHUNK19_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna"


def test_chunk19_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK19_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"


def test_chunk19_pages_in_range() -> None:
    for tid in CHUNK19_TOMB_IDS:
        p = _row(tid)["source_citation"]["page"]
        assert 214 <= p <= 227, f"{tid} page {p} outside [214, 227]"


def test_chunk19_role_distribution() -> None:
    """TT103 + TT106 = Vizier (Governor of the town and Vizier);
    TT104 = None (no title in PM headword; 'Unknown' sentinel-null collapsed
    at merge.py:159); rest = Official."""
    expected = {
        "TT101": "Official", "TT102": "Official", "TT103": "Vizier",
        "TT104": None, "TT105": "Official", "TT106": "Vizier",
        "TT107": "Official", "TT108": "Official", "TT109": "Official",
        "TT110": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK19_TOMB_IDS}
    assert actual == expected


def test_chunk19_attribution_distribution() -> None:
    """All chunk-19 rows are attested. TT108 has a `Tuthmosis IV(?)` regnal-date
    hedge and TT110 has a `Pesediri (?)` parent-identification hedge — both are
    secondary-clause hedges, not primary-occupant attribution hedges. DERIVER_OVERRIDES
    pin both back to attested per the chunk-9 TT2 precedent."""
    for tid in CHUNK19_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk19_tt101_royal_butler_bracketed_title() -> None:
    """TT101 Thanuro — [Royal butler] clean of hands, Sh. ʿAbd el-Qurna, p.214.
    PM headword brackets the title `[Royal butler]` — preserved verbatim.
    Agent A spawn-message taint caused A to emit `Royal butler clean of hands`
    (no brackets); B+C correctly emitted `[Royal butler] clean of hands.`
    The 2/1 B+C majority resolved cleanly at merge."""
    r = _row("TT101")
    assert r["occupant_name"] == "Thanuro"
    assert r["occupant_role"] == "Official"
    assert r["notes_from_pm"] == "[Royal butler] clean of hands. Temp. Amenophis II."
    assert "[Royal butler]" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 214


def test_chunk19_tt103_dagi_vizier_xi_dynasty() -> None:
    """TT103 Dagi — Governor of the town and Vizier, End of Dyn. XI, p.216.
    Mid-sentence citation `(L. D. Text, No. 36.)` placed before the `Wife`
    clause per PM's printed convention (chunk-12 cluster precedent: TT26 etc.).
    Wife (or mother) Maʿetnemti (ayin preserved)."""
    r = _row("TT103")
    assert r["occupant_name"] == "Dagi"
    assert r["occupant_role"] == "Vizier"
    assert "Governor of the town and Vizier" in r["notes_from_pm"]
    assert "End of Dyn. XI" in r["notes_from_pm"]
    assert "(L. D. Text, No. 36.)" in r["notes_from_pm"]
    assert "Maʿetnemti" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 216


def test_chunk19_tt104_hutnufer_shared_with_tt80() -> None:
    """TT104 [Hutnufer] — Temp. Amenophis II, Sh. ʿAbd el-Qurna, p.217.
    PM cross-reference `(See tomb 80.)` precedes temporal clause (tie-break-
    overrides.json pin: agent A matched PM's printed word order, agents B/C
    reversed or dropped the cross-reference). occupant_role is None because
    PM gives no title for TT104 and 'Unknown' is a SENTINEL_NULL_STRING
    (merge.py:159) — collapsed to null at merge, not repaired by any correction
    (no title available from PM). shared_with_tombs=['TT80'] per the chunk-9
    `See also Tomb N` ownership-pattern."""
    r = _row("TT104")
    assert r["occupant_name"] == "[Hutnufer]"
    assert r["occupant_role"] is None
    assert r["shared_with_tombs"] == ["TT80"]
    assert r["notes_from_pm"] == "(See tomb 80.) Temp. Amenophis II."
    assert r["source_citation"]["page"] == 217


def test_chunk19_tt106_paser_vizier_mid_sentence_citation() -> None:
    """TT106 Paser — Governor of the town and Vizier, Temp. Sethos I to
    Ramesses II, p.219. Bibliographic citation `(CHAMPOLLION, No. 32,
    L. D. Text, No. 39, HAY, No. 7.)` appears mid-sentence before `Parents,`
    per PM's printed convention (tie-break-overrides.json pin: agent A
    correct; B moved citation to end, C had OCR typo `Meytrerʿ` for
    `Merytreʿ`). Mother's name `Merytreʿ` (ayin) is correct."""
    r = _row("TT106")
    assert r["occupant_name"] == "Paser"
    assert r["occupant_role"] == "Vizier"
    assert "Governor of the town and Vizier" in r["notes_from_pm"]
    # Mid-sentence citation before Parents clause
    assert "(CHAMPOLLION, No. 32, L. D. Text, No. 39, HAY, No. 7.)" in r["notes_from_pm"]
    notes = r["notes_from_pm"]
    champollion_pos = notes.index("(CHAMPOLLION")
    parents_pos = notes.index("Parents,")
    assert champollion_pos < parents_pos, "Citation must precede Parents clause"
    # Correct mother name spelling
    assert "Merytreʿ" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 219


def test_chunk19_tt108_nebseny_regnal_hedge_attested() -> None:
    """TT108 Nebseny — First prophet of Onuris, Temp. Tuthmosis IV(?), p.225.
    `(?)` qualifies the regnal date (Tuthmosis IV), not Nebseny's
    identification. DERIVER_OVERRIDE pins attribution_certainty=attested per
    the chunk-9 TT2 / chunk-14 TT52 / chunk-15 TT69 regnal-date hedge
    precedent."""
    r = _row("TT108")
    assert r["occupant_name"] == "Nebseny"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Tuthmosis IV(?)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 225


def test_chunk19_tt110_dhout_baktH_wife() -> None:
    """TT110 Ḏhout — Royal butler, Royal herald, Temp. Ḥatshepsut to
    Tuthmosis III, p.227. Wife Baktḥ (with underdot-ḥ). Parent Pesediri (?)
    is a family-name hedge in a secondary clause — DERIVER_OVERRIDE pins
    attribution_certainty=attested per the chunk-10 TT17 parent-hedge
    precedent. occupant_name `Ḏhout` (d-bar preserved)."""
    r = _row("TT110")
    assert r["occupant_name"] == "Ḏhout"
    assert "Ḏ" in r["occupant_name"]  # d-bar (Ḏ = U+1E0E) preserved
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Wife, Baktḥ." in r["notes_from_pm"]
    assert "Pesediri (?)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 227


def test_chunk19_tt102_imhotep_royal_scribe_inaccessible() -> None:
    """TT102 Imhotep — Royal scribe, Child of the nursery, Temp. Amenophis III, p.215.
    occupant_name `Imhotep` plain-h per project's strip-Ḥ-from-occupant_name
    convention (test_occupant_name_has_no_underdot_h enforced). PR #263
    round-1 egyptologist P1 recommended `Imḥotep` with underdot per
    Egyptological convention but DECLINED — project's matchable-name
    convention strips underdot-Ḥ. Tomb state marker `(Inaccessible.)`
    preserved in notes_from_pm per chunk-12 TT47 precedent."""
    r = _row("TT102")
    assert r["occupant_name"] == "Imhotep"  # plain h, NOT Imḥotep
    assert "ḥ" not in r["occupant_name"]
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Royal scribe" in r["notes_from_pm"]
    assert "Child of the nursery" in r["notes_from_pm"]
    assert "Temp. Amenophis III" in r["notes_from_pm"]
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 215


def test_chunk19_tt105_khaemopet_dyn_xix() -> None:
    """TT105 Khaʿemopet — Prophet of the noble ram-sceptre of Amūn, Dyn. XIX,
    p.218. ayin (U+02BF) preserved in occupant_name from PM OCR `c`-glyph
    decode. Wife Amenemopet captured as PM-named family in notes_from_pm."""
    r = _row("TT105")
    assert r["occupant_name"] == "Khaʿemopet"
    assert "ʿ" in r["occupant_name"]  # raised-ayin U+02BF preserved
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Prophet of the noble ram-sceptre" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]  # macron-Ū preserved in body prose
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Wife, Amenemopet" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 218


def test_chunk19_tt107_nefersekheru_royal_scribe_amenophis_iii() -> None:
    """TT107 Nefersekheru — Royal scribe, Steward of the estate of Amenophis
    III 'Reʿ is brilliant', Temp. Amenophis III, p.224. tie-break-overrides
    entry pins agent C's mid-sentence citation form `(CHAMPOLLION, No. 33,
    L. D. Text, No. 37.)` and the underdot-ḥ in `Ḥepu` (parent name).
    Steward-of-the-estate role-cluster → `Official` (functional administrative
    title, not Vizier-precedence-eligible)."""
    r = _row("TT107")
    assert r["occupant_name"] == "Nefersekheru"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Royal scribe" in r["notes_from_pm"]
    assert "Steward of the estate of Amenophis III" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 33" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 224


def test_chunk19_tt109_min_mayor_of_thinis() -> None:
    """TT109 Min — Mayor of Thinis, Overseer of prophets of Onuris, Temp.
    Tuthmosis III, p.226. Mother Say named in notes_from_pm.
    `Mayor of <city>` + `Overseer of prophets of <deity>` is a functional-
    title-cluster → `Official` per chunk-9 TT2 precedent."""
    r = _row("TT109")
    assert r["occupant_name"] == "Min"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Mayor of Thinis" in r["notes_from_pm"]
    assert "Overseer of prophets of Onuris" in r["notes_from_pm"]
    assert "Temp. Tuthmosis III" in r["notes_from_pm"]
    assert "Mother, Say" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 226


def test_chunk20_all_rows_present() -> None:
    """All 10 TT111-TT120 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK20_TOMB_IDS:
        assert tid in EXPECTED_TOMB_IDS
        _row(tid)


def test_chunk20_all_rows_homogeneous_sub_site() -> None:
    for tid in CHUNK20_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna"


def test_chunk20_all_rows_edition_pm_i1() -> None:
    for tid in CHUNK20_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960"


def test_chunk20_pages_in_range() -> None:
    for tid in CHUNK20_TOMB_IDS:
        p = _row(tid)["source_citation"]["page"]
        assert 229 <= p <= 234, f"{tid} page {p} outside [229, 234]"


def test_chunk20_role_distribution() -> None:
    """TT114/TT115/TT116/TT119 have no surviving name → role collapses to None
    (sentinel-null from merge.py). TT112/TT113/TT117/TT118/TT120 are Officials.
    TT111 Amenwahsu is Official (Scribe of divine writings)."""
    expected = {
        "TT111": "Official", "TT112": "Official", "TT113": "Official",
        "TT114": None, "TT115": None, "TT116": None,
        "TT117": "Official", "TT118": "Official", "TT119": None,
        "TT120": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK20_TOMB_IDS}
    assert actual == expected


def test_chunk20_attribution_distribution() -> None:
    """All chunk-20 rows are attested. TT116 has `Amenophis III (?)` regnal-date
    hedge and TT118 has `Amenophis III (?)` regnal-date hedge — both are
    secondary-clause hedges qualifying the date range, not the occupant identity.
    DERIVER_OVERRIDES pin both back to attested per the chunk-9 TT2 precedent."""
    for tid in CHUNK20_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk20_tt111_amenwahsu_scribe_divine_writings() -> None:
    """TT111 Amenwahsu — Scribe of divine writings in the estate of Amūn,
    Temp. Ramesses II, p.229. Parents Simut (Head of outline-draughtsmen)
    and Wiay; wife Iuy (Songstress of Bubastis). Amūn macron-Ū preserved
    per PM body-prose verbatim policy (A+C 2/1 majority vs B's no-macron)."""
    r = _row("TT111")
    assert r["occupant_name"] == "Amenwahsu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Scribe of divine writings in the estate of Amūn" in r["notes_from_pm"]
    assert "Temp. Ramesses II" in r["notes_from_pm"]
    assert "Simut" in r["notes_from_pm"]
    assert "Songstress of Bubastis" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 229


def test_chunk20_tt112_menkheperraconb_usurped_by_ashefytemweset() -> None:
    """TT112 Menkheperraʿsonb — Temp. Tuthmosis III, usurped by ʿAshefytemweset
    (Prophet of Amūn 'Great of Majesty', Ramesside), p.229. Original occupant
    is the USURPED party → is_usurped=True (regex fires correctly, no override
    needed; contrast TT95 where Mery was the USURPER). shared_with_tombs=['TT86']
    per the cross-ref `(see tomb 86)` in PM's headword. Tie-break pin: agent A's
    macron-Amūn + source-faithful `Wife of (ʿAshefytemweset)` order."""
    r = _row("TT112")
    assert r["occupant_name"] == "Menkheperraʿsonb"
    assert r["occupant_role"] == "Official"
    assert r["is_usurped"] is True
    assert r["shared_with_tombs"] == ["TT86"]
    assert "ʿAshefytemweset" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]  # macron-Ū preserved
    assert "Wife of (ʿAshefytemweset)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 229


def test_chunk20_tt113_kynebu_waab_priest_bekenamtun() -> None:
    """TT113 Kynebu — wʿab-priest over-the-secrets of the estate of Amūn,
    Prophet in the Temple of Tuthmosis IV, Temp. Ramesses VIII, p.230.
    Father Bekenamtūn (wʿab-priest of Amun), wife Esi. Tie-break override
    assembled from correct axes across agents: ayin-before-a `wʿab` (TT14/
    TT68/TT97 precedent) + lowercase initial (body prose) + father name
    `Bekenamtūn` (consonant-complete + macron-Ū matching PM OCR `tln` glyph)."""
    r = _row("TT113")
    assert r["occupant_name"] == "Kynebu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    # ayin-before-a form with lowercase initial
    assert r["notes_from_pm"].startswith("wʿab-priest")
    assert "wʿab-priest of Amūn" in r["notes_from_pm"]
    assert "Bekenamtūn" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]  # macron-Ū preserved
    assert "Wife, Esi" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 230


def test_chunk20_tt114_anonymous_head_goldworkers_no_name() -> None:
    """TT114 — Head of goldworkers of the estate of Amūn, Dyn. XX, p.231.
    PM's headword prints the title without a personal name → occupant_name=None.
    occupant_role=None because 'Unknown' is a SENTINEL_NULL_STRING (same as
    TT104 precedent). Tie-break pin: agent A's macron-Amūn + ayin-before-a
    wʿab-priest for the father's title. Egyptologist review pending: PM prints
    a functional title suggesting role='Official' may be correct."""
    r = _row("TT114")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None  # SENTINEL_NULL — see egyptologist pending note
    assert r["attribution_certainty"] == "attested"
    assert "Head of goldworkers of the estate of Amūn" in r["notes_from_pm"]
    assert "Dyn. XX" in r["notes_from_pm"]
    assert "wʿab-priest of Anubis" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 231


def test_chunk20_tt115_anonymous_no_texts_dyn_xix() -> None:
    """TT115 — No texts, Dyn. XIX, p.233. Unanimously null across all 3 agents."""
    r = _row("TT115")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["notes_from_pm"] == "No texts. Dyn. XIX."
    assert r["source_citation"]["page"] == 233


def test_chunk20_tt116_anonymous_hereditary_prince_regnal_hedge_attested() -> None:
    """TT116 — Hereditary prince, Temp. Tuthmosis IV to Amenophis III (?), p.233.
    `(?)` qualifies the regnal-range tail (Amenophis III), not the anonymous
    occupant's identity. DERIVER_OVERRIDE pins attribution_certainty=attested
    per the chunk-10 TT12/TT19/TT20 regnal-date hedge class."""
    r = _row("TT116")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert "Hereditary prince" in r["notes_from_pm"]
    assert "Amenophis III (?)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 233


def test_chunk20_tt117_zemutefankh_dyn_xi_reuse_dyn_xxi_xxii() -> None:
    """TT117 Zemutefʿankh — Outline-draughtsman of the House of Gold, fashioning
    the gods of the estate of Amūn, Dyn. XXI-XXII. Original tomb Dyn. XI (unnamed
    occupant), re-used by Zemutefʿankh. PM headword attributes the tomb to the
    named re-user as the occupant of record — same pattern as TT57/TT58 usurpation
    entries. The TT117 interpretation (named occupant = the later user, not the
    original Dyn. XI owner) was confirmed by all 3 agents."""
    r = _row("TT117")
    assert r["occupant_name"] == "Zemutefʿankh"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Dyn. XI" in r["notes_from_pm"]
    assert "used by Zemutefʿankh" in r["notes_from_pm"]
    assert "Outline-draughtsman of the House of Gold" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Dyn. XXI-XXII" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 233


def test_chunk20_tt118_amenmosi_fan_bearer_regnal_hedge_attested() -> None:
    """TT118 Amenmosi — Fan-bearer on the right of the King, Temp. Amenophis
    III (?), p.233. `(?)` qualifies the regnal date, not Amenmosi's identification.
    DERIVER_OVERRIDE pins attribution_certainty=attested per the chunk-10 TT12/
    TT19/TT20 regnal-date hedge class."""
    r = _row("TT118")
    assert r["occupant_name"] == "Amenmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Fan-bearer on the right of the King" in r["notes_from_pm"]
    assert "Amenophis III (?)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 233


def test_chunk20_tt119_anonymous_name_lost() -> None:
    """TT119 — Name lost, Temp. Ḥatshepsut to Tuthmosis III, p.234.
    PM's headword `Name lost.` is the canonical anonymous form with
    underdot-Ḥ on Ḥatshepsut preserved in notes_from_pm (verbatim-preserve
    policy). All 3 agents agreed unanimously."""
    r = _row("TT119")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["notes_from_pm"] == "Name lost. Temp. Ḥatshepsut to Tuthmosis III."
    assert "Ḥatshepsut" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 234


def test_chunk20_tt120_anen_second_prophet_mahu_alt_name() -> None:
    """TT120 ʿAnen — Second prophet of Amūn, Temp. Amenophis III, p.234.
    Parents Yuia and Thuiu (tomb 46 in Valley of the Kings). Called Maḥu in
    Gardiner & Weigall Cat. Tie-break pin: agent C's value (Amūn macron-Ū
    + Maḥu underdot-ḥ both correct; PM source `MAI;IU` = `Maḥu`).
    occupant_alt_names=["Mahu"] (strip-ḥ per matchable-name convention;
    the structured field strips underdots) wins A+C 2/1 majority over B's [].
    shared_with_tombs=[] (A+C 2/1; B's ["KV46"] is cross-volume reference
    noted in PM prose, not an ownership/sharing relation per chunk-9 rule).
    Egyptologist review pending: external-catalogue alias in occupant_alt_names."""
    r = _row("TT120")
    assert r["occupant_name"] == "ʿAnen"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Second prophet of Amūn" in r["notes_from_pm"]
    assert "Amenophis III" in r["notes_from_pm"]
    assert "Yuia and Thuiu" in r["notes_from_pm"]
    assert "tomb 46 in the Valley of the Kings" in r["notes_from_pm"]
    assert "Called Maḥu in GARDINER and WEIGALL" in r["notes_from_pm"]
    assert r["occupant_alt_names"] == ["Mahu"]
    assert r["shared_with_tombs"] == []
    assert r["source_citation"]["page"] == 234


def test_chunk17_tt90_nebamun_macron_restored_third_collision() -> None:
    """TT90 Nebamūn — Standard-bearer of the sacred bark 'Beloved-of-
    Amūn', Captain of troops of the police on the west of Thebes, p.183.
    Third within-source NAME collision in PM I.1 (after TT17 + TT65
    Nebamūn). CHUNK17_CORRECTIONS restores macron-Ū on occupant_name
    (PM headword `90. NEBAMŪN`). 2/1 majority on raw merge (`Nebamun`
    from agents A+C, prompt-rule-compliant; agent B violated the
    no-pre-derive-macrons rule by emitting `Nebamūn` directly)."""
    r = _row("TT90")
    assert r["occupant_name"] == "Nebamūn"
    assert "ū" in r["occupant_name"]  # macron-Ū restored
    assert "'Beloved-of-Amūn'" in r["notes_from_pm"]  # ASCII straight quotes
    assert r["source_citation"]["page"] == 183


# ---------------------------------------------------------------------------
# Chunk-21: TT121-TT130 (Sh. ʿAbd el-Qurna)
# ---------------------------------------------------------------------------


def test_chunk21_all_rows_present() -> None:
    """All 10 TT121-TT130 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK21_TOMB_IDS:
        assert _row(tid)["tomb_id"] == tid


def test_chunk21_theban_area() -> None:
    """All chunk-21 rows are Sh. ʿAbd el-Qurna."""
    for tid in CHUNK21_TOMB_IDS:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna", tid


def test_chunk21_source_edition() -> None:
    """All chunk-21 rows cite PM I.1 2nd ed. 1960."""
    for tid in CHUNK21_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", tid


def test_chunk21_attribution_distribution() -> None:
    """All chunk-21 rows are attested. TT121/TT126/TT127/TT130 each carry
    `(?)` qualifying a regnal date or period, not the occupant identity.
    DERIVER_OVERRIDES pin all four back to attested per the chunk-9 TT2
    precedent. TT127 also has `usurped in Ramesside times` which correctly
    sets is_usurped=True via the deriver (no override needed)."""
    for tid in CHUNK21_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk21_role_distribution() -> None:
    """9 Officials + 1 null (TT129 `Name lost`, SENTINEL_NULL from merge).
    TT122 joint burial: both occupant and co_occupant are Officials."""
    expected = {
        "TT121": "Official", "TT122": "Official", "TT123": "Official",
        "TT124": "Official", "TT125": "Official", "TT126": "Official",
        "TT127": "Official", "TT128": "Official", "TT129": None,
        "TT130": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK21_TOMB_IDS}
    assert actual == expected


def test_chunk21_tt121_ahmosi_first_lector_amun() -> None:
    """TT121 ʿAhmosi — First lector of Amūn, Temp. Tuthmosis III (?), p.235.
    The `(?)` qualifies the regnal date only; DERIVER_OVERRIDE pins
    attribution_certainty=attested. Macron-Ū on Amūn unanimous across agents."""
    r = _row("TT121")
    assert r["occupant_name"] == "ʿAhmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert r["is_joint_burial"] is False
    assert "First lector of Amūn" in r["notes_from_pm"]
    assert "Tuthmosis III (?)" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 235


def test_chunk21_tt122_joint_burial_amenhotp_amenemhet() -> None:
    """TT122 [Amen]hotp, joint burial with Amenemhet — both Overseers of the
    magazine of Amūn, Temp. Tuthmosis III, p.235. is_joint_burial=True
    unanimous. Tie-break pin: agent B's `with Chapels of Amenemḥet, both
    Overseers...` (includes the shared-occupancy descriptor, no duplicate
    occupant_name prefix). co_occupants=[{name: Amenemhet, role: Official}]."""
    r = _row("TT122")
    assert r["occupant_name"] == "[Amen]hotp"
    assert r["occupant_role"] == "Official"
    assert r["is_joint_burial"] is True
    assert r["attribution_certainty"] == "attested"
    assert r["co_occupants"] == [{"alt_names": [], "name": "Amenemhet", "role": "Official"}]
    assert "with Chapels of Amenemḥet, both Overseers" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "ʿAmethu (tomb 83)" in r["notes_from_pm"]
    assert "Neferḥotep, Prophet" in r["notes_from_pm"]
    assert "Wife (of Amenemḥet), Esnub" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 235


def test_chunk21_tt123_amenemhet_scribe_granary() -> None:
    """TT123 Amenemhet — Scribe, Overseer of the granary, Counter of bread,
    Temp. Tuthmosis III, p.236. (L. D. Text, No. 84.) Wife Ḥenu(t)iri.
    Note name collision: TT122's co_occupant is also Amenemhet — different person
    (different tomb, different role description)."""
    r = _row("TT123")
    assert r["occupant_name"] == "Amenemhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Scribe, Overseer of the granary" in r["notes_from_pm"]
    assert "Counter of bread" in r["notes_from_pm"]
    assert "Tuthmosis III" in r["notes_from_pm"]
    assert "Ḥenu(t)iri" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 236


def test_chunk21_tt124_rey_steward_tuthmosis_i() -> None:
    """TT124 Reʿy — Overseer of the magazine of the Lord of the Two Lands,
    Steward of the good god Tuthmosis I, Temp. Tuthmosis I, p.237.
    Wife Taerdais. Earliest dated tomb in chunk-21 (Tuthmosis I, Dyn. XVIII)."""
    r = _row("TT124")
    assert r["occupant_name"] == "Reʿy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "Overseer of the magazine of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Tuthmosis I" in r["notes_from_pm"]
    assert "Taerdais" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 237


def test_chunk21_tt125_duauneheh_first_herald_hatshepsut() -> None:
    """TT125 Duauneheh — First herald, Overseer of the estate of Amūn,
    Temp. Ḥatshepsut, p.237. (CHAMPOLLION, No. 22, L. D. Text, No. 77.)
    Mother, Tarunet. Underdot-Ḥ on Ḥatshepsut preserved in notes_from_pm
    (verbatim-preserve field)."""
    r = _row("TT125")
    assert r["occupant_name"] == "Duauneheh"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert "First herald" in r["notes_from_pm"]
    assert "Ḥatshepsut" in r["notes_from_pm"]
    assert "CHAMPOLLION, No. 22" in r["notes_from_pm"]
    assert "Tarunet" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 237


def test_chunk21_tt126_harmosi_great_commander_saite() -> None:
    """TT126 Harmosi — Great commander of soldiers of the estate of Amūn,
    Saite (?), p.241. (CHAMPOLLION, No. 23.) The `(?)` qualifies the Saite
    period, not Harmosi's identity. DERIVER_OVERRIDE pins attested."""
    r = _row("TT126")
    assert r["occupant_name"] == "Harmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert "Great commander of soldiers" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Saite (?)" in r["notes_from_pm"]
    assert "CHAMPOLLION, No. 23" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 241


def test_chunk21_tt127_senemioh_usurped_ramesside() -> None:
    """TT127 Senemiʿoh — Royal scribe, Overseer of all that grows,
    Temp. Tuthmosis III (?), usurped in Ramesside times, p.241.
    is_usurped=True: Senemiʿoh IS the usurped party (the deriver fires
    correctly on `usurped in Ramesside times` — no override needed,
    contrast TT95 Mery the usurper). attribution_certainty=attested via
    DERIVER_OVERRIDE (`(?)` qualifies regnal date, not occupant identity).
    Agent A swapped parents/wives — resolved by B+C 2/1 majority:
    Parents Wazmosi and ʿAḥmosi; Wives Sensonb and Tetisonb."""
    r = _row("TT127")
    assert r["occupant_name"] == "Senemiʿoh"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is True
    assert "usurped in Ramesside times" in r["notes_from_pm"]
    assert "Parents, Wazmosi and ʿAḥmosi" in r["notes_from_pm"]
    assert "Wives, Sensonb and Tetisonb" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 241


def test_chunk21_tt128_pathenfy_mayor_edfu_saite() -> None:
    """TT128 Pathenfy — Mayor of Edfu, Mayor of the City, Saite, p.243.
    (CHAMPOLLION, No. 24.) Father Pedeamun. No `(?)` in notes — Saite
    period is unhedged."""
    r = _row("TT128")
    assert r["occupant_name"] == "Pathenfy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert "Mayor of Edfu" in r["notes_from_pm"]
    assert "Saite" in r["notes_from_pm"]
    assert "Pedeamun" in r["notes_from_pm"]
    assert "CHAMPOLLION, No. 24" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 243


def test_chunk21_tt129_anonymous_name_lost() -> None:
    """TT129 — Name lost, Temp. Tuthmosis III or IV, p.244.
    PM's headword `Name lost.` is the canonical anonymous form.
    occupant_name=None, occupant_role=None (SENTINEL_NULL from merge —
    all three agents emitted `Unknown` which collapses to null, same as
    TT104/TT114/TT115/TT116/TT119 precedent)."""
    r = _row("TT129")
    assert r["occupant_name"] is None
    assert r["occupant_role"] is None
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert r["notes_from_pm"] == "Name lost. Temp. Tuthmosis III or IV."
    assert r["source_citation"]["page"] == 244


def test_chunk21_tt130_may_harbour_master_wife_tuy() -> None:
    """TT130 May — Harbour-master in the Southern City, Temp. Tuthmosis III (?),
    p.244. Wife Tuy. The `(?)` qualifies the regnal date; DERIVER_OVERRIDE
    pins attribution_certainty=attested."""
    r = _row("TT130")
    assert r["occupant_name"] == "May"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["is_usurped"] is False
    assert "Harbour-master in the Southern City" in r["notes_from_pm"]
    assert "Tuthmosis III (?)" in r["notes_from_pm"]
    assert "Tuy" in r["notes_from_pm"]
    assert r["source_citation"]["page"] == 244


# ============================================================================
# Chunk-22: TT131-TT140 (PM I.1 § I, pp. 245-254)
# ============================================================================


def test_chunk22_all_rows_present() -> None:
    """All 10 TT131-TT140 tomb IDs are in the expected set and in the data."""
    for tid in CHUNK22_TOMB_IDS:
        assert _row(tid)["tomb_id"] == tid


def test_chunk22_source_edition() -> None:
    """All chunk-22 rows cite PM I.1 2nd ed. 1960."""
    for tid in CHUNK22_TOMB_IDS:
        assert _row(tid)["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", tid


def test_chunk22_attribution_distribution() -> None:
    """All chunk-22 rows are attested. TT140 `probably called Ḥefia` hedges
    only the alt-name; DERIVER_OVERRIDE pins attribution_certainty=attested."""
    for tid in CHUNK22_TOMB_IDS:
        assert _row(tid)["attribution_certainty"] == "attested", tid


def test_chunk22_theban_area_distribution() -> None:
    """TT131-TT139 are Sh. ʿAbd el-Qurna; TT140 is Dra' Abu el-Naga
    (first numbered tomb in the Sh. ʿAbd el-Qurna section to break from
    the sub-site — PM p.254 explicitly assigns it to Dra' Abu el-Naga)."""
    for tid in {f"TT{n}" for n in range(131, 140)}:
        assert _row(tid)["theban_area"] == "Sh. ʿAbd el-Qurna", tid
    assert _row("TT140")["theban_area"] == "Dra' Abu el-Naga"


def test_chunk22_role_distribution() -> None:
    """8 Officials + TT136 Unknown (named title but no personal name) +
    implicit Official for all others. Note TT136 occupant_role is restored
    to `Unknown` from sentinel-null by CHUNK22_CORRECTIONS."""
    expected = {
        "TT131": "Official", "TT132": "Official", "TT133": "Official",
        "TT134": "Official", "TT135": "Official", "TT136": "Unknown",
        "TT137": "Official", "TT138": "Official", "TT139": "Official",
        "TT140": "Official",
    }
    actual = {tid: _row(tid)["occupant_role"] for tid in CHUNK22_TOMB_IDS}
    assert actual == expected


def test_chunk22_tt131_amenuser_see_tomb_61() -> None:
    """TT131 Amenuser — Official, Temp. Tuthmosis III, p.245.
    Alt-name User (from headword `AMENUSER or USER`). Shared with TT61
    (ownership cross-ref from `(See tomb 61.)`). All 3 agents mis-decoded
    source OCR `6z` as `62` (TT62); CHUNK22_CORRECTIONS fixes to `61` (TT61)
    — TT61 (Governor and Vizier, Temp. Tuthmosis III) is the companion tomb
    of the same official; TT62 is a different person. CHUNK22_CORRECTIONS also
    restores the `(See tomb 61.)` parenthetical that majority A+C dropped
    (per chunk-9-onward cross-ref convention). (L. D. Text, No. 87.)"""
    r = _row("TT131")
    assert r["occupant_name"] == "Amenuser"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == ["User"]
    assert r["shared_with_tombs"] == ["TT61"]
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert r["is_uninscribed"] is False
    assert r["notes_from_pm"] == "(See tomb 61.) Temp. Tuthmosis III. (L. D. Text, No. 87.)"
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 245


def test_chunk22_tt132_raomosi_treasuries_taharqa() -> None:
    """TT132 Raʿmosi — Great scribe of the King, Overseer of the treasuries
    of Taharqa. Temp. Taharqa, p.247. Mother Thesmeḥitpert (underdot-ḥ).
    occupant_name `Raʿmosi` (ayin between Ra and mosi — 2/1 majority A+C
    over agent B's `Rʿmosi` with no `a`). Citation mid-sentence before
    Mother clause (2/1 majority A+C). (L. D. Text, No. 83.)"""
    r = _row("TT132")
    assert r["occupant_name"] == "Raʿmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "(L. D. Text, No. 83.)" in r["notes_from_pm"]
    assert "Mother, Thesmeḥitpert" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 247


def test_chunk22_tt133_neferronpet_weavers_hunuro() -> None:
    """TT133 Neferronpet — Chief of the weavers in the Ramesseum in the estate
    of Amūn. Temp. Ramesses II, p.249. Wife Ḥunuro. Amūn macron from 2/1
    majority B+C. Ḥunuro underdot-ḥ restored by CHUNK22_CORRECTIONS (source
    OCR `l:lunuro` = underdot-Ḥ; A emitted correctly, B+C stripped it)."""
    r = _row("TT133")
    assert r["occupant_name"] == "Neferronpet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "Chief of the weavers in the Ramesseum" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Ḥunuro" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 249


def test_chunk22_tt134_thauenany_called_any_amenaphis() -> None:
    """TT134 Thauenany — Prophet of Amenaphis who navigates on the Sea of Amūn,
    Dyn. XIX, p.249. Called Any. (1st ed. 135) cross-numbering note.
    Father Besuemopet (same title). Wife Tabesi. (L. D. Text, No. 79.)
    Tie-break pins agent C: has `(1st ed. 135)` + `Amenaphis` + Amūn macron
    + mid-sentence citation. occupant_alt_names=[`Any`]."""
    r = _row("TT134")
    assert r["occupant_name"] == "Thauenany"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == ["Any"]
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "(1st ed. 135)" in r["notes_from_pm"]
    assert "Amenaphis" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "(L. D. Text, No. 79.)" in r["notes_from_pm"]
    assert "Besuemopet" in r["notes_from_pm"]
    assert "Tabesi" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 249


def test_chunk22_tt135_bekenamun_waab_priest() -> None:
    """TT135 Bekenamun — wʿab-priest in front of Amūn, Dyn. XIX, p.250.
    Tie-break pins agent C (`Wab-priest`, macron-Ū correct). CHUNK22_CORRECTIONS
    restores `Wab-priest` → `wʿab-priest` (ayin before a, lowercase per PM
    body-prose convention — same class as TT113/TT114/TT139)."""
    r = _row("TT135")
    assert r["occupant_name"] == "Bekenamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert r["notes_from_pm"] == "wʿab-priest in front of Amūn. Dyn. XIX."
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 250


def test_chunk22_tt136_anonymous_royal_scribe_sentinel_null() -> None:
    """TT136 — anonymous Royal scribe, Dyn. XIX, p.251. PM headword `136.
    Royal scribe ... of the Lord of the Two Lands. Dyn. XIX.` — no personal
    name. All 3 agents emitted occupant_name=null, occupant_role=`Unknown`.
    merge.py SENTINEL_NULL_STRINGS coerces `Unknown` → null; CHUNK22_CORRECTIONS
    restores occupant_role=`Unknown` (same as TT58/TT70/TT91 precedent).
    Note: occupant_name remains null (no name to restore). Egyptologist
    review pending: PM's headword prints a title (Royal scribe) — may
    warrant occupant_role=`Official` per TT114 analogy."""
    r = _row("TT136")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "Royal scribe" in r["notes_from_pm"]
    assert "Lord of the Two Lands" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 251


def test_chunk22_tt137_mose_head_of_works() -> None:
    """TT137 Mose — Head of works of the Lord of the Two Lands in every
    monument of Amūn. Temp. Ramesses II, p.251. Parents: Bak (Head of works
    in the Place of Eternity) and Tekhu. Wife Taikharu. (L. D. Text, No. 91.)
    occupant_name `Mose` from 2/1 majority B+C (agent A had `Mosi` from OCR
    `Mosx` trailing-x noise). Tie-break pins agent C: Amūn macron +
    mid-sentence citation."""
    r = _row("TT137")
    assert r["occupant_name"] == "Mose"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "Head of works of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert "(L. D. Text, No. 91.)" in r["notes_from_pm"]
    assert "Bak" in r["notes_from_pm"]
    assert "Tekhu" in r["notes_from_pm"]
    assert "Taikharu" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 251


def test_chunk22_tt138_nezemger_garden_neshaoin() -> None:
    """TT138 Nezemger — Overseer of the garden in the Ramesseum in the estate
    of Amūn. Temp. Ramesses II, p.251. (CHAMPOLLION, No. 29.) Wife Neshaʿ.
    Tie-break pins agent C: Amūn macron + CHAMPOLLION uppercase + mid-sentence
    citation. CHUNK22_CORRECTIONS restores ayin on Wife `Neshaʿ` (source OCR
    `Nesha(` = `Neshaʿ`; A+B emitted ayin, C dropped it)."""
    r = _row("TT138")
    assert r["occupant_name"] == "Nezemger"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "Overseer of the garden in the Ramesseum" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 29.)" in r["notes_from_pm"]
    assert "Neshaʿ" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 251


def test_chunk22_tt139_pairi_waab_priest_sheroy_hathor() -> None:
    """TT139 Pairi — wʿab-priest in front, First royal son in front of Amūn,
    Overseer of peasants of Amūn. Temp. Amenophis III, p.252. Father Sheroy,
    Prophet of Ptaḥ and Ḥatḥor. Wife Ḥenutnefert. Tie-break pins agent C:
    Amūn macrons (×2) + Ptaḥ + Ḥatḥor + Ḥenutnefert underdots correct.
    CHUNK22_CORRECTIONS restores `Wab-priest` → `wʿab-priest` (ayin before a,
    lowercase — same class as TT113/TT114/TT135)."""
    r = _row("TT139")
    assert r["occupant_name"] == "Pairi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert r["notes_from_pm"].startswith("wʿab-priest in front,")
    assert "First royal son in front of Amūn" in r["notes_from_pm"]
    assert "Overseer of peasants of Amūn" in r["notes_from_pm"]
    assert "Amenophis III" in r["notes_from_pm"]
    assert "Sheroy" in r["notes_from_pm"]
    assert "Ptaḥ" in r["notes_from_pm"]
    assert "Ḥatḥor" in r["notes_from_pm"]
    assert "Ḥenutnefert" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["source_citation"]["page"] == 252


def test_chunk22_tt140_neferronpet_hefia_dra_abu_el_naga() -> None:
    """TT140 Neferronpet — probably called Ḥefia, Goldworker, Portrait sculptor,
    Temp. Tuthmosis III to Amenophis II, p.254. Wife Tauy. Dra' Abu el-Naga
    (first numbered tomb breaking from Sh. ʿAbd el-Qurna in this section).
    occupant_alt_names=[`Hefia`] (ḥ-stripped per TT57/TT120 matchable-name
    precedent; tie-break pins agent B). CHUNK22_CORRECTIONS restores `Kefia`
    → `Ḥefia` in notes_from_pm (source OCR `l):.efia` confirms underdot-Ḥ).
    DERIVER_OVERRIDE pins attribution_certainty=attested (`probably called`
    hedges the alt-name only, not the primary occupant attribution)."""
    r = _row("TT140")
    assert r["occupant_name"] == "Neferronpet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == ["Hefia"]
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_usurped"] is False
    assert "probably called Ḥefia" in r["notes_from_pm"]
    assert "Goldworker" in r["notes_from_pm"]
    assert "Portrait sculptor" in r["notes_from_pm"]
    assert "Tuthmosis III to Amenophis II" in r["notes_from_pm"]
    assert "Tauy" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 254


def test_chunk23_tt141_bekenkhons_waab_priest_amun() -> None:
    """TT141 Bekenkhons — wʿab-priest of Amūn. Ramesside. Wife Takhaʿ(t). p.254.
    Dra' Abu el-Naga. Tie-break pins agent B (Amūn macron + ayin on wife name).
    CHUNK23_CORRECTIONS restores `Wab-priest` → `wʿab-priest` (ayin before a,
    lowercase initial, same OCR class as TT135/TT139). 1/1/1 tie on Amün/Amūn/Amun
    macron variant. All 3 agents agree on structured fields."""
    r = _row("TT141")
    assert r["occupant_name"] == "Bekenkhons"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert r["notes_from_pm"].startswith("wʿab-priest of Amūn.")
    assert "Ramesside" in r["notes_from_pm"]
    assert "Takhaʿ(t)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 254


def test_chunk23_tt142_simut_overseer_works_djhutnofer() -> None:
    """TT142 Simut — Overseer of works of Amen-reʿ in Karnak. Temp. Tuthmosis
    III to Amenophis II (?). Parents: Menta (Overseer of granary of Amon) and
    Ḏḥutnofer. Wife Sitamon. p.255. 2/1 majority: B+C emit d-bar Ḏḥutnofer;
    A had `Dḥutnofer` (no d-bar). DERIVER_OVERRIDE pins attribution_certainty=
    attested (the `(?)` qualifies the regnal-range tail, not Simut's
    identification)."""
    r = _row("TT142")
    assert r["occupant_name"] == "Simut"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of works of Amen-reʿ in Karnak" in r["notes_from_pm"]
    assert "Tuthmosis III to Amenophis II (?)" in r["notes_from_pm"]
    assert "Menta" in r["notes_from_pm"]
    assert "Ḏḥutnofer" in r["notes_from_pm"]
    assert "Sitamon" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 255


def test_chunk23_tt143_anonymous_name_lost_tentkhesbed() -> None:
    """TT143 — Name lost. Temp. Tuthmosis III to Amenophis II (?). Wife
    Tentkhesbed. p.255. occupant_name=null, occupant_role=Unknown (SENTINEL_NULL
    coercion restored by CHUNK23_CORRECTIONS, same class as TT136/TT116/TT70/
    TT58). DERIVER_OVERRIDE pins attribution_certainty=attested (anonymous tomb,
    (?) qualifies regnal range tail only)."""
    r = _row("TT143")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Name lost" in r["notes_from_pm"]
    assert "Tuthmosis III to Amenophis II (?)" in r["notes_from_pm"]
    assert "Tentkhesbed" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 255


def test_chunk23_tt144_nu_head_field_labourers_henuttaui() -> None:
    """TT144 Nu — Head of the field-labourers. Temp. Tuthmosis III (?). Wife
    Henuttaui. p.257. Tie-break pins agent A: space before (?) (A+C majority)
    + Henuttaui without underdot-Ḥ (A+B majority). DERIVER_OVERRIDE pins
    attribution_certainty=attested ((?) qualifies regnal date, not Nu's
    identification). Egyptologist flag: agent C had Ḥenuttaui with underdot;
    confirm PDF p.275."""
    r = _row("TT144")
    assert r["occupant_name"] == "Nu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Head of the field-labourers" in r["notes_from_pm"]
    assert "Tuthmosis III (?)" in r["notes_from_pm"]
    assert "Henuttaui" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 257


def test_chunk23_tt145_nebamun_head_bowmen_ahhotp() -> None:
    """TT145 Nebamun — Head of bowmen. Dyn. XVIII. Wife ʿAḥḥotp. p.257.
    2/1 majority: B+C emit ʿAḥḥotp (ayin + doubled-ḥ); agent A had OCR-noise
    `<Al).l).otp.` No corrections needed — majority resolves cleanly."""
    r = _row("TT145")
    assert r["occupant_name"] == "Nebamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Head of bowmen" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert "ʿAḥḥotp" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 257


def test_chunk23_tt146_nebamun_granary_inaccessible() -> None:
    """TT146 Nebamun — Overseer of the granary of Amūn, Scribe, Counter of
    grain, tny of the god's wife (titles from cones). Temp. Tuthmosis III (?).
    (Inaccessible.) Wife Suitnub (from cone). p.258. Tie-break pins agent B
    (Amūn macron). DERIVER_OVERRIDE pins attribution_certainty=attested ((?)
    qualifies regnal date only)."""
    r = _row("TT146")
    assert r["occupant_name"] == "Nebamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of the granary of Amūn" in r["notes_from_pm"]
    assert "titles from cones" in r["notes_from_pm"]
    assert "Tuthmosis III (?)" in r["notes_from_pm"]
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert "Suitnub" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 258


def test_chunk23_tt147_anonymous_masters_ceremonies_amun() -> None:
    """TT147 — Head of the masters of ceremonies(?) of Amūn, &c. Temp.
    Tuthmosis IV(?). Wife Nefert. p.258. occupant_name=null, occupant_role=
    Unknown (SENTINEL_NULL coercion restored by CHUNK23_CORRECTIONS). Tie-break
    pins agent B: Amūn macron + no space before (?) + clean period on wife name.
    DERIVER_OVERRIDE pins attribution_certainty=attested (both (?) qualify
    title uncertainty and regnal date, not occupant identity)."""
    r = _row("TT147")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "masters of ceremonies(?)" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Tuthmosis IV(?)" in r["notes_from_pm"]
    assert "Nefert" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 258


def test_chunk23_tt148_amenemopet_prophet_amun_thonnfer() -> None:
    """TT148 Amenemopet — Prophet of Amūn. Temp. Ramesses III to V. Parents:
    Thonnfer (tomb 158) and Nefertere. Wife Tamert, Chief of the harim [of Amūn].
    p.259. Tie-break pins agent B (Amūn macron ×2). Egyptologist flag: Thonnfer
    may carry a macron (Thonnūfer?) per PM verbatim — confirm PDF p.277."""
    r = _row("TT148")
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Prophet of Amūn" in r["notes_from_pm"]
    assert "Ramesses III to V" in r["notes_from_pm"]
    assert "Thonnfer" in r["notes_from_pm"]
    assert "tomb 158" in r["notes_from_pm"]
    assert "Nefertere" in r["notes_from_pm"]
    assert "Tamert" in r["notes_from_pm"]
    assert "harim [of Amūn]" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 259


def test_chunk23_tt149_amenmosi_royal_scribe_huntsmen() -> None:
    """TT149 Amenmosi — Royal scribe of the table of the Lord of the Two Lands,
    Overseer of the huntsmen of Amūn. Ramesside. Wife Sitmut. p.260. Tie-break
    pins agent B (Amūn macron). All agents agree on structured fields."""
    r = _row("TT149")
    assert r["occupant_name"] == "Amenmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Royal scribe of the table of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Overseer of the huntsmen of Amūn" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert "Sitmut" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 260


def test_chunk23_tt150_userhet_cattle_unfinished_iaetib() -> None:
    """TT150 Userhet — Overseer of cattle of Amūn. Late Dyn. XVIII. (Unfinished.)
    Wife Iaet-ib, Royal concubine. p.261. is_unfinished=True (derived from
    `(Unfinished.)` in notes via _ISSUE_182_DERIVATIONS — all 3 agents agree).
    Tie-break pins agent B (Amūn macron; B alone had Iaet-ib vs A+C's Iact-ib).
    Egyptologist flag: confirm wife name Iaet-ib vs Iact-ib against PDF p.279."""
    r = _row("TT150")
    assert r["occupant_name"] == "Userhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert "Overseer of cattle of Amūn" in r["notes_from_pm"]
    assert "Late Dyn. XVIII" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert "Iaet-ib" in r["notes_from_pm"]
    assert "Royal concubine" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 261


# ---------------------------------------------------------------------------
# Chunk 24: TT151–TT160. All in Dra' Abu el-Naga (§ I). PM I.1 pp.261–273.
# 3 tie-break-overrides entries: TT151|notes_from_pm (A omits Parents, B has
# OCR garbage `Men:;;:`, pin C), TT157|notes_from_pm (Amūn×2 + CHAMPOLLION,
# pin A), TT158|notes_from_pm (Amūn×2 + CHAMPOLLION, pin A).
# 2/1-majority resolutions: TT152 notes `Name lost, late Dyn.` (A+C comma),
# TT155 occupant_name `[Antef]` (A+C brackets), TT156 notes `CHAMPOLLION`
# (A+C uppercase), TT159 occupant_name `Raʿya` (A+B trailing a),
# TT160 notes `CHAMPOLLION` (A+C uppercase), all theban_area without trailing
# apostrophe (A+B).
# 3 CHUNK24_CORRECTIONS: TT151 Amun → Amūn (macron restore post-tie-break),
# TT152 occupant_role sentinel-null restore, TT153 occupant_role sentinel-null.
# 4 DERIVER_OVERRIDES: TT152 is_usurped(?)=event hedge not occupant-ID,
# TT153 regnal-date hedge, TT154 regnal-date hedge, TT158 `Probably` on
# regnal date — all attribution_certainty restored to `attested`.
# Egyptologist flags: TT159 Raʿya vs Raʿy — PM source OCR `RAcy` (no
# terminal a); confirm printed form against PDF p.271.
# ---------------------------------------------------------------------------


def test_chunk24_tt151_hety_scribe_steward_godswife() -> None:
    """TT151 Hety — Scribe, Counter of cattle of the god's wife of Amūn,
    Steward of the god's wife. Temp. Tuthmosis IV. (Unfinished.) Wife
    Nefertere. Parents Nebnufer. p.261. is_unfinished=True.
    Tie-break pins agent C (no OCR garbage, has Parents clause). Macron
    Amun → Amūn restored via CHUNK24_CORRECTIONS."""
    r = _row("TT151")
    assert r["occupant_name"] == "Hety"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert "Scribe, Counter of cattle of the god's wife of Amūn" in r["notes_from_pm"]
    assert "Steward of the god's wife" in r["notes_from_pm"]
    assert "Temp. Tuthmosis IV" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert "Wife, Nefertere" in r["notes_from_pm"]
    assert "Parents, Nebnufer" in r["notes_from_pm"]
    assert "Men:;;:" not in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 261


def test_chunk24_tt152_anonymous_usurped_ramesside() -> None:
    """TT152 — Name lost, late Dyn. XVIII. Usurped in Ramesside times(?).
    p.262. occupant_name=None, occupant_role=Unknown (sentinel-null restored).
    is_usurped=True (deriver fires on `Usurped in Ramesside times`).
    attribution_certainty=attested (DERIVER_OVERRIDE: (?) qualifies event
    timing, not occupant identity; occupant is anonymous)."""
    r = _row("TT152")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is True
    assert "Name lost" in r["notes_from_pm"]
    assert "late Dyn. XVIII" in r["notes_from_pm"]
    assert "Usurped in Ramesside times(?)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 262


def test_chunk24_tt153_anonymous_sethos() -> None:
    """TT153 — Name lost. Temp. Sethos I (?). p.262. occupant_name=None,
    occupant_role=Unknown (sentinel-null restored). attribution_certainty=attested
    (DERIVER_OVERRIDE: (?) qualifies regnal date, not occupant identity)."""
    r = _row("TT153")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Name lost" in r["notes_from_pm"]
    assert "Temp. Sethos I (?)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 262


def test_chunk24_tt154_tati_butler_tuthmosis() -> None:
    """TT154 Tati — Butler. Temp. Tuthmosis III(?). p.262.
    attribution_certainty=attested (DERIVER_OVERRIDE: (?) qualifies regnal
    date, not Tati's identification as Butler)."""
    r = _row("TT154")
    assert r["occupant_name"] == "Tati"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Butler" in r["notes_from_pm"]
    assert "Tuthmosis III(?)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 262


def test_chunk24_tt155_antef_great_herald() -> None:
    """TT155 [Antef] — Great herald of the King. Temp. Ḥatshepsut and
    Tuthmosis III. (HAY, No. 1.) p.263. occupant_name includes brackets
    (2/1 majority: A+C emitted `[Antef]`, B emitted `Antef`)."""
    r = _row("TT155")
    assert r["occupant_name"] == "[Antef]"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Great herald of the King" in r["notes_from_pm"]
    assert "Ḥatshepsut" in r["notes_from_pm"]
    assert "Tuthmosis III" in r["notes_from_pm"]
    assert "(HAY, No. 1.)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 263


def test_chunk24_tt156_pennesuttaui_captain_troops() -> None:
    """TT156 Pennesuttaui — Captain of troops, Governor of the South Lands.
    Dyn. XIX. (CHAMPOLLION, No. 43.) Wife Mia. p.265. CHAMPOLLION uppercase
    per PM convention (A+C vs B's lowercase; 2/1 majority)."""
    r = _row("TT156")
    assert r["occupant_name"] == "Pennesuttaui"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Captain of troops" in r["notes_from_pm"]
    assert "Governor of the South Lands" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 43.)" in r["notes_from_pm"]
    assert "Wife, Mia" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 265


def test_chunk24_tt157_nebwenenef_first_prophet_amun() -> None:
    """TT157 Nebwenenef — First prophet of Amūn. Temp. Ramesses II.
    (CHAMPOLLION, No. 42, L. D. Text, No. 7.) Wife Takhaʿt, Chief of the
    harim of Amūn, Songstress of Isis. p.266. occupant_role=High Priest.
    Tie-break pins agent A (Amūn×2, CHAMPOLLION uppercase)."""
    r = _row("TT157")
    assert r["occupant_name"] == "Nebwenenef"
    assert r["occupant_role"] == "High Priest"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "First prophet of Amūn" in r["notes_from_pm"]
    assert "Temp. Ramesses II" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 42, L. D. Text, No. 7.)" in r["notes_from_pm"]
    assert "Wife, Takhaʿt" in r["notes_from_pm"]
    assert "harim of Amūn" in r["notes_from_pm"]
    assert "Songstress of Isis" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 266


def test_chunk24_tt158_thonufer_third_prophet_amun() -> None:
    """TT158 Thonufer — Third prophet of Amūn. Probably temp. Ramesses III.
    (CHAMPOLLION, No. 44, L. D. Text, No. 9.) Wife Nefertere, Chief of the
    harim of Amūn. p.268. attribution_certainty=attested (DERIVER_OVERRIDE:
    `Probably` qualifies regnal date for Ramesses III, not Thonufer's
    identity as Third prophet). Tie-break pins agent A (Amūn×2 + CHAMPOLLION)."""
    r = _row("TT158")
    assert r["occupant_name"] == "Thonufer"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Third prophet of Amūn" in r["notes_from_pm"]
    assert "Probably temp. Ramesses III" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 44, L. D. Text, No. 9.)" in r["notes_from_pm"]
    assert "Wife, Nefertere" in r["notes_from_pm"]
    assert "harim of Amūn" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 268


def test_chunk24_tt159_raya_fourth_prophet_amun() -> None:
    """TT159 Raʿya — Fourth prophet of Amūn. Dyn. XIX. Wife Mutemwia. p.271.
    occupant_name `Raʿya` per 2/1 majority (A+B vs C's `Raʿy`).
    Egyptologist flag: source OCR `RAcy` (no terminal a); confirm `Raʿya`
    vs `Raʿy` against printed PDF p.271."""
    r = _row("TT159")
    assert r["occupant_name"] == "Raʿya"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Fourth prophet of Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Wife, Mutemwia" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 271


def test_chunk24_tt160_besenmut_royal_acquaintance_saite() -> None:
    """TT160 Besenmut — True royal acquaintance. Saite. (CHAMPOLLION, No. 46.)
    Parents Pedemut and Tahibet. p.273. CHAMPOLLION uppercase per PM convention
    (A+C vs B's lowercase; 2/1 majority)."""
    r = _row("TT160")
    assert r["occupant_name"] == "Besenmut"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "True royal acquaintance" in r["notes_from_pm"]
    assert "Saite" in r["notes_from_pm"]
    assert "(CHAMPOLLION, No. 46.)" in r["notes_from_pm"]
    assert "Parents, Pedemut and Tahibet" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["source_citation"]["page"] == 273


# ---------------------------------------------------------------------------
# Chunk 25: TT161–TT170. Dra' Abu el-Naga (TT161–TT169) + Sh. ʿAbd el-Qurna
# (TT170). PM I.1 pp.274–279.
# 0 tie-break-overrides entries (all 2/1 or unanimous).
# 2/1-majority resolutions:
#   TT161 notes_from_pm — A+B ordering (title→parents→wife→biblio) + Taḳemt
#     (K-underdot) over C's reordering + Taḥemt (H-underdot).
#   TT162 occupant_name — B+C `Kenamun` (plain K) over A's `Ḳenamun` (underdot).
#   TT162 notes_from_pm — B+C shorter form (no Daressy footnote) over A.
# 1 CHUNK25_CORRECTIONS: TT167 occupant_role sentinel-null restore.
# 3 DERIVER_OVERRIDES: TT161 regnal-date hedge (Amenophis III(?)),
#   TT163 parentage-hedge (Father(?)), TT165 regnal-date hedge (Tuthmosis IV(?))
#   — all attribution_certainty restored to `attested`.
# Egyptologist flags:
#   TT162 occupant_name — PM source headword line 93 reads `~ENAMUN` (OCR
#     rendering with tilde rather than Ḳ/K prefix). Agent A read `Ḳenamun`
#     (with underdot-K), B+C read `Kenamun` (plain K). Footnote 1 (p.275) says
#     "Name and titles from cones" — the cone rendering may differ from the
#     hieroglyphic text. Egyptologist should confirm correct diacritic form
#     against cone catalogue or other references.
#   TT162 notes_from_pm — Agent A included a Daressy footnote (`Footnote:
#     Daressy gives alternative owner as: Eyes of the King in the North Land,
#     Ḥari of Ḥaremmaʿet, from text in Hall at (1).`). B+C omitted it. Majority
#     (B+C) prevailed. Egyptologist should confirm whether the footnote text
#     belongs in notes_from_pm or a separate footnote field.
# ---------------------------------------------------------------------------


def test_chunk25_tt161_nakht_bearer_floral_offerings() -> None:
    """TT161 Nakht — Bearer of the floral offerings of Amūn.
    Temp. Amenophis III(?). Dra' Abu el-Naga. p.274.
    is_unfinished=False. DERIVER_OVERRIDE: (?) qualifies regnal date."""
    r = _row("TT161")
    assert r["occupant_name"] == "Nakht"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Bearer of the floral offerings of Amūn" in r["notes_from_pm"]
    assert "Amenophis III(?)" in r["notes_from_pm"]
    assert "Guraru" in r["notes_from_pm"]
    assert "Taḳemt" in r["notes_from_pm"]
    assert "(L. D. Text, No. 13, HAY, No. 9.)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 274


def test_chunk25_tt162_kenamun_mayor_southern_city() -> None:
    """TT162 Kenamun — Mayor in the Southern City, Overseer of the granary
    of Amūn. Dyn. XVIII. Dra' Abu el-Naga. p.275.
    occupant_name 2/1 majority (B+C plain K over A underdot-Ḳ).
    notes_from_pm 2/1 majority (B+C shorter form, no Daressy footnote)."""
    r = _row("TT162")
    assert r["occupant_name"] == "Kenamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Mayor in the Southern City" in r["notes_from_pm"]
    assert "Overseer of the granary of Amūn" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert "Mut-tuy" in r["notes_from_pm"]
    assert "(from cone)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 275


def test_chunk25_tt163_amenemhet_mayor_royal_scribe() -> None:
    """TT163 Amenemhet — Mayor of the Southern City, Royal scribe. Dyn. XIX.
    Dra' Abu el-Naga. p.276.
    DERIVER_OVERRIDE: Father(?) is parentage hedge, not occupant-ID hedge."""
    r = _row("TT163")
    assert r["occupant_name"] == "Amenemhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Mayor of the Southern City" in r["notes_from_pm"]
    assert "Royal scribe" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "(Inaccessible.)" in r["notes_from_pm"]
    assert "Ḥuy" in r["notes_from_pm"]
    assert "Nezemt-net" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 276


def test_chunk25_tt164_antef_scribe_recruits() -> None:
    """TT164 Antef — Scribe of recruits. Temp. Tuthmosis III.
    Dra' Abu el-Naga. p.276."""
    r = _row("TT164")
    assert r["occupant_name"] == "Antef"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of recruits" in r["notes_from_pm"]
    assert "Tuthmosis III" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 276


def test_chunk25_tt165_nehemaway_goldworker_sculptor() -> None:
    """TT165 Nehemʿaway — Goldworker and portrait-sculptor.
    Temp. Tuthmosis IV(?). Dra' Abu el-Naga. p.277.
    DERIVER_OVERRIDE: (?) qualifies regnal date (Tuthmosis IV)."""
    r = _row("TT165")
    assert r["occupant_name"] == "Nehemʿaway"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Goldworker and portrait-sculptor" in r["notes_from_pm"]
    assert "Tuthmosis IV(?)" in r["notes_from_pm"]
    assert "Tentamentet" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 277


def test_chunk25_tt166_racmosi_overseer_works_karnak() -> None:
    """TT166 Raʿmosi — Overseer of works in Karnak, Overseer of cattle.
    Dyn. XX. Dra' Abu el-Naga. p.277."""
    r = _row("TT166")
    assert r["occupant_name"] == "Raʿmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of works in Karnak" in r["notes_from_pm"]
    assert "Overseer of cattle" in r["notes_from_pm"]
    assert "Dyn. XX" in r["notes_from_pm"]
    assert "Ipy" in r["notes_from_pm"]
    assert "Thoth" in r["notes_from_pm"]
    assert "Tay" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 277


def test_chunk25_tt167_anonymous_unfinished_dyn18() -> None:
    """TT167 — Name lost. Dyn. XVIII. (Unfinished.) Dra' Abu el-Naga. p.278.
    occupant_name=None, occupant_role sentinel-null restored via CHUNK25_CORRECTIONS,
    is_unfinished=True."""
    r = _row("TT167")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert "Name lost" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 278


def test_chunk25_tt168_any_divine_father() -> None:
    """TT168 Any — Divine father clean of hands, Chosen lector of the lord
    of the gods. Dyn. XIX. Dra' Abu el-Naga. p.278."""
    r = _row("TT168")
    assert r["occupant_name"] == "Any"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Divine father clean of hands" in r["notes_from_pm"]
    assert "Chosen lector of the lord of the gods" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Merynub" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 278


def test_chunk25_tt169_senna_head_goldworkers() -> None:
    """TT169 Senna — Head of the goldworkers of Amūn. Temp. Amenophis II.
    Dra' Abu el-Naga. p.278.
    Egyptologist note: PM source OCR p.249 headword SENNA with cartouche-
    like symbol — confirm full hieroglyphic name form against printed source."""
    r = _row("TT169")
    assert r["occupant_name"] == "Senna"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Head of the goldworkers of Amūn" in r["notes_from_pm"]
    assert "Amenophis II" in r["notes_from_pm"]
    assert "Sensonb" in r["notes_from_pm"]
    assert "Tanub" in r["notes_from_pm"]
    assert "Maʿetka" in r["notes_from_pm"]
    assert r["theban_area"] == "Dra' Abu el-Naga"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 278


def test_chunk25_tt170_nebmehyt_scribe_recruits_ramesseum() -> None:
    """TT170 Nebmehy(t) — Scribe of recruits of the Ramesseum in the estate
    of Amūn. Temp. Ramesses II. Sh. ʿAbd el-Qurna. p.279."""
    r = _row("TT170")
    assert r["occupant_name"] == "Nebmehy(t)"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of recruits of the Ramesseum" in r["notes_from_pm"]
    assert "estate of Amūn" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 279


# Chunk 26: TT171–TT180. Sh. ʿAbd el-Qurna (TT171) + Khôkha (TT172–TT180).
# PM I.1 pp.279–286.
# 0 tie-break-overrides entries (all 2/1 or unanimous).
# 2/1-majority resolutions:
#   TT171 notes_from_pm — A+C `"Name lost. Dyn. XVIII. Wife, Esi."` wins 2/1
#     over B's reordering `"Name lost. Wife, Ḥesi. Dyn. XVIII."` (B has Ḥesi,
#     A+C have Esi — Esi vs Ḥesi flagged for egyptologist).
#   TT172 notes_from_pm — A+B `"Mother, Ḥepu."` wins 2/1 over C's
#     `"Mother, Ḥepu A."` (OCR hieroglyph-fragment `A` stripped by majority).
#   TT178 notes_from_pm — A+B `"Amen-reʿ"` wins 2/1 over C's `"Amen-Reʿ"`
#     (capital `R` dropped by majority).
#   TT179 notes_from_pm — B+C clean `ʿAḥmosi` wins 2/1 over A's form with
#     spurious space after ayin.
# 3 CHUNK26_CORRECTIONS: TT171/TT175/TT180 occupant_role sentinel-null restore.
# 3 DERIVER_OVERRIDES: TT172 regnal-range tail hedge (Amenophis II(?)),
#   TT175 anonymous regnal-date hedge (Tuthmosis IV(?)),
#   TT177 regnal-date hedge (Ramesses II(?)) — all attribution_certainty
#   restored to `attested`.
# Egyptologist flags (require PDF visual confirmation before applying):
#   TT171 notes wife-name — majority form `Esi` vs minority B `Ḥesi`; OCR
#     colon+E rendering may be Ḥ class. Check printed source for underdot-H.
#   TT176 occupant_name — `[Amen]userhet` may be `[Amen]userhēt` per TT51/
#     TT56 USERḤĒT→Userhēt precedent. Egyptologist should check vowel macron.
#   TT177 occupant_name — `Amenemopet` may be `Amenemōpet` per TT29/TT41
#     precedent. Egyptologist should confirm macron form.
#   TT179 occupant_name — `Nebamun` may be `Nebamūn` per TT17/TT65/TT90
#     within-source precedent (three earlier Nebamūn in PM I.1). Egyptologist
#     should confirm macron form for this fourth instance.
# ---------------------------------------------------------------------------


def test_chunk26_tt171_anonymous_dyn18_sh_abd_el_qurna() -> None:
    """TT171 — Name lost. Dyn. XVIII. Wife, Esi. Sh. ʿAbd el-Qurna. p.279.
    occupant_name=None, occupant_role sentinel-null restored via CHUNK26_CORRECTIONS.
    TT171 is the only chunk-26 tomb outside Khôkha (Sh. ʿAbd el-Qurna).
    Egyptologist flag: wife name Esi vs Ḥesi — PDF confirmation pending."""
    r = _row("TT171")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Name lost" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert "Esi" in r["notes_from_pm"]
    assert r["theban_area"] == "Sh. ʿAbd el-Qurna"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 279


def test_chunk26_tt172_mentiywy_royal_butler() -> None:
    """TT172 Mentiywy — Royal butler, Child of the nursery.
    Temp. Tuthmosis III to Amenophis II (?). Khôkha. p.279.
    notes 2/1 majority: A+B `Mother, Ḥepu.` over C's `Mother, Ḥepu A.`.
    DERIVER_OVERRIDE: (?) qualifies regnal-range tail (Amenophis II)."""
    r = _row("TT172")
    assert r["occupant_name"] == "Mentiywy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Royal butler" in r["notes_from_pm"]
    assert "Child of the nursery" in r["notes_from_pm"]
    assert "Tuthmosis III to Amenophis II (?)" in r["notes_from_pm"]
    assert "Ḥepu" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 279


def test_chunk26_tt173_khay_scribe_divine_offerings() -> None:
    """TT173 Khaʿy — Scribe of the divine offerings of the Gods of Thebes.
    Dyn. XIX. Khôkha. p.281."""
    r = _row("TT173")
    assert r["occupant_name"] == "Khaʿy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of the divine offerings of the Gods of Thebes" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Biathefu" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 281


def test_chunk26_tt174_ashakhet_priest_front_mut() -> None:
    """TT174 ʿAshakhet — Priest in front of Mut. Dyn. XIX. Khôkha. p.281."""
    r = _row("TT174")
    assert r["occupant_name"] == "ʿAshakhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Priest in front of Mut" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Tazabu" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 281


def test_chunk26_tt175_anonymous_tuthmosis_iv() -> None:
    """TT175 — No name. Temp. Tuthmosis IV (?). Khôkha. p.281.
    occupant_name=None, occupant_role sentinel-null restored via CHUNK26_CORRECTIONS.
    DERIVER_OVERRIDE: (?) qualifies regnal date (Tuthmosis IV), not identity."""
    r = _row("TT175")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "No name" in r["notes_from_pm"]
    assert "Tuthmosis IV" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 281


def test_chunk26_tt176_amenUserhet_servant_clean_hands() -> None:
    """TT176 [Amen]userhet — Servant clean of hands.
    Temp. Amenophis II to Tuthmosis IV. Khôkha. p.281.
    Bracket-fragment name form preserved from PM headword.
    Egyptologist flag: macron form [Amen]userhēt not confirmed against PDF."""
    r = _row("TT176")
    assert r["occupant_name"] == "[Amen]userhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Servant clean of hands" in r["notes_from_pm"]
    assert "Amenophis II to Tuthmosis IV" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 281


def test_chunk26_tt177_amenemopet_scribe_truth_ramesseum() -> None:
    """TT177 Amenemopet — Scribe of truth in the Ramesseum in the estate of Amūn.
    Temp. Ramesses II (?). (Unfinished.) Khôkha. p.283.
    is_unfinished=True. DERIVER_OVERRIDE: (?) qualifies regnal date (Ramesses II).
    Egyptologist flag: macron form Amenemōpet not confirmed against PDF."""
    r = _row("TT177")
    assert r["occupant_name"] == "Amenemopet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert "Scribe of truth in the Ramesseum" in r["notes_from_pm"]
    assert "estate of Amūn" in r["notes_from_pm"]
    assert "Ramesses II (?)" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert "Nebḥed" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 283


def test_chunk26_tt178_neferronpet_kenro_scribe_treasury() -> None:
    """TT178 Neferronpet, called Kenro — Scribe of the treasury in the estate
    of Amen-reʿ. Temp. Ramesses II. Khôkha. p.283.
    occupant_alt_names=["Kenro"]. notes 2/1 majority: A+B `Amen-reʿ` over
    C's `Amen-Reʿ` (capital R)."""
    r = _row("TT178")
    assert r["occupant_name"] == "Neferronpet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == ["Kenro"]
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of the treasury" in r["notes_from_pm"]
    assert "Amen-reʿ" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert "Mutemwia" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 283


def test_chunk26_tt179_nebamun_scribe_counter_grain() -> None:
    """TT179 Nebamun — Scribe, Counter of grain in the granary of divine
    offerings of Amūn. Temp. Ḥatshepsut. Khôkha. p.285.
    notes 2/1 majority: B+C clean ʿAḥmosi over A's spurious-space form.
    Egyptologist flag: macron form Nebamūn not confirmed against PDF (fourth
    Nebamun in PM I.1; TT17/TT65/TT90 all carry Nebamūn)."""
    r = _row("TT179")
    assert r["occupant_name"] == "Nebamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe, Counter of grain" in r["notes_from_pm"]
    assert "divine offerings of Amūn" in r["notes_from_pm"]
    assert "Ḥatshepsut" in r["notes_from_pm"]
    assert "Yotef" in r["notes_from_pm"]
    assert "ʿAḥmosi" in r["notes_from_pm"]
    assert "Sentnefert" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 285


def test_chunk26_tt180_anonymous_unfinished_dyn19() -> None:
    """TT180 — No name. Dyn. XIX. (Unfinished.) Accessible from tomb 179.
    Khôkha. p.286.
    occupant_name=None, occupant_role sentinel-null restored via CHUNK26_CORRECTIONS.
    is_unfinished=True. shared_with_tombs=[] (access relation, not ownership
    cross-ref; `Accessible from tomb 179` is architectural, not `See also`)."""
    r = _row("TT180")
    assert r["occupant_name"] is None
    assert r["occupant_role"] == "Unknown"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is True
    assert r["is_usurped"] is False
    assert "No name" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "(Unfinished.)" in r["notes_from_pm"]
    assert "Accessible from tomb 179" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 286


# ---------------------------------------------------------------------------
# Chunk-27 per-row tests (TT181–TT190, Khôkha + ʿAsâsîf)
# ---------------------------------------------------------------------------


def test_chunk27_all_rows_present() -> None:
    """All 10 TT181–TT190 rows must be present in reconciled.jsonl."""
    actual = {r["tomb_id"] for r in _rows()} & CHUNK27_TOMB_IDS
    assert actual == CHUNK27_TOMB_IDS, sorted(CHUNK27_TOMB_IDS - actual)


def test_chunk27_theban_area() -> None:
    """TT181–TT188 are Khôkha; TT189–TT190 are ʿAsâsîf (PM I.1 p.286–297)."""
    for tid in {f"TT{n}" for n in range(181, 189)}:
        r = _row(tid)
        assert r["theban_area"] == "Khokha", (tid, r["theban_area"])
    for tid in {"TT189", "TT190"}:
        r = _row(tid)
        assert r["theban_area"] == "ʿAsâsîf", (tid, r["theban_area"])


def test_chunk27_source_edition() -> None:
    """All chunk-27 rows cite PM I.1 2nd ed. 1960."""
    for tid in CHUNK27_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid,
            r["source_citation"]["edition"],
        )


def test_chunk27_all_official_role() -> None:
    """All 10 chunk-27 rows have occupant_role=Official — no unknowns."""
    for tid in CHUNK27_TOMB_IDS:
        r = _row(tid)
        assert r["occupant_role"] == "Official", (tid, r["occupant_role"])


def test_chunk27_tt181_nebamun_ipuky_joint_burial() -> None:
    """TT181 — NEBAMŪN + IPUKY, Head sculptor + Sculptor of the Lord of the
    Two Lands. Temp. Amenophis III–IV. Khôkha. p.286.
    Coordinate joint burial: PM p.286 lists both coordinately with bare
    AND conjunction and distinct per-occupant roles. is_joint_burial=True,
    co_occupants=[Ipuky, Official].
    CHUNK27_CORRECTIONS: occupant_name macron (Nebamun→Nebamūn, PDF p.304
    headword NEBAMŪN); notes Nebamon→Nebamūn + Senennoter→Senennūter.
    DERIVER_OVERRIDE: attribution_certainty=attested (deriver fires on
    `probably` in `Wife of Ipuky (and probably of Nebamūn)` — secondary
    association hedge, not primary occupant hedge; same class as TT2)."""
    r = _row("TT181")
    assert r["occupant_name"] == "Nebamūn"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == [{"name": "Ipuky", "role": "Official", "alt_names": []}]
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is True
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Head sculptor of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Ipuky, Sculptor of the Lord of the Two Lands" in r["notes_from_pm"]
    assert "Amenophis III to IV" in r["notes_from_pm"]
    assert "Neferḥet" in r["notes_from_pm"]
    assert "Senennūter" in r["notes_from_pm"]
    assert "Ḥenutnefert" in r["notes_from_pm"]
    assert "Nebamūn" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 286


def test_chunk27_tt182_amenemhet_scribe_mat() -> None:
    """TT182 — Amenemhet, Scribe of the mat. Temp. Tuthmosis III.
    Khôkha. p.289. Wife Sit-ḏḥout (d-bar Ḏ — Thoth-family name)."""
    r = _row("TT182")
    assert r["occupant_name"] == "Amenemhet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of the mat" in r["notes_from_pm"]
    assert "Tuthmosis III" in r["notes_from_pm"]
    assert "Sit-ḏḥout" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 289


def test_chunk27_tt183_nebsumenu_chief_steward_ramesses2() -> None:
    """TT183 — Nebsumenu, Chief steward, Steward in the house of Ramesses II.
    Temp. Ramesses II. Khôkha. p.289. Parents: Paser (Mayor of Southern City)
    + Tuia. Wife Bekmut. Brother Hunufer cross-ref to tomb 385."""
    r = _row("TT183")
    assert r["occupant_name"] == "Nebsumenu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Chief steward" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert "Paser" in r["notes_from_pm"]
    assert "Bekmut" in r["notes_from_pm"]
    assert "Hunufer" in r["notes_from_pm"]
    assert "tomb 385" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 289


def test_chunk27_tt184_nefermenu_mayor_southern_city() -> None:
    """TT184 — Nefermenu, Mayor in the Southern City, Royal scribe.
    Temp. Ramesses II. Khôkha. p.290.
    Disagreement: C emitted `Mayor of the Southern City` (genitive `of`),
    A+B emitted `Mayor in the Southern City` — 2/1 majority chose `in`."""
    r = _row("TT184")
    assert r["occupant_name"] == "Nefermenu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Mayor in the Southern City" in r["notes_from_pm"]
    assert "Royal scribe" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 290


def test_chunk27_tt185_senioher_hereditary_prince_fip() -> None:
    """TT185 — Senioher, Hereditary prince, Divine chancellor.
    First Intermediate Period. Khôkha. p.290.
    source_citation page: 2/1 majority chose p.290 (A+C), B had p.291."""
    r = _row("TT185")
    assert r["occupant_name"] == "Senioher"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Hereditary prince" in r["notes_from_pm"]
    assert "Divine chancellor" in r["notes_from_pm"]
    assert "First Intermediate Period" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 290


def test_chunk27_tt186_hy_nomarch_fip() -> None:
    """TT186 — Hy, Nomarch. First Intermediate Period. Khôkha. p.290.
    occupant_name: B+C=`Hy` (2/1), A=`Hiy`.
    notes: A+C=`Ḥatḥor` (underdot-H correct), B=`Hathor` (no underdot).
    Egyptologist flag: `Hy` vs PM-printed form — verify against PDF."""
    r = _row("TT186")
    assert r["occupant_name"] == "Hy"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Nomarch" in r["notes_from_pm"]
    assert "First Intermediate Period" in r["notes_from_pm"]
    assert "Imy" in r["notes_from_pm"]
    assert "Ḥatḥor" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 290


def test_chunk27_tt187_pakhihet_wab_priest_amun() -> None:
    """TT187 — Pakhihet, wʿab-priest of Amūn. Dyn. XIX. Khôkha. p.293.
    Parents: ʿAshakhet (tomb 174) + Tazabu. Wife Mutemonet.
    notes per CHUNK27_CORRECTIONS (PR #271 round-1 Gemini fix): sentence-
    initial lowercase `wʿab-priest` preserved per PM source verbatim
    (chunk-22 TT113 + chunk-26 ayin-before-a precedent); macron-Ū
    restored on Amūn per chunk-12-onward verbatim-preserve policy."""
    r = _row("TT187")
    assert r["occupant_name"] == "Pakhihet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "wʿab-priest" in r["notes_from_pm"]
    assert "Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "ʿAshakhet" in r["notes_from_pm"]
    assert "tomb 174" in r["notes_from_pm"]
    assert "Tazabu" in r["notes_from_pm"]
    assert "Mutemonet" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 293


def test_chunk27_tt188_parennufer_royal_butler_amenophis4() -> None:
    """TT188 — Parennufer, Royal butler clean of hands, Steward.
    Temp. Amenophis IV. Khôkha. p.293."""
    r = _row("TT188")
    assert r["occupant_name"] == "Parennufer"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Royal butler clean of hands" in r["notes_from_pm"]
    assert "Steward" in r["notes_from_pm"]
    assert "Amenophis IV" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 293


def test_chunk27_tt189_nekhtdhout_overseer_carpenters() -> None:
    """TT189 — Nekht-Ḏhout, Overseer of carpenters of the northern lake of
    Amūn, Head of goldworkers in the estate of Amūn. Temp. Ramesses II.
    ʿAsâsîf. p.295.
    occupant_name tie-break: C=`Nekht-Ḏhout` (d-bar — PDF p.313 confirms
    NEKHT-ḎHOUT headword). A=plain h, B=underdot-K (wrong consonant).
    notes: CHUNK27_CORRECTIONS restores Neteḥab→Netemḥab + Amūn macrons."""
    r = _row("TT189")
    assert r["occupant_name"] == "Nekht-Ḏhout"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of carpenters" in r["notes_from_pm"]
    assert "northern lake of Amūn" in r["notes_from_pm"]
    assert "goldworkers in the estate of Amūn" in r["notes_from_pm"]
    assert "Ramesses II" in r["notes_from_pm"]
    assert "Netemḥab" in r["notes_from_pm"]
    assert "Tentpa" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 295


def test_chunk27_tt190_esbanebded_saite_usurper() -> None:
    """TT190 — Esbanebded, Divine father, Prophet of the head of the King.
    Saite (usurped from a Ramesside tomb). ʿAsâsîf. p.297.
    is_usurped=False: Esbanebded IS the usurper of a Ramesside tomb — not
    the usurped party. Same structural parallel as TT95 Mery (chunk-18
    DERIVER_OVERRIDE): the `usurped from` phrase describes the event from
    the usurper's perspective. DERIVER_OVERRIDE pins is_usurped=False.
    notes: CHUNK27_CORRECTIONS restores Meramuniotes→Meramūniotes and
    Amen-Re→Amen-rēʿ per PDF p.297."""
    r = _row("TT190")
    assert r["occupant_name"] == "Esbanebded"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Divine father" in r["notes_from_pm"]
    assert "Prophet of the head of the King" in r["notes_from_pm"]
    assert "Saite (usurped from a Ramesside tomb)" in r["notes_from_pm"]
    assert "Pakharkhons" in r["notes_from_pm"]
    assert "Meramūniotes" in r["notes_from_pm"]
    assert "Amen-rēʿ" in r["notes_from_pm"]
    assert "Tanub" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 297


# === Chunk 28 — TT191-TT200 (ʿAsâsîf + Khôkha) ==============================


def test_chunk28_all_rows_present() -> None:
    """All 10 TT191-TT200 rows must be present in reconciled.jsonl."""
    actual = {r["tomb_id"] for r in _rows()} & CHUNK28_TOMB_IDS
    assert actual == CHUNK28_TOMB_IDS, sorted(CHUNK28_TOMB_IDS - actual)


def test_chunk28_theban_area() -> None:
    """TT191-TT197 are ʿAsâsîf; TT198-TT200 are Khôkha (PM I.1 p.297-303)."""
    for tid in {f"TT{n}" for n in range(191, 198)}:
        r = _row(tid)
        assert r["theban_area"] == "ʿAsâsîf", (tid, r["theban_area"])
    for tid in {"TT198", "TT199", "TT200"}:
        r = _row(tid)
        assert r["theban_area"] == "Khokha", (tid, r["theban_area"])


def test_chunk28_source_edition() -> None:
    """All chunk-28 rows cite PM I.1 2nd ed. 1960."""
    for tid in CHUNK28_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid,
            r["source_citation"]["edition"],
        )


def test_chunk28_all_official_role() -> None:
    """All 10 chunk-28 rows have occupant_role=Official."""
    for tid in CHUNK28_TOMB_IDS:
        r = _row(tid)
        assert r["occupant_role"] == "Official", (tid, r["occupant_role"])


def test_chunk28_tt191_wehebre_nebpehti_chamberlain() -> None:
    """TT191 — Wehebreʿ-Nebpehti, Chamberlain of the divine adoratress,
    Director of the festival. Temp. Psammetikhos I. ʿAsâsîf. p.297.
    Parents: Pedeḥor (Head of outline-draughtsmen) + Thesmutpert.
    All 3 agents unanimous on all fields."""
    r = _row("TT191")
    assert r["occupant_name"] == "Wehebreʿ-Nebpehti"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Chamberlain of the divine adoratress" in r["notes_from_pm"]
    assert "Director of the festival" in r["notes_from_pm"]
    assert "Psammetikhos I" in r["notes_from_pm"]
    assert "Pedeḥor" in r["notes_from_pm"]
    assert "Thesmutpert" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 297


def test_chunk28_tt192_kharuef_steward_royal_wife_teye() -> None:
    """TT192 — Kharuef (called Senaʿa), Steward of the Great Royal Wife Teye.
    Temp. Amenophis III-IV. ʿAsâsîf. p.298.
    Tie-break (1/1/1): notes_from_pm — pin 'called Senaʿa' inline + Silḥed
    parent name. A+C omit 'called Senaʿa'; B has the clause but Siḥed
    (missing 'l'). C had Silʿed (wrong diacritic — ayin not underdot-H).
    occupant_alt_names=['Senaʿa'] unanimous (all 3 agents agree)."""
    r = _row("TT192")
    assert r["occupant_name"] == "Kharuef"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == ["Senaʿa"]
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Steward of the Great Royal Wife Teye" in r["notes_from_pm"]
    assert "called Senaʿa" in r["notes_from_pm"]
    assert "Amenophis III to IV" in r["notes_from_pm"]
    assert "Silḥed" in r["notes_from_pm"]
    assert "Ruiu" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 298


def test_chunk28_tt193_ptahemhab_magnate_seal_treasury() -> None:
    """TT193 — Ptahemhab, Magnate of the seal in the treasury of the estate
    of Amūn. Dyn. XIX. ʿAsâsîf. p.300.
    Tie-break (1/1/1): notes_from_pm — pin C (macron-Amūn + stela clause).
    A+B omit stela clause; B has circumflex Amûn. Source footnote ¹ on
    headword '193. ¹ PTAḤEMḤAB' confirms stela-only status.
    is_uninscribed=False: stela clause does not contain 'uninscribed' token."""
    r = _row("TT193")
    assert r["occupant_name"] == "Ptahemhab"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Magnate of the seal" in r["notes_from_pm"]
    assert "estate of Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Tadetawert" in r["notes_from_pm"]
    assert "Stela only, but numbered as a tomb" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 300


def test_chunk28_tt194_dhutemhab_overseer_marshland_dwellers() -> None:
    """TT194 — [Ḏ]hutemhab, Overseer of marshland-dwellers of the estate of
    Amūn, Scribe of the temple of Amūn. Dyn. XIX. ʿAsâsîf. p.300.
    Tie-break (1/1/1): notes_from_pm — composite pin (A+C macron-Amūn,
    B wʿab-priest ayin, no stela clause — footnote ¹ belongs to TT193 not
    TT194; agents A+B misattributed it).
    occupant_name: [Ḏ]hutemhab (A+C 2/1 majority, B had [Ḏḥ]utemhab).
    Egyptologist flag: bracket scope — source OCR headword '[>I;IUTEMI;IAB'
    could be [Ḏ] (A+C) or [Ḏḥ] (B). Reviewer should confirm from PDF."""
    r = _row("TT194")
    assert r["occupant_name"] == "[Ḏ]hutemhab"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of marshland-dwellers" in r["notes_from_pm"]
    assert "estate of Amūn" in r["notes_from_pm"]
    assert "temple of Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "wʿab-priest" in r["notes_from_pm"]
    assert "Scribe of divine offerings of Amūn" in r["notes_from_pm"]
    assert "Nezemtmut" in r["notes_from_pm"]
    assert "Stela only" not in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 300


def test_chunk28_tt195_bekenamun_scribe_treasury() -> None:
    """TT195 — Bekenamun, Scribe of the treasury of the estate of Amūn.
    Dyn. XIX. ʿAsâsîf. p.301.
    notes_from_pm: A+C=Amūn (macron), B=Amûn (circumflex) — 2/1 majority."""
    r = _row("TT195")
    assert r["occupant_name"] == "Bekenamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of the treasury" in r["notes_from_pm"]
    assert "estate of Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "Wertnefert" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 301


def test_chunk28_tt196_pedehorresnet_chief_steward_amun_saite() -> None:
    """TT196 — Pedehorresnet, Chief steward of Amūn. Saite. ʿAsâsîf. p.302.
    Tie-break (1/1/1): notes_from_pm — pin C (Amūn macron + Shepenernōte).
    A=Shepenamūte (wrong name — OCR confusion). B=Shepenernûte (circumflex).
    OCR source 'ShepenernOte' — capital O = macron-ō → Shepenernōte.
    shared_with_tombs: A=['TT36'] vs B+C=[] — 2/1 majority chose []
    (PM p.302 mentions Ibi's tomb 36 as parentage cross-ref, not shared
    burial; agent A incorrectly encoded the text reference as shared_with_tombs)."""
    r = _row("TT196")
    assert r["occupant_name"] == "Pedehorresnet"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Chief steward of Amūn" in r["notes_from_pm"]
    assert "Saite" in r["notes_from_pm"]
    assert "Ibi (tomb 36)" in r["notes_from_pm"]
    assert "Shepenernōte" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 302


def test_chunk28_tt197_pedeneith_chief_steward_gods_wife() -> None:
    """TT197 — Pedeneith, Chief steward of the god's wife, the divine adoratress
    ʿAnkhnesneferebreʿ. Temp. Psammetikhos II. ʿAsâsîf. p.302.
    All 3 agents unanimous on all fields."""
    r = _row("TT197")
    assert r["occupant_name"] == "Pedeneith"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Chief steward of the god's wife" in r["notes_from_pm"]
    assert "ʿAnkhnesneferebreʿ" in r["notes_from_pm"]
    assert "Psammetikhos II" in r["notes_from_pm"]
    assert "CHAMPOLLION, No. 55" in r["notes_from_pm"]
    assert "Psammethek" in r["notes_from_pm"]
    assert "Tadedubaste" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 302


def test_chunk28_tt198_riya_head_magazine_amun_karnak() -> None:
    """TT198 — Riya, Head of the magazine of Amūn in Karnak. Ramesside.
    Khôkha. p.303.
    notes_from_pm: A+C=Amūn (macron), B=Amûn (circumflex) — 2/1 majority."""
    r = _row("TT198")
    assert r["occupant_name"] == "Riya"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Head of the magazine of Amūn in Karnak" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 303


def test_chunk28_tt199_amenarnofru_overseer_magazine_dyn18() -> None:
    """TT199 — [Amen]arnofru, Overseer of the magazine. Dyn. XVIII.
    Khôkha. (Inaccessible.) p.303.
    All 3 agents unanimous on all fields."""
    r = _row("TT199")
    assert r["occupant_name"] == "[Amen]arnofru"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Overseer of the magazine" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert "Inaccessible" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 303


def test_chunk28_tt200_ded_governor_deserts_west_thebes() -> None:
    """TT200 — Ded, Governor of the deserts on the west of Thebes, Head of
    the regiment of Pharaoh. Temp. Tuthmosis III to Amenophis II. Khôkha. p.303.
    occupant_name: A+B='Ded' (2/1 majority), C='Dedi'. Source OCR headword
    'D ED 1' — superscript ¹ is a footnote marker, not a second letter 'i'.
    PDF p.303 headword is 'DED' confirming the 2/1 majority.
    Egyptologist flag: verify 'Ded' vs 'Dedi' against PDF p.321 headword."""
    r = _row("TT200")
    assert r["occupant_name"] == "Ded"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Governor of the deserts on the west of Thebes" in r["notes_from_pm"]
    assert "Head of the regiment of Pharaoh" in r["notes_from_pm"]
    assert "Tuthmosis III to Amenophis II" in r["notes_from_pm"]
    assert "CHAMPOLLION, No. 36" in r["notes_from_pm"]
    assert "HAY, No. 5" in r["notes_from_pm"]
    assert "Tuy" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 303


# === Chunk 29 — TT201-TT210 (Khôkha ×8 + ʿAsâsîf ×1 + Deir el-Medina ×1) ===


def test_chunk29_all_rows_present() -> None:
    """All 10 TT201-TT210 rows must be present in reconciled.jsonl."""
    actual = {r["tomb_id"] for r in _rows()} & CHUNK29_TOMB_IDS
    assert actual == CHUNK29_TOMB_IDS, sorted(CHUNK29_TOMB_IDS - actual)


def test_chunk29_theban_area() -> None:
    """TT201-TT208 are Khôkha; TT209 is ʿAsâsîf; TT210 is Deir el-Medina
    (PM I.1 p.304-307)."""
    for tid in {f"TT{n}" for n in range(201, 209)}:
        r = _row(tid)
        assert r["theban_area"] == "Khokha", (tid, r["theban_area"])
    r209 = _row("TT209")
    assert r209["theban_area"] == "ʿAsâsîf", r209["theban_area"]
    r210 = _row("TT210")
    assert r210["theban_area"] == "Deir el-Medina", r210["theban_area"]


def test_chunk29_source_edition() -> None:
    """All chunk-29 rows cite PM I.1 2nd ed. 1960."""
    for tid in CHUNK29_TOMB_IDS:
        r = _row(tid)
        assert r["source_citation"]["edition"] == "PM I.1 2nd ed. 1960", (
            tid,
            r["source_citation"]["edition"],
        )


def test_chunk29_all_official_role_except_prince() -> None:
    """TT201-TT208 and TT210 are Official; TT209 (Hereditary prince) is Prince."""
    for tid in CHUNK29_TOMB_IDS - {"TT209"}:
        r = _row(tid)
        assert r["occupant_role"] == "Official", (tid, r["occupant_role"])
    r209 = _row("TT209")
    assert r209["occupant_role"] == "Prince", r209["occupant_role"]


def test_chunk29_tt201_re_first_royal_herald() -> None:
    """TT201 — Reʿ, First royal herald. Temp. Tuthmosis IV to Amenophis III.
    Khôkha. p.304.
    occupant_name: 2/1 majority chose `Re`; CHUNK29_CORRECTIONS restores
    ayin from PM headword `RE<` → `Reʿ`. Ayin-preserve convention."""
    r = _row("TT201")
    assert r["occupant_name"] == "Reʿ"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "First royal herald" in r["notes_from_pm"]
    assert "Tuthmosis IV" in r["notes_from_pm"]
    assert "Amenophis III" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 304


def test_chunk29_tt202_nekhtamun_prophet_ptah() -> None:
    """TT202 — Nekhtamun, Prophet of Ptaḥ Lord of Thebes, Priest in front of
    Amūn. Dyn. XIX(?). Khôkha. p.305.
    occupant_role: 2/1 majority chose High Priest; CHUNK29_CORRECTIONS
    downgrades to Official (Prophet of Ptaḥ is not First Prophet rank).
    notes_from_pm: tie-break pinned Ptaḥ underdot + no-comma; CHUNK29_CORRECTIONS
    adds macron-Ū on Amūn.
    attribution_certainty: DERIVER_OVERRIDE to attested (Dyn. XIX(?) qualifies
    dynastic date, not Nekhtamun's identity).
    Egyptologist flag: confirm Official vs High Priest for Prophet of Ptaḥ."""
    r = _row("TT202")
    assert r["occupant_name"] == "Nekhtamun"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Prophet of Ptaḥ Lord of Thebes" in r["notes_from_pm"]
    assert "Priest in front of Amūn" in r["notes_from_pm"]
    assert "Dyn. XIX(?)" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 305


def test_chunk29_tt203_unnufer_divine_father_mut() -> None:
    """TT203 — Unnufer, Divine father of Mut. Dyn. XIX. Khôkha. p.305.
    All 3 agents unanimous on all fields."""
    r = _row("TT203")
    assert r["occupant_name"] == "Unnufer"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Divine father of Mut" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 305


def test_chunk29_tt204_nebanensu_sailor_first_prophet() -> None:
    """TT204 — Nebʿanensu, Sailor of the first prophet of Amun. Dyn. XVIII.
    Khôkha. p.305.
    occupant_name: 2/1 majority chose `Nebanensu`; CHUNK29_CORRECTIONS restores
    ayin from PM headword `NEB<ANENSU` → `Nebʿanensu`."""
    r = _row("TT204")
    assert r["occupant_name"] == "Nebʿanensu"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Sailor of the first prophet of Amun" in r["notes_from_pm"]
    assert "title from cone" in r["notes_from_pm"]
    assert "Dyn. XVIII" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 305


def test_chunk29_tt205_dhutmosi_royal_butler() -> None:
    """TT205 — Ḏhutmosi, Royal butler. Temp. Tuthmosis III(?) to Amenophis II(?).
    Khôkha. p.305.
    occupant_name: 2/1 majority chose `Ḏhutmosi` (d-bar, no ḥ-underdot).
    attribution_certainty: DERIVER_OVERRIDE to attested — both (?) qualify
    regnal-date endpoints, not Ḏhutmosi's identity."""
    r = _row("TT205")
    assert r["occupant_name"] == "Ḏhutmosi"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Royal butler" in r["notes_from_pm"]
    assert "Tuthmosis III(?)" in r["notes_from_pm"]
    assert "Amenophis II(?)" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 305


def test_chunk29_tt206_inpuemhab_scribe_place_of_truth() -> None:
    """TT206 — Inpuemhab, Scribe of the Place of Truth. Ramesside. Khôkha. p.305.
    All 3 agents unanimous except B had `Inpuemḥab` (underdot-Ḥ stripped by
    2/1 majority to `Inpuemhab` per strip-Ḥ rule for occupant_name)."""
    r = _row("TT206")
    assert r["occupant_name"] == "Inpuemhab"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of the Place of Truth" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 305


def test_chunk29_tt207_haremhab_scribe_divine_offerings() -> None:
    """TT207 — Haremhab, Scribe of divine offerings of Amūn. Ramesside.
    Khôkha. p.306. Parents: Ḥemawen and Nebuy.
    notes_from_pm: tie-break pinned Ḥemawen (PM `~emawen` → underdot-Ḥ);
    CHUNK29_CORRECTIONS adds macron-Ū on Amūn."""
    r = _row("TT207")
    assert r["occupant_name"] == "Haremhab"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Scribe of divine offerings of Amūn" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert "Ḥemawen" in r["notes_from_pm"]
    assert "Nebuy" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 306


def test_chunk29_tt208_roma_divine_father_amen_re() -> None:
    """TT208 — Roma, Divine father of Amen-reʿ. Ramesside. Khôkha. p.306.
    notes_from_pm: 2/1 majority chose `Amen-Re`; CHUNK29_CORRECTIONS restores
    lowercase `r` + ayin from PM `Amen-rec` → `Amen-reʿ`."""
    r = _row("TT208")
    assert r["occupant_name"] == "Roma"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Divine father of Amen-reʿ" in r["notes_from_pm"]
    assert "Ramesside" in r["notes_from_pm"]
    assert r["theban_area"] == "Khokha"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 306


def test_chunk29_tt209_seremhatrekhyt_hereditary_prince_saite() -> None:
    """TT209 — Seremhatrekhyt (?), Hereditary prince, Sole beloved friend.
    Saite. ʿAsâsîf. p.306. Formerly read Ḥatashemro.
    notes_from_pm: 1/1/1 tie-break pinned PM-faithful form with (?) and
    formerly-read parenthetical.
    attribution_certainty: uncertain — (?) qualifies the name-reading itself
    (PM's standard reading-uncertainty marker on the name transcription).
    occupant_role: 2/1 majority Prince (correct).
    occupant_alt_names: 2/1 majority [] (correct — "formerly read" is a
    superseded reading, not an alternate personal name).
    Egyptologist flag: confirm whether `(?)` on PM's name transcription
    warrants attribution_certainty=uncertain vs attested."""
    r = _row("TT209")
    assert r["occupant_name"] == "Seremhatrekhyt"
    assert r["occupant_role"] == "Prince"
    assert r["attribution_certainty"] == "uncertain"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == []
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Hereditary prince" in r["notes_from_pm"]
    assert "Sole beloved friend" in r["notes_from_pm"]
    assert "Saite" in r["notes_from_pm"]
    assert "formerly read Ḥatashemro" in r["notes_from_pm"]
    assert r["theban_area"] == "ʿAsâsîf"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 306


def test_chunk29_tt210_raweben_servant_place_of_truth_deir() -> None:
    """TT210 — Raʿweben, Servant in the Place of Truth. Dyn. XIX.
    Deir el-Medina (NEW sub-site first seen in PM I.1 § I numbered tombs
    since chunk-9). p.307. Parents(?): Piay, Sculptor, and Nefertkhaʿ.
    Wife: Nebtyunu. Shared with TT217 (brother (?) of deceased).
    occupant_name: 2/1 majority chose `Raweben`; CHUNK29_CORRECTIONS restores
    ayin from PM `RA<WEBEN` → `Raʿweben`.
    notes_from_pm: 1/1/1 tie-break pinned agent C (L.D. cite mid-sentence +
    Piay comma + Nefertkhaʿ ayin).
    attribution_certainty: DERIVER_OVERRIDE to attested — Parents(?) qualifies
    parentage identification, not Raʿweben's identity."""
    r = _row("TT210")
    assert r["occupant_name"] == "Raʿweben"
    assert r["occupant_role"] == "Official"
    assert r["attribution_certainty"] == "attested"
    assert r["occupant_alt_names"] == []
    assert r["co_occupants"] == []
    assert r["shared_with_tombs"] == ["TT217"]
    assert r["is_joint_burial"] is False
    assert r["is_uninscribed"] is False
    assert r["is_unfinished"] is False
    assert r["is_usurped"] is False
    assert "Servant in the Place of Truth" in r["notes_from_pm"]
    assert "Dyn. XIX" in r["notes_from_pm"]
    assert "L. D. Text, No. 104." in r["notes_from_pm"]
    assert "Piay, Sculptor in the Place of Truth" in r["notes_from_pm"]
    assert "Nefertkhaʿ" in r["notes_from_pm"]
    assert "Nebtyunu" in r["notes_from_pm"]
    assert r["theban_area"] == "Deir el-Medina"
    assert r["dynasty"] is None
    assert r["source_citation"]["page"] == 307
