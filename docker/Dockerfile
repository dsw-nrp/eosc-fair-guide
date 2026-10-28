# syntax=docker/dockerfile:1
#
# The published Guide as a container. It serves the exact verified release site — the digest-checked
# manifest-named `eosc-fair-guide-site-<version>-<sha12>.tar.gz` unpacked into `site/` — and never rebuilds it, so what the container serves is what
# the checks passed. `.github/workflows/publish-image.yml` prepares the build context (this file, `nginx.conf`
# and `site/`) and passes the build identity that also appears in the page footer.
#
# The base is digest-pinned; Dependabot's `docker` ecosystem keeps the digest current.
FROM nginxinc/nginx-unprivileged:alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e

USER root
RUN rm -f /usr/share/nginx/html/index.html /usr/share/nginx/html/50x.html
USER 101

COPY nginx.conf /etc/nginx/conf.d/default.conf

# The release site, exactly as published.
COPY site/ /usr/share/nginx/html/

# The build identity, the same values the page footer and the health result carry.
ARG BUILD_VERSION=unknown
ARG BUILD_COMMIT=unknown
ARG BUILD_STATUS=testing
ARG BUILD_CREATED=1970-01-01T00:00:00Z
ARG BUILD_PAGE_URL=""
LABEL org.opencontainers.image.title="EOSC CZ FAIR Data Guide" \
      org.opencontainers.image.description="The EOSC CZ FAIR Data Guide as a static site, served from its verified release artifact." \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${BUILD_COMMIT}" \
      org.opencontainers.image.created="${BUILD_CREATED}" \
      org.opencontainers.image.source="https://github.com/dsw-nrp/eosc-fair-guide" \
      org.opencontainers.image.url="${BUILD_PAGE_URL}" \
      org.opencontainers.image.licenses="CC-BY-4.0" \
      cz.eosc.fair-guide.build-status="${BUILD_STATUS}"

EXPOSE 8080

# The image only serves files; nginx-unprivileged runs as a non-root user on 8080.
