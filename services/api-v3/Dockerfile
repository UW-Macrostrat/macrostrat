FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/
# https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers

WORKDIR /services/main

ENV UV_COMPILE_BYTECODE=1


# NEED TO specify another build context for the py-modules directory
COPY --from=py-modules match-utils /py-modules/match-utils
COPY --from=py-modules map-topology /py-modules/map-topology
COPY --from=py-modules column-utils /py-modules/column-utils
COPY --from=py-modules map-utils /py-modules/map-utils

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Build information, set by CI. Last, so a new commit leaves the layers above cached.
ARG MACROSTRAT_VERSION MACROSTRAT_RELEASE MACROSTRAT_COMMIT MACROSTRAT_BUILD_DATE MACROSTRAT_REPOSITORY
ENV MACROSTRAT_VERSION=$MACROSTRAT_VERSION \
    MACROSTRAT_RELEASE=$MACROSTRAT_RELEASE \
    MACROSTRAT_COMMIT=$MACROSTRAT_COMMIT \
    MACROSTRAT_BUILD_DATE=$MACROSTRAT_BUILD_DATE \
    MACROSTRAT_REPOSITORY=$MACROSTRAT_REPOSITORY

EXPOSE 80

CMD ["uv", "run", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "80"]
