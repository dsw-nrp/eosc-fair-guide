"""Small explicit publication evidence for archive/protocol tests; not a passed real release."""

import json


def publication_files(base="https://example.org/guide/", *, semantic=None, built=None, version="1.2.3-alpha.1"):
    semantic = semantic or base
    vocab, profile = semantic + "terms#", semantic + "profile/0.1"
    config = {"pageUrl": base, "vocab": {"guide": vocab}}
    if built is not None:
        config["build"] = built
    crate = {
        "@context": ["https://w3id.org/ro/crate/1.2/context", {"scope": vocab + "scope"}],
        "@graph": [
            {"@id": "./", "@type": "Dataset", "version": version, "conformsTo": {"@id": profile}},
            {"@id": profile, "@type": "Profile"},
            {"@id": vocab + "scope", "@type": "rdf:Property"},
        ],
    }
    return {
        "assets/data/ui.js": ("window.FairGuideData.ui = " + json.dumps({"config": config}) + ";\n").encode(),
        "ro-crate-metadata.json": json.dumps(crate).encode(),
    }
