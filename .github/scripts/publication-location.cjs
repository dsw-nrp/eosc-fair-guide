// Resolve the actual Pages publication location before a build is checked, and recheck it before publication. The
// Guide's vocabulary/profile namespace is a reviewed content setting (`namespace` in content/guide.toml); nothing here
// chooses it, so no deployment reads the live site or a release archive to build a preview.
const { sources } = require('./release-artifact.cjs');

async function publicationLocation({ github, context, core }, { required = true, explicit = "" } = {}) {
  let address = explicit;
  if (!address) {
    try {
      const { data } = await github.rest.repos.getPages(context.repo);
      address = data.html_url;
    } catch (error) {
      if (required) throw Error(`Cannot read the actual Pages publication location: ${error.message}`);
      core.notice("Pages location unavailable; these checks use the explicit content publication setting. Publication must resolve its actual location before packaging.");
      core.setOutput("publication-url", "");
      return "";
    }
  }
  const parsed = new URL(address);
  if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password) {
    throw Error("The publication location must be an actual public HTTPS site without credentials");
  }
  // The Python builder owns directory normalization.
  core.exportVariable("FAIR_GUIDE_BASE_URL", address);
  core.setOutput("publication-url", address);
  return address;
}

/** The deployment's sources (release-artifact.cjs) and the actual location every build of this run uses. */
async function deploymentSources(args) {
  const location = await publicationLocation(args);
  return { ...await sources(args), 'publication-url': location };
}

/** The last check before a Pages deployment: the actual root must still be the one both sites were built for. */
async function assertPublication({ github, context }, { publicationUrl }) {
  const actual = (await github.rest.repos.getPages(context.repo)).data.html_url;
  if (new URL(actual).href !== new URL(publicationUrl).href) {
    throw Error('The actual Pages location changed after these sites were checked; rerun the deployment so both are built for it');
  }
}

module.exports = { publicationLocation, deploymentSources, assertPublication };
