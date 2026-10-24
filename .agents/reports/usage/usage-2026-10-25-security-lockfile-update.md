# Security lockfile update

- **When:** 2026-10-25
- **Agent / runtime:** Claude Code (VS Code extension)
- **Model / backend:** claude-opus-5-5
- **What:** Lockfile-only patch updates for open security advisories in development tools: `dompurify` 3.4.17
  (through `mermaid`), `undici` 8.12.3 (through `@apidevtools/swagger-parser`) and `fast-uri` 3.1.9 (through `ajv`).
  Dependabot raised the `dompurify` alerts; `npm audit` found the other two. Dependabot security updates are off by
  policy, and its version updates do not raise indirect dependencies.
- **Impacted:** `package-lock.json`, this entry.
- **Close-out:** Each integrity hash matches the registry, and `npm audit` reports 0 vulnerabilities. After `npm ci`,
  all 31 checks pass. The published site bundles none of the three packages.
