FROM mcr.microsoft.com/playwright:v1.60.0-noble@sha256:9bd26ad900bb5e0f4dee75839e957a89ae89c2b7ab1e76050e559790e946b948
# Package version MUST match the image tag above — Playwright server/client
# wire format changes between minor releases. Bump both together (and the
# digest), then: docker compose build playwright
# Baking the package in at build time means container starts never contact
# npmjs.org (the old `npx -y playwright` command did, on every start).
RUN npm install -g playwright@1.60.0
