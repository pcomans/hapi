# Merge review — ruler escalation queue (2026-10-12)

The `egyptologist-reviewer` checked every merged cluster of the rebuilt graph against the
source records (`pipeline/pipeline/authority/sources/*/reconciled.jsonl`), with special
attention to the Second and Third Intermediate Periods, reused throne names and Horus-name
links after Dynasty 3. It reviewed the graph before the code-review guards (438 approved
links, 58 merged clusters; its reviewer run is `reviewed-run.jsonl.gz`) and found **no
false merge**. The guards only remove approvals: every link approved in the committed graph
is one of the 438 reviewed (`merge-review.json`, pinned by
`pipeline/tests/test_ruler_escalation_queue_audit.py`). The table lists the 51 merged
clusters of the committed graph, each a subset of a reviewed cluster.

| Cluster | Records | Joined by | Verdict |
|---|---|---|---|
| (Queen) Sobekneferu | 3 | horus | correct |
| Amenemnisu | 4 | name_dynasty | correct |
| Amenhotep II | 3 | prenomen | correct |
| Amenmesse | 3 | horus | correct |
| Apries | 4 | name_dynasty | correct |
| Arses | 2 | name_dynasty | correct |
| Artaxerxes I | 2 | name_dynasty | correct |
| Dareios III. | 2 | name_dynasty | correct |
| Djed-ka-re Isesi | 3 | name_dynasty | correct |
| Djet | 2 | name_dynasty | correct |
| Intef I | 2 | horus | correct |
| Intef II | 2 | horus | correct |
| Intef III | 2 | horus | correct |
| Kashta | 2 | name_dynasty | correct |
| Mentuhotep I | 2 | horus | correct |
| Mer-en-ptah | 3 | name_dynasty | correct |
| Necho II | 3 | name_dynasty | correct |
| Nefaarudu I | 3 | name_dynasty | correct |
| Neferkaura | 2 | prenomen | correct |
| Ni-user-rê Ini | 3 | name_dynasty | correct |
| Osochor | 3 | name_dynasty | correct |
| Osorkon II | 4 | name_dynasty | correct |
| Osorkon III | 3 | name_dynasty | correct |
| Pa-Seba-Kha-En-Niut II | 2 | name_dynasty | correct |
| Pedubast I | 2 | name_dynasty | correct |
| Pepi I | 3 | name_dynasty | correct |
| Pi-nodjem I. | 2 | name_dynasty | correct |
| Psametik I. | 4 | name_dynasty | correct |
| Psametik II. | 4 | name_dynasty | correct |
| Psametik III. | 4 | name_dynasty | correct |
| Psusennes I | 3 | name_dynasty | correct |
| Ptolemy II | 2 | horus | correct |
| Ptolemy V | 2 | horus | correct |
| Ptolemy XV | 2 | horus | correct |
| Qemau Siharnedjheritef | 2 | prenomen | correct |
| Ramesses III | 3 | horus, name_dynasty | correct |
| Ramesses VII | 3 | horus, name_dynasty | correct |
| Ramesses XI | 4 | name_dynasty | correct |
| Rudamun | 3 | name_dynasty | correct |
| Sahura | 2 | horus | correct |
| Sethôs II. | 3 | name_dynasty | correct |
| Shoshenq III | 4 | name_dynasty | correct |
| Siamun | 4 | name_dynasty | correct |
| Taharqa | 4 | name_dynasty | correct |
| Tantamani | 3 | name_dynasty | correct |
| Teti | 3 | horus, name_dynasty | correct |
| Thutmose II | 3 | prenomen | correct |
| Thutmose IV | 2 | prenomen | correct |
| Unas | 3 | horus, name_dynasty | correct |
| Userkaf | 2 | name_dynasty | correct |
| Xerxes I | 2 | name_dynasty | correct |

Points the reviewer recorded:
- Kings sharing a reused throne name stay in separate clusters: Merenptah and Nepherites I
  (Baenre); Osorkon II and Osorkon III (Usermaatre-setepenamun); Psamtik I's Wahibre
  outside Apries; Kitchen 23.02 Iuput I outside Osorkon III; the Shoshenq IV renumbering
  pairs escalated, not merged.
- Psusennes II excludes the High Priest "Psusennes" (Beckerath 21.09).
- Pinedjem I is correct, but the reviewer's reason calls his prenomen "Kheperkare"
  (Senwosret I's); Beckerath 21.08 has Cheper-cha-rê = Khakheperre (P3, reason text only).
- Leprohon "Meryibre Khety (VIII)" = pharaoh.se "Meribra Khety I" (same objects and
  bibliography; Leprohon numbers the Herakleopolitan Khetys in sequence). The pair is
  `name_only` in the committed graph because the normaliser keys "mery ib ra" and
  "Mer ib Ra" differently (follow-up), so it is escalated, not merged. Leprohon's separate
  "[Khety I]" (9-10a.01) must never join that cluster.

Missed merges the reviewer judged (all escalated, in the queue): Senakhtenre Ahmose
(Leprohon 17.26, pharaoh.se) against Ryholt 17.7 "Siamun (?)": same king (Biston-Moulin
2012); Seqenenre Tao (Leprohon 17.27, pharaoh.se) against Ryholt 17.8: same king, the
sources print different Horus names; escalation is defensible.

Source-data issues for follow-up: the pharaoh.se Ptolemy V row is column-shifted (prenomen
truncated to "Iwa en netjerwy"); pharaoh.se Qemau-Siharnedjheritef carries the alt label
"Amenemhat VI", which is Ryholt 13.8.
