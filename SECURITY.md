# Security policy

## Scope

The guide is a static page with no backend and no user accounts. It stores the user's answers only in their
browser. It sends requests to external services only when the user starts a live check or a lookup, and only
to an allowlist of hosts. Security-relevant parts are:

- the connectors in `assets/js/` that call external services and render their responses;
- the Content Security Policy and other page headers;
- the content checks and generator in `scripts/`;
- the CI workflows in `.github/workflows/`.

## Supported versions

Only the current state of `main` and the latest release are supported.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private vulnerability reporting (**Security → Report a
vulnerability**) in this repository. If that is not available, contact the maintainer privately through
<https://github.com/motyc>.

Please include the affected file or page view, steps to reproduce, and the impact you expect. You will
receive an acknowledgement, and the fix will be credited in the changelog unless you prefer otherwise.
