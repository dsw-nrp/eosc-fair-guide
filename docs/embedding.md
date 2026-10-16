# Embedding the Guide

The Guide works in an ordinary iframe without a CMS plugin. For automatic height and shareable host addresses,
include the same local `embed.js` asset on the host, as shown below. Replace the Guide address with the published
site's address; for eosc.cz the host origin must match one of the origins configured on the Guide's script in
`index.html`. `self` permits a host on the Guide's own HTTP(S) origin. Add other exact origins there and rebuild
before embedding on another site. Paths, wildcards and opaque `file://` origins are not admitted to the protocol;
plain file and iframe navigation still works without it.

```html
<iframe id="fair-guide" title="Průvodce FAIR daty"
  src="https://fair.eosc.cz/#/cs/DS/path/start"
  style="width:100%;height:800px;border:0"></iframe>
<script src="https://fair.eosc.cz/assets/js/embed.js"
  data-guide-frame="fair-guide" defer></script>
```

The host's Content Security Policy must permit the Guide origin in `frame-src` and `script-src`. The host iframe
needs JavaScript; if sandboxed, allow scripts and the original origin. Clipboard and download permission follow
the host's policy. Never configure a wildcard origin or remove the message-source checks.

The host keeps its own path, parameters and fragment. The `fair-guide-view` query parameter records the current
Guide view. Copying the host address reopens that view, including its language, role and selected check part.
This parameter changes with `history.replaceState`, so reading the Guide does not fill the host's Back history.
Back or Forward to a host entry with a different view restores it. A host uses one managed Guide frame.

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

Run `npm run check:embed` after building. The local host fixture tests resizing in both directions, disclosure,
view restoration, language and role changes, unrelated host URL state, and rejection of forged or foreign messages.
