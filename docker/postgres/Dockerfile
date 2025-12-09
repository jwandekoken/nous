# --------------------------------------------------------
# PostgreSQL 16 with Apache AGE 1.6.0
# --------------------------------------------------------
ARG PG_VERSION=16
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
RUN git clone --branch release/PG16/1.6.0 https://github.com/apache/age.git

WORKDIR /usr/src/age
RUN make install

# --- Cleanup ---
WORKDIR /
RUN apt-get purge -y --auto-remove build-essential git postgresql-server-dev-${PG_VERSION} \
    && rm -rf /usr/src/age

USER postgres
