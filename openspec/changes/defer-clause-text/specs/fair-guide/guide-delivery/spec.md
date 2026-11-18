## MODIFIED Requirements

### Requirement: Deferred advice retains complete content and search

Initial transport SHALL keep structure and short advice within the unchanged configured budget, deferring detailed advice and the text of ledger requirements; a requirement's record, with its identifier, source, principles, actor, kind, locator and status, SHALL stay in the initial transport. Every supported language/part load order SHALL reconstruct the complete bilingual graph. The crate/API SHALL retain all content. Station routes, views that show a requirement's text and complete search SHALL wait for the part that holds it. Language/load failures SHALL preserve a usable view, saved answers and retry, with local-file/iframe operation and no external request on load retained.

#### Scenario: Cold search needs deferred advice

- **GIVEN** a fresh browser whose detailed-advice language part has not loaded
- **WHEN** the reader searches for text present only in that advice while its download is delayed
- **THEN** complete results wait for the required part and include the matching advice rather than caching an incomplete index

#### Scenario: Advice language loading fails

- **GIVEN** a usable station and saved answers with the other language's advice not loaded
- **WHEN** switching languages fails to retrieve that part and the reader retries
- **THEN** the usable view and answers survive, retry loads the requested advice and the reconstructed graph retains both languages

#### Scenario: A requirement's text is shown from a cold start

- **GIVEN** a fresh browser that opens a view showing a ledger requirement, such as its catalogue entry, a station's basis or a principle in the explorer, while the part holding requirement texts is delayed
- **WHEN** the view is drawn
- **THEN** it waits for that part and shows the requirement's text in the reader's language, never an empty or untranslated requirement

#### Scenario: The first download leaves room for content

- **GIVEN** the content of the default branch
- **WHEN** the build measures what each language's page downloads before any user action
- **THEN** requirement texts are not part of it, and both languages stay within the configured budget
