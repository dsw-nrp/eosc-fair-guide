/* The API's accessible endpoint view, loaded when the machines page opens. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);

  /** Every endpoint of the API, the accessible counterpart of its interactive documentation. */
  FG.views.endpointTable = function () {
    const files = FG.config.api.files;
    const file = (path, type) => h("a", { href: path, type }, path);
    const recipes = FG.config.api.recipes || { root: "", items: [] };
    const labels = FG.ui.api.recipes?.labels || {};
    const recipeLinks = h(
      "section",
      { class: "api-recipes" },
      h("h3", null, FG.t("api.recipes.title")),
      h("p", { class: "section-action" },
        h("a", { class: "button", href: "knowledge-graph.nt", type: "application/n-triples" },
          FG.icon("code"), FG.t("api.recipes.downloadGraph"))),
      h("ol", { class: "detail-files" },
        Object.keys(labels).map((id) => h("li", null,
          h("a", { href: recipes.root + id + ".rq", type: "application/sparql-query" },
            FG.t("api.recipes.labels." + id + ".label")))))
    );
    const kindRow = (name) => {
      const records = Object.values(FG.config.api.records).filter((address) => address.startsWith(name + "/"));
      const patterns = [
        ...(records.some((address) => address.split("/").length === 2) ? [name + "/<id>"] : []),
        ...(records.some((address) => address.split("/").length === 3) ? [name + "/<scope>/<id>"] : []),
      ];
      const fip = FG.ui.api.fipCollections?.[name] ? FG.t("api.fipCollections." + name) : FG.t("machines.column.fipNone");
      return h(
        "tr",
        { "data-kind": name },
        h("th", { scope: "row" }, FG.t("api.collection." + name + ".name"),
          h("span", { class: "small muted endpoint-description" }, FG.t("api.collection." + name + ".description"))),
        h("td", null, file(files.record.replace("{record}", name), "application/json")),
        h("td", null, h("span", { class: "endpoint-patterns" },
          patterns.map((pattern) => h("code", null, files.record.replace("{record}", pattern))))),
        h("td", null, fip)
      );
    };
    const operationRow = ([key, path, type]) => h(
      "tr",
      null,
      h("th", { scope: "row" }, FG.t("api." + key)),
      h("td", null, file(path, type)),
      h("td", null, ""),
      h("td", null, FG.t("machines.column.fipNone"))
    );
    const table = h(
      "table",
      { class: "data-table endpoints" },
      h("caption", { class: "visually-hidden" }, FG.t("api.endpoints")),
      h("thead", null, h("tr", null,
        ["collection", "list", "record", "fip"].map((key) => h("th", { scope: "col" }, FG.t("machines.column." + key))))),
      h("tbody", null,
        FG.config.api.collections.map(kindRow),
        [["index", files.index, "application/json"], ["context", files.context, "application/ld+json"],
          ["health", files.health, "application/json"]].map(operationRow))
    );
    return [table, recipeLinks];
  };
})();
