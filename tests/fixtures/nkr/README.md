# NKR Repository fixture

The five public Repository records present on 1 November 2026, fetched from
`https://repo.cz/search?query=type:Repository&pageSize=100&pageNum=0` on
2 November 2026. Their handles, names, addresses and types match the first
harvest in [dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168).
`nkr-schema.json` is the Repository schema from `https://repo.cz/schemas/Repository`.

Every main contact is replaced with `contact@example.org`. Record ACLs and
editing metadata are omitted, as are the unlicensed repository descriptions.
No fixture is published as Guide content. The remaining source values, including
NKR status spellings and keyword typos, are retained for regression tests.
