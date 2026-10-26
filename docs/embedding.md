<!-- type: how-to -->
# Embedding the Guide

The Guide works in an ordinary iframe without a CMS plugin. For automatic height and shareable host addresses,
include the same local `embed.js` asset on the host, as shown below. Replace the Guide address with the published
site's address; for eosc.cz the host origin must match one of the origins configured on the Guide's script in
`index.html`. `self` permits a host on the Guide's own HTTP(S) origin. Add other exact origins there and rebuild
before embedding on another site. Paths, wildcards and opaque `file://` origins are not admitted to the protocol;
plain file and iframe navigation still works without it.

Ask the Guide maintainer to change its source `index.html` in a reviewed pull request if the published Guide does
not yet admit your host. The Guide-side script uses `data-parent-origins`: whitespace-separated HTTP(S) origins,
without a path or trailing slash; `self` means the Guide's own origin. For example:

```html
<script src="assets/js/embed.js"
  data-parent-origins="self https://www.eosc.cz https://eosc.cz https://host.example.org" defer></script>
```

The maintainer [builds and checks](how-to/build-and-check.md) that source and delivers the change through the
normal release route. Editing only the host page cannot change the published Guide's allowlist.

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

## Verify the host

Build the site and run `npm run check:embed`. In your host, open a long and short view, expand guidance, change
language and role, then copy and reopen the host address. Confirm that height changes without a nested scrollbar
and the view returns without losing the host's own URL state. Protocol fields and limits are in the
[embedding reference](embedding-reference.md#message-protocol-v1).
