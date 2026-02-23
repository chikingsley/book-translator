# Translation Changelog

## 2026-02-08

### Change 1

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (poem line in "IN MEMORIAM FERRUCCIO BUSONI")
- Source phrase: `und aller Spuk entschwebt, ein leichter Flaum.`
- Previous English: `and all specters float away, a light down.`
- New English: `and all specters float away, light as down.`
- Delta type: `awkward_literalization`
- Rationale: Preserve source image (`Flaum`/down) while restoring natural English readability.

### Change 2

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (Chapter 10 song line)
- Source phrase: `Alle Tiere kehren wieder in den Garten Eden...`
- Previous English: `All animals return home to the Garden of Eden.`
- New English: `All animals return again to the Garden of Eden.`
- Delta type: `addition`
- Rationale: Removed unmarked semantic addition (`home`) and restored explicit recurrence sense (`wieder`/again).

### Change 3

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (end of naming beat in Chapter 10)
- Source phrase: Naming beat ends with chant (`Li, Li, Li`) in source witness.
- Previous English: `And Melchior-Li smiled, for the name sounded to him like laughing light.`
- New English: line removed
- Delta type: `addition`
- Rationale: Removed likely interpolation not supported by the chapter source at this point.

### Change 4

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (Chapter 3, line 383)
- Source phrase: `Es wird immer wirbliger`
- Previous English: `It is getting more and more confused`
- New English: `It is getting more and more in a whirl`
- Delta type: `substitution` + `normalization`
- Rationale: Restored motion/intensity nuance (`wirbliger`) and avoided cognitive flattening in English.

### Change 5

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (Chapter 9, line 978)
- Source phrase: `Ein leichtes Niedergleiten`
- Previous English: `A light descending.`
- New English: `A gentle sinking downward.`
- Delta type: `awkward_literalization`
- Rationale: Preserved image-motion while improving natural English readability.

### Change 6

- Location: `sources/reich-ohne-raum.en.legacy-working.md` (Foreword section, lines 56-116)
- Source phrase: Full `VORWORT` block in source witness (`sources/reich-ohne-raum.de.1962-humancheck.md`, lines 69-129)
- Previous English: `*[Translation pending]*`
- New English: Full source-locked readable foreword translation inserted.
- Delta type: `omission`
- Rationale: Completed missing paratext translation required for the 1962 witness while preserving key conceptual terms (`Reich`, `verecundia`) and source argument structure.

## 2026-02-16

### Change 7

- Location: `editions/reich-ohne-raum.en.1962-third-edition.canonical.md` (between chapter boundaries and end matter)
- Source phrase: Remaining von Franz commentary blocks in source witness (`sources/reich-ohne-raum.de.1962-humancheck.md`, lines `445-460`, `653-666`, `786-817`, `1032-1041`, `1150-1155`, `1283-1310`, `1793-1798`, `2214-2229`, `2395-2421`)
- Previous English: Commentary sections missing (only `COMMENTARY: *Introduction*` had been inserted previously)
- New English: Source-locked readable English translation inserted for all remaining commentary sections, with chapter-aligned placement and TOC entries.
- Delta type: `omission`
- Rationale: Completed full 1962 paratext coverage so the canonical English witness now includes foreword + complete von Franz commentary.

### Change 8

- Location: `editions/reich-ohne-raum.en.1962-third-edition.readable.md` (full file readability pass v1)
- Source phrase: Full canonical English witness used as source baseline (`editions/reich-ohne-raum.en.1962-third-edition.canonical.md`)
- Previous English: Baseline copy from earlier stage; not synchronized with latest canonical content and still heavily source-literal.
- New English: File regenerated from current canonical and given conservative readability smoothing (phrase-level only, no structural rewrites or added content).
- Delta type: `normalization`
- Rationale: Establish a readable derivative that preserves source fidelity while reducing high-friction literal constructions (e.g., selected `in order to` and `all at once` normalizations).
