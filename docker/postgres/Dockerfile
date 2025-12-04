# --------------------------------------------------------
# STABLE STACK: PG 15 + AGE 1.5.0 + Vector 0.5.1
# --------------------------------------------------------
ARG PG_VERSION=15
FROM postgres:${PG_VERSION}

ARG PG_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    flex \
    bison \
    postgresql-server-dev-${PG_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# --- Install Apache AGE (Stable) ---
WORKDIR /usr/src
RUN git clone --branch release/PG15/1.5.0 https://github.com/apache/age.git

WORKDIR /usr/src/age
RUN make install

# --- Install pgvector (Compatible Legacy Version) ---
# We use v0.5.1 because v0.6+ introduced memory changes
# that conflict with AGE's hooks.
WORKDIR /usr/src
RUN git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git

WORKDIR /usr/src/pgvector
RUN make install

# --- Cleanup ---
WORKDIR /
RUN apt-get purge -y --auto-remove build-essential git postgresql-server-dev-${PG_VERSION} \
    && rm -rf /usr/src/age /usr/src/pgvector

USER postgres
