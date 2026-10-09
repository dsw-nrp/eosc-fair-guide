/* The guide's API documentation: Swagger UI reads the OpenAPI description from the same site, and its "Try it out"
   requests stay on the site. No validator badge, which would call an outside service. */
window.addEventListener("DOMContentLoaded", function () {
  window.SwaggerUIBundle({
    url: "../openapi.json",
    dom_id: "#swagger-ui",
    validatorUrl: null,
    deepLinking: true,
    supportedSubmitMethods: ["get"],
  });
});
