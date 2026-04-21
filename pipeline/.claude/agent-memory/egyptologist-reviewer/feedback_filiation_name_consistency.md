---
name: Preserve Baud's French king names in filiation fields
description: Baud uses French forms (Rêkhaef, Snéfrou, Pépi Iᵉʳ) — don't silently anglicize in father/mother/spouse fields
type: feedback
---

Baud's PARENTÉ prose gives kings in French school form: Snéfrou, Khoufou, Rêdjedef, Rêkhaef, Menkaourê, Chepseskaf, Sahourê, Néferirkarê, Rênéferef, Niouserrê, Djedkarê, Ounas, Téti, Pépi Iᵉʳ, Merenrê, Pépi II.

**Why:** Phase-A normalization reconciles to the canonical pharaoh.se Conventional English Display Form; the Phase-0 extraction preserves Baud's wording verbatim so the provenance chain is auditable. Silently anglicizing (e.g. "Rêkhaef" → "Khafre") in filiation fields during extraction erases that provenance.

**How to apply:** If a row has `father_name: "Khafre"` but Baud's prose says "Rêkhaef", that's a drift — flag it. `name_anglicised` is the one field where English forms go; filiation fields should carry Baud's form. Exception: if Baud himself uses the transliterated form (e.g. `Ḫwfw-ḫꜥ.f I`), preserve that.
