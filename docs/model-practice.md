# Layers and seams in the guide

The guide uses the conceptual model from *Layers and seams of FAIR implementation in the Czech national
research data infrastructure* (in preparation). `content/model.toml` maintains six functional layers,
twelve connections across responsibility boundaries, reviewed associations and role-specific explanations.
The model overview, catalogue, path and checks reuse those records.

The layer order explains a functional rationale. It is not a project timeline or maturity scale. A connection
can join different functions within one layer. The guide's four reader lenses, its L0–L3 disclosure levels,
the FAIR principles and the groups of individual assessment frameworks retain their own meanings.

## One maintained relationship, several useful views

An association links an item to the function or information transfer it addresses. A question is associated
according to its criterion; a test according to its actual documented coverage. Connections supply their
related layers, so an editor does not need to repeat those layer links on every associated item. No association
is propagated from all the sources an item cites.

For repository-to-NMA discovery, `dataset.05` asks about an NMA record, `maturity.05` about an OAI-PMH
endpoint and `gate.08` about harvesting. These are different claims. An NMA record may have been entered
manually, and an available endpoint does not establish successful harvesting. Model filters group relevant
content without treating all of it as a test of the whole connection.

Conceptual connections carry no operational status. Implementation examples retain their own scope,
evidence and observation date. The manuscript's national mapping observes September 2026, at month
precision. Its NKR catalogue pilot and planned catalogue-to-planning integration are separate examples.
Maintenance actors are not labelled as formally accountable owners without evidence of such an assignment.

## The guide's own information transfer

The worked example follows existing records:

1. Source requirement `A.F1.R1` describes assigning a persistent data identifier.
2. Question `dataset.01` turns that requirement into an assessment criterion.
3. Test `guide-dataset-01` inspects supported PID resolution. Its record, implementation and documentation
   state that this does not establish long-term data availability.
4. Provenance action `2026-10-11-test-definitions-and-health` records the revision that made the test
   implementation and its limits inspectable.

This chain demonstrates how source meaning, assessment scope and revision information travel between
functions. It does not invent a test run. Actual saved results additionally carry their target, observation,
date, source, test reference and available invocation details. A recipient can inspect that evidence before
changing metadata or service configuration. Unavailable evidence remains an inspection limitation.

## Editing

Add explicit associations in `content/model.toml`, using existing content identifiers. Check the complete
question or advice item before assigning a connection. Station explanations belong in Proč; practical
corrections belong in the existing steps. Preserve published requirement wording and originals, especially
where the guide clarifies that FIPs select resources while detailed requirements live in profiles and schemas.

The in-preparation manuscript is an explicitly approved conceptual-model source. It supplies no new
compliance obligations. Do not invent its publication metadata or republish the working document.
The maintainer explicitly approved adapting Figures 1–3: the general model, Czech NDI functions and
metadata architecture. Bilingual SVGs in `assets/diagrams/` retain the originals' geometry, colours,
functional labels and scoped statuses and arrow meanings. Adaptations use web fonts, translated labels,
accessible titles/descriptions and adjacent prose; each can be opened at full size. The national figures
show the state as of October 2026, confirmed by the maintainer, rather than a live service-status dashboard.
Source-scoped catalogue examples retain the manuscript's September observation dates.

Run the content, model, API and page checks after building. Record the edited model and associated items in
the batch's provenance action. The deferred team audit of test gaps and validity starts from the first
official prerelease and remains a separate standing task.
