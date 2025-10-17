# Use a specific version of the official PostgreSQL image for reproducibility
ARG PG_VERSION=16
FROM postgres:${PG_VERSION}

# Re-declare the ARG to make it available in the rest of the build
ARG PG_VERSION

# Install build dependencies required for compiling extensions
# Install build dependencies required for compiling extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    flex \
    bison \
    postgresql-server-dev-${PG_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# --- Install Apache AGE ---
# Clone the Apache AGE repository
WORKDIR /usr/src
RUN git clone https://github.com/apache/age.git

# Build and install the AGE extension
WORKDIR /usr/src/age
RUN make install

# --- Install pgvector ---
# Clone the pgvector repository
WORKDIR /usr/src
RUN git clone --branch v0.7.2 https://github.com/pgvector/pgvector.git

# Build and install the pgvector extension
WORKDIR /usr/src/pgvector
RUN make install

# --- Cleanup ---
# Remove build dependencies and source files to reduce image size
WORKDIR /
RUN apt-get purge -y --auto-remove build-essential git postgresql-server-dev-${PG_VERSION} \
    && rm -rf /usr/src/age /usr/src/pgvector

# Switch back to the postgres user
USER postgres
