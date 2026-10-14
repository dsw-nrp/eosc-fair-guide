/* Reviewed public object and software discovery, loaded locally only after an explicit lookup. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const live = FG.live;
  const connector = live.connector;

  /** Bounded anonymous GET. Redirects are refused before they can contact an unreviewed origin. External
      text stays inert; even HTML is parsed only in a detached document and never inserted into the page. */
  async function publicRead(connectorId, path, options) {
    const target = connector(connectorId);
    const url = new URL(path, target.origin + "/");
    if (url.origin !== target.origin || url.username || url.password) throw Object.assign(new Error("unsupported origin"), { code: "unsupported-origin" });
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), (options.timeoutSeconds || 20) * 1000);
    try {
      const response = await fetch(url.href, { method: "GET", headers: { Accept: options.accept || "application/json" },
        signal: controller.signal, credentials: "omit", referrerPolicy: "no-referrer", redirect: "error" });
      if (response.status === 404 && options.allowNotFound) return null;
      if (!response.ok) {
        const limited = response.status === 429 || (response.status === 403 && response.headers.get("x-ratelimit-remaining") === "0");
        throw Object.assign(new Error(target.name + ": HTTP " + response.status), { code: limited ? "rate-limit" : "http-error", status: response.status });
      }
      if (response.type === "opaque" || response.type === "opaqueredirect" || (response.url && new URL(response.url).origin !== target.origin)) {
        throw Object.assign(new Error("unreadable response or redirect"), { code: "unreadable-response" });
      }
      if (Number(response.headers.get("content-length")) > options.maxBytes) {
        if (response.body) await response.body.cancel();
        throw Object.assign(new Error("response exceeds byte limit"), { code: "size-limit" });
      }
      let text = "";
      if (response.body && response.body.getReader) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let bytes = 0;
        try {
          while (true) {
            const chunk = await reader.read();
            if (chunk.done) break;
            bytes += chunk.value.byteLength;
            if (bytes > options.maxBytes) {
              await reader.cancel();
              throw Object.assign(new Error("response exceeds byte limit"), { code: "size-limit" });
            }
            text += decoder.decode(chunk.value, { stream: true });
          }
          text += decoder.decode();
        } finally { reader.releaseLock(); }
      } else {
        text = await response.text();
        if (new TextEncoder().encode(text).byteLength > options.maxBytes) throw Object.assign(new Error("response exceeds byte limit"), { code: "size-limit" });
      }
      return { text, url: url.href, headers: response.headers, format: String(response.headers.get("content-type") || "").split(";")[0].toLowerCase() };
    } finally { clearTimeout(timer); }
  }

  function diagnostic(result, error, source, url) {
    result.diagnostics.push({ code: error.code || (error.name === "AbortError" ? "timeout" : "unavailable"), source, url,
      message: String(error.message || error).slice(0, 500) });
  }

  function safeAddress(value, base) {
    try {
      const url = new URL(String(value || ""), base);
      return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
    } catch (error) { return null; }
  }

  live.readPublic = publicRead;
  live.identityMatch = (...args) => identityMatch(...args);

  /* ---------------------------------------------------------------- shared object discovery */

  function identityValue(value) {
    if (value && typeof value === "object") return value["@id"] || value.value || value["@value"] || "";
    return typeof value === "string" ? value.trim() : "";
  }

  function identityMatch(data, pid, landing, registry, base) {
    // Compact JSON-LD terms only identify a subject when their declared vocabulary supports that meaning; the shared
    // bounded reader in assess.js decides that, exactly as the assessments read the same representation.
    const values = (name) => registry ? FG.list(data[name]) : FG.jsonLd.propertyValues(data, name);
    const identifiers = values("identifier").concat(registry ? FG.list(data.doi) : []);
    const stated = [...identifiers, ...FG.list(data["@id"]), ...values("url"), ...values("sameAs")].map(identityValue).filter(Boolean);
    const claimed = identifiers.map(identityValue).map(live.parsePid).filter(Boolean);
    const equal = (other) => pid && other && other.type === pid.type && (pid.type === "doi" ? other.value.toLowerCase() === pid.value.toLowerCase() : other.value === pid.value);
    if (pid && claimed.length && !claimed.some(equal)) return "mismatched";
    if (stated.some((value) => equal(live.parsePid(value)) || (landing && safeAddress(value, base || landing) === safeAddress(landing)))) return "matched";
    return stated.length ? "mismatched" : "unverified";
  }

  function headerLinks(value, base) {
    const links = [];
    /* Split only between complete link-values; commas inside quoted parameters or the URI stay intact. */
    for (const match of String(value || "").matchAll(/<([^>]*)>((?:[^<"]|"[^"]*")*)/g)) {
      const parameters = {};
      for (const pair of match[2].matchAll(/;\s*([\w-]+)\s*=\s*(?:"([^"]*)"|([^;,\s]+))/g)) parameters[pair[1].toLowerCase()] = pair[2] || pair[3];
      const url = safeAddress(match[1], base);
      if (url) links.push({ url, rel: String(parameters.rel || "").split(/\s+/), type: parameters.type || null,
        anchor: parameters.anchor ? safeAddress(parameters.anchor, base) : base, profile: parameters.profile || null });
    }
    return links;
  }

  /** Read Schema.org microdata using HTML property boundaries, including itemref and nested items.
      This is a bounded vocabulary-specific reader, not a general RDF or conformance validator. */
  function microdata(doc, base, limit) {
    const tokens = (value) => String(value || "").trim().split(/\s+/).filter(Boolean);
    let remaining = 2000, limited = false;
    const read = (scope, ancestors = new Set()) => {
      if (ancestors.has(scope) || ancestors.size >= 8) { limited = true; return null; }
      const types = tokens(scope.getAttribute("itemtype"));
      if (!types.length || types.some((type) => !/^https?:\/\/schema\.org\/[^/#]+$/.test(type))) return null;
      const data = Object.create(null);
      data["@context"] = FG.config.discovery.schemaVocabulary;
      data["@type"] = types.map((type) => type.replace(/^http:/, "https:"));
      if (scope.hasAttribute("itemid")) data["@id"] = safeAddress(scope.getAttribute("itemid"), base);
      const pending = [...scope.children];
      for (const id of tokens(scope.getAttribute("itemref"))) {
        const referenced = doc.getElementById(id);
        if (referenced) pending.push(referenced);
      }
      const visited = new Set([scope]);
      const lineage = new Set(ancestors).add(scope);
      while (pending.length && remaining > 0) {
        const node = pending.shift();
        if (visited.has(node)) continue;
        visited.add(node); remaining -= 1;
        const properties = tokens(node.getAttribute("itemprop"));
        if (!node.hasAttribute("itemscope")) pending.unshift(...node.children);
        if (!properties.length) continue;
        let value;
        if (node.hasAttribute("itemscope")) value = read(node, lineage);
        else if (node.tagName === "META") value = node.getAttribute("content");
        else if (["A", "AREA", "LINK"].includes(node.tagName)) value = safeAddress(node.getAttribute("href"), base);
        else if (["AUDIO", "EMBED", "IFRAME", "IMG", "SOURCE", "TRACK", "VIDEO"].includes(node.tagName)) value = safeAddress(node.getAttribute("src"), base);
        else if (node.tagName === "OBJECT") value = safeAddress(node.getAttribute("data"), base);
        else if (["DATA", "METER"].includes(node.tagName)) value = node.getAttribute("value");
        else if (node.tagName === "TIME" && node.hasAttribute("datetime")) value = node.getAttribute("datetime");
        else value = node.textContent;
        if (value == null) continue;
        for (const name of properties) {
          if (FG.unsafeKey(name) || ["@context", "@id", "@type"].includes(name)) continue;
          data[name] = FG.list(data[name]).concat(value);
        }
      }
      if (pending.length) limited = true;
      return data;
    };
    const scopes = [...doc.querySelectorAll("[itemscope][itemtype]")];
    if (scopes.length > limit) limited = true;
    return { nodes: scopes.slice(0, limit).map((scope) => read(scope)).filter(Boolean), limited };
  }

  /** Discover one object after a user action; this does not run FAIR Champion. Returns {input,pid,supported,
      resolved,datacite,date,representations,observations,diagnostics,links,coverage}. A representation is
      {source,record,url,subject,format,data,identity,profiles,declarations,links}. Only identity-matched representations
      enter this collection. Observations report facts, never a CDIF/FDO conformance verdict. Unsupported
      managed PID families remain manual assessment targets with supported:false, rather than invalid IDs.
      An HTTPS landing target has pid:null; resolved is populated only after its actual successful read. */
  live.discoverObject = async function (input) {
    const config = FG.config.discovery;
    const pid = typeof input === "object" && input ? live.parsePid(input.value) : live.parsePid(input);
    const inputValue = typeof input === "object" && input ? input.value : String(input || "").trim();
    const suppliedLanding = !pid && safeAddress(inputValue);
    const result = { input: inputValue, pid, supported: Boolean(pid || suppliedLanding),
      resolved: null, datacite: null, date: new Date().toISOString(), representations: [], observations: [], diagnostics: [], links: [],
      coverage: { requests: 0, maxRequests: config.maxRequests, truncated: false } };
    if (!result.supported) {
      diagnostic(result, { code: "unsupported-pid", message: "Automatic discovery supports DOI, Handle and reviewed HTTPS landing pages; other managed identifiers can be assessed manually." }, "resolver", safeAddress(result.input));
      return result;
    }
    const pidUrl = pid ? live.pidUrl(pid) : suppliedLanding;
    const subjectUrls = new Set([pidUrl]);
    const budget = async (action) => {
      if (result.coverage.requests >= config.maxRequests) throw Object.assign(new Error("discovery request limit"), { code: "request-limit" });
      result.coverage.requests += 1;
      return action();
    };
    const bounded = { maxBytes: config.maxBytes, timeoutSeconds: config.timeoutSeconds };
    const nodesOf = (data, source, url) => {
      const nodes = FG.list(data && (data["@graph"] || data));
      const limit = config.maxRepresentations * 4;
      if (nodes.length > limit) {
        result.coverage.truncated = true;
        diagnostic(result, { code: "representation-limit", message: "Only a bounded number of metadata subjects were inspected." }, source, url);
      }
      return nodes.slice(0, limit).map((node) => node && typeof node === "object" && data["@context"] !== undefined && !Object.prototype.hasOwnProperty.call(node, "@context") ?
        Object.assign({ "@context": data["@context"] }, node) : node);
    };
    const observe = (kind, value, representation, path) => result.observations.push({ kind, value, source: representation.source,
      record: representation.url, subject: pidUrl, date: result.date, representation: representation.url, path, coverage: "partial" });
    const addRepresentation = (data, source, url, format, links, profiles, landing) => {
      const identity = identityMatch(data, pid, landing, source === "datacite" || format === "text/html", url);
      if (identity !== "matched") {
        diagnostic(result, { code: "identity-" + identity, message: "The representation does not establish the inspected object's identity." }, source, url);
        return;
      }
      if (result.representations.length >= config.maxRepresentations) {
        result.coverage.truncated = true;
        diagnostic(result, { code: "representation-limit", message: "Representation inspection is bounded." }, source, url);
        return;
      }
      /* Preserve declarations and their predicates/context; interpreting a vocabulary and validating a
         profile are separate assessment steps. Remote JSON-LD contexts are never fetched. */
      const declarations = Object.entries(data).filter(([predicate]) => /(?:^|[\/#:])(?:conformsTo|profile)$/.test(predicate))
        .flatMap(([predicate, values]) => FG.list(values).slice(0, config.maxLinks).map((value) => ({ predicate, value: identityValue(value) || (value && value.url) })))
        .filter((entry) => typeof entry.value === "string" && entry.value).slice(0, config.maxLinks);
      const found = { source, record: url, url, subject: pidUrl, format, data, identity, profiles: profiles || [], declarations, links: links || [] };
      result.representations.push(found);
      subjectUrls.add(url);
      observe("representation", format, found, "Content-Type");
      for (const profile of found.profiles) observe("declared-profile", profile, found, "profile");
    };
    if (pid) try {
      result.resolved = await budget(() => live.resolvePid(pid, bounded));
      if (result.resolved.found) result.observations.push({ kind: "pid-record", value: result.resolved.values,
        source: "pid-record", record: pidUrl, subject: pidUrl, date: result.date, coverage: "partial" });
      else diagnostic(result, { code: "not-found", message: "The resolver did not return this identifier." }, pid.type, pidUrl);
    } catch (error) { diagnostic(result, error, pid.type, pidUrl); }
    if (pid && pid.type === "doi") {
      const url = new URL("dois/" + encodeURIComponent(pid.value), live.origin("datacite") + "/").href;
      try {
        const data = await budget(() => live.datacite(pid.value, bounded));
        if (data && identityMatch(data, pid, null, true) === "matched") {
          result.datacite = data;
          addRepresentation(data, "datacite", url, "application/json", [], [], null);
        } else if (data) diagnostic(result, { code: "identity-mismatched", message: "DataCite returned a different DOI." }, "datacite", url);
      } catch (error) { diagnostic(result, error, "datacite", url); }
    }
    const landing = suppliedLanding || safeAddress(result.resolved && result.resolved.url);
    if (!landing) return result;
    subjectUrls.add(landing);
    const queue = [{ url: landing, rel: ["landing"], anchor: landing }];
    const visited = new Set();
    const allowed = (url) => config.connectors.map(connector).find((entry) => entry.origin === new URL(url).origin);
    function enqueue(links, source) {
      for (const link of links) {
        if (result.links.length >= config.maxLinks) {
          result.coverage.truncated = true;
          diagnostic(result, { code: "link-limit", message: "Link discovery is bounded." }, source, link.url);
          break;
        }
        result.links.push(Object.assign({ source, subject: pidUrl, date: result.date }, link));
        if (link.anchor && !subjectUrls.has(link.anchor)) {
          diagnostic(result, { code: "identity-mismatched", message: "Link anchor describes a different subject." }, source, link.url);
          continue;
        }
        if (link.rel.some((rel) => ["describedby", "linkset"].includes(rel))) queue.push(link);
        if (link.rel.includes("profile") && subjectUrls.has(link.anchor)) {
          result.observations.push({ kind: "declared-profile", value: link.url, source, record: link.anchor, subject: pidUrl, date: result.date, coverage: "partial" });
        }
      }
    }
    /* A registry's explicit HasMetadata relation is a discovery route, not a conformance assertion.
       No API location or schema is inferred from a landing hostname or URL path. */
    if (result.datacite) enqueue(FG.list(result.datacite.relatedIdentifiers)
      .filter((item) => item && item.relationType === "HasMetadata" && item.relatedIdentifierType === "URL")
      .map((item) => ({ url: safeAddress(item.relatedIdentifier), rel: ["describedby"], anchor: pidUrl }))
      .filter((item) => item.url), "datacite");
    while (queue.length && result.coverage.requests < config.maxRequests) {
      const link = queue.shift();
      if (visited.has(link.url)) continue;
      visited.add(link.url);
      const target = allowed(link.url);
      if (!target) { diagnostic(result, { code: "unsupported-origin", message: "This origin has no reviewed discovery connector; inspect the link manually." }, "landing", link.url); continue; }
      try {
        const response = await budget(() => publicRead(target.id, link.url, Object.assign({}, bounded, {
          accept: "text/html, application/ld+json, application/json, application/linkset+json, application/linkset" })));
        if (suppliedLanding && link.url === suppliedLanding) result.resolved = { found: true, url: suppliedLanding, title: null, values: [] };
        let links = headerLinks(response.headers.get("link"), link.url);
        const profiles = links.filter((entry) => entry.rel.includes("profile") && entry.anchor === link.url).map((entry) => entry.url).slice(0, config.maxLinks);
        if (link.profile) profiles.push(link.profile);
        if (response.format === "text/html") {
          const doc = new DOMParser().parseFromString(response.text, "text/html");
          const documentBase = safeAddress(doc.querySelector("base[href]")?.getAttribute("href"), link.url) || link.url;
          if (suppliedLanding && link.url === suppliedLanding) result.resolved.title = doc.title || null;
          links = links.concat([...doc.querySelectorAll("link[rel][href], a[rel][href]")].map((node) => ({ url: safeAddress(node.getAttribute("href"), documentBase),
            rel: node.getAttribute("rel").split(/\s+/), type: node.getAttribute("type"), anchor: link.url })).filter((entry) => entry.url));
          profiles.push(...links.filter((entry) => entry.rel.includes("profile") && entry.anchor === link.url).map((entry) => entry.url).filter((url) => !profiles.includes(url)));
          /* Resolution establishes the landing document's scope; JSON-LD nodes still match independently. */
          if (link.url === landing) addRepresentation({ url: landing, title: doc.title }, "landing", link.url, "text/html", links, profiles, landing);
          const scripts = [...doc.querySelectorAll('script[type="application/ld+json"]')];
          if (scripts.length > config.maxRepresentations * 4) {
            result.coverage.truncated = true;
            diagnostic(result, { code: "representation-limit", message: "Only a bounded number of embedded metadata blocks were inspected." }, "landing", link.url);
          }
          for (const script of scripts.slice(0, config.maxRepresentations * 4)) {
            try {
              const parsed = JSON.parse(script.textContent);
              for (const node of nodesOf(parsed, "landing", link.url)) if (node && typeof node === "object") {
                addRepresentation(node, "landing", link.url, "application/ld+json", links, profiles, landing);
              }
            } catch (error) { diagnostic(result, { code: "unsupported-format", message: "Unreadable JSON-LD." }, "landing", link.url); }
          }
          const items = microdata(doc, documentBase, config.maxRepresentations * 4);
          if (items.limited) {
            result.coverage.truncated = true;
            diagnostic(result, { code: "representation-limit", message: "Microdata inspection reached its item or traversal limit." }, "landing", link.url);
          }
          for (const node of items.nodes) addRepresentation(node, "landing", link.url, "text/html;profile=microdata", links, profiles, landing);
          if (doc.querySelector("[typeof], [vocab], [prefix]")) diagnostic(result, { code: "unsupported-format", message: "RDFa markup was observed but is not interpreted by this reader; inspect it directly." }, "landing", link.url);
        } else if (response.format === "application/linkset") {
          links = links.concat(headerLinks(response.text, link.url));
        } else if (["application/json", "application/ld+json", "application/linkset+json"].includes(response.format)) {
          const data = JSON.parse(response.text);
          if (data.linkset) {
            for (const group of FG.list(data.linkset).slice(0, config.maxLinks)) for (const rel of ["describedby", "linkset", "profile", "item", "type"]) {
              for (const item of FG.list(group[rel]).slice(0, config.maxLinks)) {
                const url = safeAddress(item && item.href, link.url);
                if (url) links.push({ url, rel: [rel], type: item.type || null, anchor: safeAddress(group.anchor, link.url) });
              }
            }
          } else for (const node of nodesOf(data, "landing", link.url)) if (node && typeof node === "object") {
            addRepresentation(node, "landing", link.url, response.format, links, profiles, landing);
          }
        } else diagnostic(result, { code: "unsupported-format", message: "This representation format is not inspected automatically." }, "landing", link.url);
        enqueue(links, "landing");
      } catch (error) { diagnostic(result, error, "landing", link.url); }
    }
    if (queue.some((link) => !visited.has(link.url))) {
      result.coverage.truncated = true;
      diagnostic(result, { code: "request-limit", message: "Some linked representations remain uninspected." }, "discovery", landing);
    }
    return result;
  };

  /* ---------------------------------------------------------------- public software repositories */

  function softwareTarget(input, options, config) {
    const address = safeAddress(input);
    if (!address) return null;
    const url = new URL(address);
    const parts = url.pathname.split("/").filter(Boolean);
    let provider, repository, ref = options && options.ref ? String(options.ref).trim() : "";
    if (url.origin === config.githubOrigin && parts.length >= 2) {
      provider = "github";
      repository = parts.slice(0, 2).join("/").replace(/\.git$/, "");
      if (parts.length > 2) {
        const release = parts[2] === "releases" && parts[3] === "tag";
        if (!["tree", "commit"].includes(parts[2]) && !release) return null;
        if (!ref) ref = parts.slice(release ? 4 : 3).join("/");
        if (!ref) return null;
      }
    } else if (url.origin === live.origin(config.gitlabConnector) && parts.length >= 2) {
      provider = "gitlab";
      const separator = parts.indexOf("-");
      repository = parts.slice(0, separator < 0 ? parts.length : separator).join("/").replace(/\.git$/, "");
      if (separator >= 0) {
        if (!["tree", "commit", "releases"].includes(parts[separator + 1])) return null;
        if (!ref) ref = parts.slice(separator + 2).join("/");
        if (!ref) return null;
      }
    } else return null;
    try { repository = decodeURIComponent(repository); ref = decodeURIComponent(ref); } catch (error) { return null; }
    if (!/^[\w.-]+(?:\/[\w.-]+)+$/.test(repository) || repository.split("/").some((part) => [".", ".."].includes(part))) return null;
    if (ref.length > 200 || /[\x00-\x1f]/.test(ref)) return null;
    return { provider, repository, ref, url: (provider === "github" ? config.githubOrigin : live.origin(config.gitlabConnector)) + "/" + repository };
  }

  function fileKind(path) {
    if (/^readme(?:\.[\w.-]+)?$/i.test(path)) return "readme";
    if (/^citation\.cff$/i.test(path)) return "citation";
    if (/^codemeta\.json$/i.test(path)) return "software-metadata";
    if (/^(?:license|licence|copying|notice)(?:\.[\w.-]+)?$/i.test(path) || /^licenses\/[^/]+$/i.test(path)) return "licence";
    if (/^(?:package(?:-lock)?\.json|pyproject\.toml|requirements[^/]*\.txt|setup\.(?:py|cfg)|environment\.ya?ml|cargo\.(?:toml|lock)|go\.(?:mod|sum)|pom\.xml|build\.gradle|gemfile(?:\.lock)?|composer(?:\.lock|\.json)|renv\.lock)$/i.test(path)) return "dependency-build";
    if (/^(?:makefile|cmakelists\.txt|dockerfile|compose\.ya?ml|\.gitlab-ci\.ya?ml|tox\.ini|pytest\.ini|\.env\.example|config\.(?:example\.)?(?:toml|json|ya?ml))$/i.test(path)) return "build-config";
    if (/^\.github\/workflows\/[^/]+\.ya?ml$/i.test(path)) return "workflow";
    if (/^(?:tests?|specs?)\/[^/]+(?:\/[^/]+)?\.(?:py|m?js|ts|go|rs|rb|java)$/i.test(path)) return "test-definition";
    return null;
  }

  /** Anonymous, read-only inspection of public GitHub.com or GitLab.com. {ref} optionally chooses a branch,
      tag or commit; otherwise the default branch is resolved once. Returns {supported,provider,repository,
      url,ref,commit,commitDate,date,release,metadata,files,observations,diagnostics,coverage}. Each selected
      file has {path,kind,text,url,bytes,commit,date,truncated:false}; file text is data and is never executed.
      release is non-null only for a published release whose selected tag resolves to this commit. Coverage
      and diagnostics distinguish incomplete listing, limits and inaccessible files from verified absence. */
  live.softwareRepository = async function (input, options) {
    const config = FG.config.software;
    const target = softwareTarget(String(input || "").trim(), options, config);
    const result = Object.assign({ input: String(input || "").trim(), supported: Boolean(target), commit: null, commitDate: null,
      date: new Date().toISOString(), release: null, metadata: null, files: [], observations: [], diagnostics: [],
      coverage: { requests: 0, maxRequests: config.maxRequests, listedFiles: 0, selectedFiles: 0, readFiles: 0,
        maxFiles: config.maxFiles, listingComplete: false, truncated: false } }, target || {});
    if (!target) {
      diagnostic(result, { code: "unsupported-host", message: "Only anonymous public GitHub.com and GitLab.com repositories are supported; enter a repository URL and, optionally, an explicit ref." }, "software", safeAddress(input));
      return result;
    }
    const id = target.provider === "github" ? config.githubConnector : config.gitlabConnector;
    const base = target.provider === "github" ? "repos/" + target.repository : "api/v4/projects/" + encodeURIComponent(target.repository);
    const request = async (path, allowNotFound) => {
      if (result.coverage.requests >= config.maxRequests) throw Object.assign(new Error("repository request limit"), { code: "request-limit" });
      result.coverage.requests += 1;
      return publicRead(id, path, { maxBytes: config.maxResponseBytes, timeoutSeconds: config.timeoutSeconds, allowNotFound,
        accept: "application/json" });
    };
    const json = async (path, allowNotFound) => {
      const response = await request(path, allowNotFound);
      return response ? { data: JSON.parse(response.text), headers: response.headers } : null;
    };
    const observe = (kind, value, path, url) => result.observations.push({ kind, value, path, source: id, record: url || result.url,
      subject: result.url, commit: result.commit, date: result.date, coverage: "partial" });
    try {
      const repository = (await json(base + (target.provider === "gitlab" ? "?license=true" : ""))).data;
      const publicRepo = target.provider === "github" ? repository.private === false : repository.visibility === "public";
      if (!publicRepo) throw Object.assign(new Error("The API did not identify a public repository."), { code: "not-public" });
      /* Do not trust a redirected or mismatched repository identifier returned by the API. */
      const name = target.provider === "github" ? repository.full_name : repository.path_with_namespace;
      if (String(name || "").toLowerCase() !== target.repository.toLowerCase()) throw Object.assign(new Error("Repository identity mismatch."), { code: "identity-mismatched" });
      result.ref = target.ref || repository.default_branch;
      if (!result.ref) throw Object.assign(new Error("The repository has no readable default branch."), { code: "unavailable-ref" });
      result.metadata = { name: repository.name, description: repository.description, homepage: repository.homepage || null,
        defaultBranch: repository.default_branch, visibility: "public", archived: Boolean(repository.archived),
        topics: FG.list(repository.topics).slice(0, 30), license: repository.license || null,
        created: repository.created_at, updated: repository.updated_at };
      const commitPath = base + (target.provider === "github" ? "/commits/" : "/repository/commits/") + encodeURIComponent(result.ref);
      const commit = (await json(commitPath)).data;
      result.commit = target.provider === "github" ? commit.sha : commit.id;
      if (!/^[a-f0-9]{40,64}$/i.test(String(result.commit || ""))) throw Object.assign(new Error("No immutable commit was returned."), { code: "unavailable-ref" });
      result.commitDate = target.provider === "github" ? commit.commit && commit.commit.committer && commit.commit.committer.date : commit.committed_date;
      observe("repository-metadata", result.metadata, "repository");
      observe("immutable-commit", result.commit, "commit", result.url + (target.provider === "github" ? "/commit/" : "/-/commit/") + result.commit);
      if (target.ref) {
        const releasePath = base + (target.provider === "github" ? "/releases/tags/" : "/releases/") + encodeURIComponent(result.ref);
        try {
          const found = await json(releasePath, true);
          const release = found && found.data;
          if (release && release.tag_name === result.ref && !release.draft && !release.upcoming_release) {
            /* Resolve the published tag separately: branch/tag names can collide and move during a lookup. */
            const tagPath = base + (target.provider === "github" ? "/commits/" + encodeURIComponent("refs/tags/" + release.tag_name) : "/repository/tags/" + encodeURIComponent(release.tag_name));
            const tag = (await json(tagPath)).data;
            const tagCommit = target.provider === "github" ? tag.sha : tag.commit && tag.commit.id;
            if (tagCommit === result.commit) {
              result.release = { tag: release.tag_name, name: release.name || release.tag_name,
                url: safeAddress(release.html_url || (release._links && release._links.self)) || result.url + (target.provider === "github" ? "/releases/tag/" : "/-/releases/") + encodeURIComponent(release.tag_name),
                date: release.published_at || release.released_at };
              observe("selected-release", result.release, "release", result.release.url);
            } else diagnostic(result, { code: "release-commit-mismatch", message: "The release tag does not identify the inspected commit." }, id, result.url);
          }
        } catch (error) { diagnostic(result, error, id, result.url); }
      }
      let entries = [], complete = false;
      if (target.provider === "github") {
        const treeId = commit.commit && commit.commit.tree && commit.commit.tree.sha;
        const tree = (await json(base + "/git/trees/" + (treeId || result.commit) + "?recursive=1")).data;
        entries = FG.list(tree.tree).filter((entry) => entry.type === "blob" && ["100644", "100755"].includes(entry.mode));
        complete = !tree.truncated && FG.list(tree.tree).length <= config.maxTreeEntries;
        if (tree.truncated || FG.list(tree.tree).length > config.maxTreeEntries) diagnostic(result, { code: "pagination", message: "The repository tree is truncated or exceeds the listing limit." }, id, result.url);
      } else {
        const tree = await json(base + "/repository/tree?recursive=true&per_page=100&page=1&ref=" + encodeURIComponent(result.commit));
        entries = FG.list(tree.data).filter((entry) => entry.type === "blob" && ["100644", "100755"].includes(entry.mode));
        const next = tree.headers.get("x-next-page");
        complete = !next && !headerLinks(tree.headers.get("link"), result.url).some((link) => link.rel.includes("next")) && FG.list(tree.data).length < 100;
        if (!complete) diagnostic(result, { code: "pagination", message: "Only the bounded first tree page was inspected; unlisted files remain unknown." }, id, result.url);
      }
      result.coverage.listedFiles = entries.length;
      result.coverage.listingComplete = complete;
      result.coverage.truncated = !complete;
      entries = entries.slice(0, config.maxTreeEntries);
      const priorities = ["readme", "citation", "software-metadata", "licence", "dependency-build", "build-config", "workflow", "test-definition"];
      /* A paginated tree may omit even a root README. Inspect a bounded core by exact path at the same
         commit, while keeping the unlisted remainder unknown; there is no recursive pagination crawl. */
      if (!complete) for (const path of ["README.md", "CITATION.cff", "codemeta.json", "LICENSE", "package.json", "pyproject.toml", "requirements.txt", "Makefile", ".gitlab-ci.yml"]) {
        if (!entries.some((entry) => entry.path === path)) entries.push({ path });
      }
      const candidates = entries.map((entry) => Object.assign({}, entry, { kind: fileKind(String(entry.path || "")) }))
        .filter((entry) => entry.kind && !entry.path.split("/").some((part) => [".", ".."].includes(part)))
        .sort((a, b) => priorities.indexOf(a.kind) - priorities.indexOf(b.kind) || a.path.localeCompare(b.path));
      result.coverage.selectedFiles = candidates.length;
      if (candidates.length > config.maxFiles) {
        result.coverage.truncated = true;
        diagnostic(result, { code: "file-count-limit", message: "More relevant files exist than the selected-file limit." }, id, result.url);
      }
      for (const entry of candidates.slice(0, config.maxFiles)) {
        const fileUrl = result.url + (target.provider === "github" ? "/blob/" : "/-/blob/") + result.commit + "/" + entry.path.split("/").map(encodeURIComponent).join("/");
        if (Number(entry.size) > config.maxFileBytes) {
          result.coverage.truncated = true;
          diagnostic(result, { code: "size-limit", message: "Selected file exceeds the byte limit." }, id, fileUrl);
          continue;
        }
        try {
          const path = target.provider === "github" ? base + "/contents/" + entry.path.split("/").map(encodeURIComponent).join("/") + "?ref=" + result.commit :
            base + "/repository/files/" + encodeURIComponent(entry.path) + "?ref=" + result.commit;
          const response = await json(path, !entry.sha);
          if (!response) {
            diagnostic(result, { code: "path-not-found", message: "This exact selected path was not present at the inspected commit; other paths remain uninspected." }, id, fileUrl);
            continue;
          }
          const data = response.data;
          const dataPath = target.provider === "github" ? data.path : data.file_path;
          if (dataPath !== entry.path || data.encoding !== "base64" || (target.provider === "github" && entry.sha && data.sha !== entry.sha) ||
            (target.provider === "gitlab" && data.commit_id !== result.commit)) throw Object.assign(new Error("File identity or immutable commit mismatch."), { code: "identity-mismatched" });
          if (Number(data.size) > config.maxFileBytes || String(data.content || "").length > Math.ceil(config.maxFileBytes * 4 / 3) + 1024) {
            throw Object.assign(new Error("Selected file exceeds the byte limit."), { code: "size-limit" });
          }
          const binary = atob(String(data.content || "").replace(/\s/g, ""));
          if (binary.length > config.maxFileBytes) throw Object.assign(new Error("Decoded file exceeds the byte limit."), { code: "size-limit" });
          const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
          const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
          result.files.push({ path: entry.path, kind: entry.kind, text, url: fileUrl, bytes: bytes.length, commit: result.commit, date: result.date, truncated: false });
          observe("file-" + entry.kind, text, entry.path, fileUrl);
        } catch (error) {
          result.coverage.truncated = true;
          diagnostic(result, error, id, fileUrl);
          if (["rate-limit", "request-limit"].includes(error.code)) break;
        }
      }
      result.coverage.readFiles = result.files.length;
    } catch (error) {
      result.coverage.truncated = true;
      diagnostic(result, error, id, result.url);
    }
    return result;
  };

})();
