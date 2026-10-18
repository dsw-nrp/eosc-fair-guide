# Physical sample metadata, IP/patent exceptions, and post-publication error management

## Why

Practical gaps were identified in Stations 6 (Metadata), 7 (Licensing), and 8 (Publication):
1. **Metadata links to physical samples and instruments:** In experimental disciplines (geology, archaeology, chemistry, biology), datasets originate from physical specimens or specific equipment. Persistent identifiers (e.g. IGSN, specimen codes) and grant identifiers for national evaluation (RIV) must be explicitly linked in `metadata.05`.
2. **Intellectual property and patent filing:** Researchers often believe FAIR data requirements prevent them from filing patents or partnering with commercial sponsors. Clear guidance is needed on coordinating with Technology Transfer Offices (TTO), applying pre-filing embargos, and declaring statutory exceptions under Section 83(5) of Act No. 328/2025 Coll. (`licence.31`).
3. **Post-publication corrections and errata:** Researchers often overwrite or delete files when correcting mistakes, breaking persistent identifier immutability. Concrete steps are needed distinguishing metadata typo fixes, versioned errata with PID chains (or patches for huge files), and tombstone withdrawals for serious legal/ethical concerns (`publication.05`).

## What Changes

- Update `metadata.05` in `06-metadata.toml` to include physical sample PIDs (IGSN, collection codes), instrument identifiers, and grant/project codes.
- Add `licence.31` in `07-licence.toml` explaining patent applications, trade secrets, embargo periods, and statutory exception citations.
- Update `publication.05` in `08-publication.toml` specifying how to handle metadata typo fixes, versioned data corrections, and tombstone pages.
- Register new identifiers in `content/identifiers.toml`.
- Add an updated provenance action in `content/provenance.toml` with string literal name/description and timestamp strictly greater than base commit.

## Capabilities

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: extended with physical sample linking, patent/commercial embargo procedures, and immutable errata practices.

## Impact

Clarifies key intersections of Open Science with patent law, commercial collaboration, laboratory workflows, and citation integrity. Conforms to WCAG 2.2, bilingual parity, and RO-Crate 1.2 rules.
