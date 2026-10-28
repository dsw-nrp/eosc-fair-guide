<!-- type: reference -->
# Embedding reference

The [embedding how-to](embedding.md) owns host setup. A host uses one managed Guide frame; the protocol carries
only navigation and size, with strict origin and window checks.

The Guide-side `index.html` script's `data-parent-origins` value is a whitespace-separated list of exact HTTP(S)
origins, plus `self` for its own origin. Paths, trailing slashes, wildcards and opaque origins are not admitted.
The [embedding how-to](embedding.md) gives both Guide-side configuration and host-side markup.

The host keeps its own path, parameters and fragment. `fair-guide-view` records the current Guide view;
`history.replaceState` avoids filling Back history. Back and Forward restore the selected view.

## Message protocol v1

| Direction | Message | Fields |
| --- | --- | --- |
| Host → Guide | `fair-guide:init` | `version: 1`, `view`: a Guide fragment beginning with `#/` |
| Guide → Host | `fair-guide:state` | `version: 1`, `view`: current fragment, `height`: integer content height in CSS pixels |

Both ends check the sending window, its exact origin, message type, version and field shape. The Guide accepts
only its parent and an origin configured in its script; the host accepts only the selected iframe and its source
origin. Replies name the accepted parent origin. The protocol sends no answers, stored evidence or credentials.
A view explicitly containing a shared result remains a shared address; avoid including private information in it.
Views are bounded to 2 MiB of characters (including encoded shared results) and height to 24–1000000 pixels.
Invalid messages have no effect.

Height is updated after content, navigation, disclosure, font/image loading and width changes. Measuring body
content lets a short view shrink after a long one, without an iframe scrollbar or a resize feedback loop. Messages
with unchanged view and height are suppressed. Without an admitted handshake the Guide sends nothing to its host.

`npm run check:embed` checks the built site. The local host fixture tests resizing in both directions, disclosure,
view restoration, language and role changes, unrelated host URL state, and rejection of forged or foreign messages.
