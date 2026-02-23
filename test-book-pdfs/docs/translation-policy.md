# Translation Constitution and Policy (v1.0)

Date established: 2026-02-08  
Last revised: 2026-02-16  
Project: `Das Reich ohne Raum` translation corpus

## Objective

Create a translation corpus with clear edition boundaries and clear mode boundaries:

1. Canonical editions are source-locked and edition-locked.
2. Readable editions are derived from canonical text and stay semantically faithful.
3. Commentary and interpretation stay outside narrative body text.

## Corpus Constitution (Edition Set)

This project tracks the following edition artifacts:

1. German 1919 source witness (`DE-1919`, no foreword, no von Franz commentary, original 15-chapter structure).
2. English 1919 canonical translation (`EN-1919-canonical`, edition-locked to the 1919 witness).
3. German 1962 source witness (`DE-1962`, includes Corti foreword and von Franz commentary).
4. English 1962 canonical translation (`EN-1962-canonical`, edition-locked to 1962 witness).
5. English 1962 readable-literary derivative (`EN-1962-readable`, derived from `EN-1962-canonical`, never replacing it).

## Non-Negotiable Rules

1. Edition lock first: no element may be added across editions without explicit edition evidence.
2. No silent additions: added meaning in English is prohibited unless explicitly marked.
3. No silent omissions: source meaning cannot be dropped for smoothness.
4. Symbolic integrity: recurring motifs and key images must remain traceable across the corpus.
5. Register integrity: retain authorial pressure and difficulty where it is intentional.
6. Readability is allowed only after source meaning and image are preserved.
7. Commentary firewall: von Franz or other interpretive material must not be merged into narrative body text.
8. Output separation: canonical and readable-literary outputs must exist as separate files, never overwrites.
9. Terminology consistency: recurring terms must stay consistent unless context forces change.
10. Evidence discipline: uncertain readings are flagged and resolved against source witness, not guessed.
11. Auditability: every substantive change is logged with rationale in changelog.
12. Reproducibility: policy decisions must be explicit enough that another translator can follow them.

## Translation Modes

### Mode A: Canonical (source-locked)

Use for `EN-1919-canonical` and `EN-1962-canonical`.

Rules:
1. Prioritize semantic and imagistic fidelity over fluency.
2. Preserve controlled strangeness where source strangeness is intentional.
3. Allow minimal idiomatic repair only when literal form breaks English comprehension.
4. Do not import interpretation from secondary commentary.

### Mode B: Readable-Literary (derived)

Use for optional reader-facing edition derived from canonical.

Rules:
1. No plot/event/symbolic shifts.
2. Improve cadence and readability without flattening rhetoric.
3. Keep cognitive pressure equivalent to source where difficulty is integral.
4. All meaningful departures from canonical are logged.

## Source Fidelity Delta Types

- `addition`: English introduces meaning not explicit in source.
- `omission`: English removes explicit source meaning.
- `substitution`: English shifts meaning strength or direction.
- `normalization`: English smooths intentionally strange source wording.
- `register_shift`: English changes formality/archaic level significantly.
- `ambiguity_collapse`: English resolves uncertainty left open in source.
- `awkward_literalization`: literal wording preserved but English idiom is broken.
- `paratext_leak`: commentary/interpretive material contaminates narrative text.

## Workflow Standard

1. Identify witness and edition boundary before translating.
2. Produce canonical pass (source-locked).
3. Run fidelity audit against source.
4. Log all corrections in changelog.
5. If needed, produce readable-literary derivative from canonical.
6. Re-audit derivative for semantic drift.

## Change Logging Requirement

Every substantive translation edit must be logged in
`translation-changelog.md` with:

1. Date
2. Target file and line reference
3. Source phrase
4. Previous English
5. New English
6. Delta type
7. Rationale
8. Edition scope impacted (`1919-canonical`, `1962-canonical`, `1962-readable`, or multiple)

## Decision Hierarchy

When options conflict:

1. Edition evidence
2. Source meaning
3. Source image/motif
4. Source register/rhetorical force
5. Readability

## Current Known Gaps

1. `EN-1962-canonical` still requires full translation of von Franz commentary sections if this edition is to be text-complete in English.
2. `EN-1962-readable` currently begins as a baseline copy and requires dedicated readability pass.
3. `DE-1919` and `EN-1919-canonical` should be spot-checked against physical 1919 scans at section boundaries.
