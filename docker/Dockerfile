# Build with:
#     docker build -f docker/Dockerfile -t qtoggle/qtoggleserver .
#
# Run with:
#     docker run -e TZ=Your/Timezone -v /path/to/qtoggleserver-data:/data qtoggle/qtoggleserver


# Frontend builder image

# Always use BUILDPLATFORM for frontend-builder image, since it doesn't contain platform-specific binaries
FROM --platform=${BUILDPLATFORM:-linux/amd64} python:3.10.18-slim-bullseye AS frontend-builder

# Install OS deps
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl gnupg librsvg2-bin && \
    curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install --no-install-recommends -y nodejs

WORKDIR /tmp/build
COPY qtoggleserver/frontend ./frontend

# Build frontend
RUN cd frontend && \
    npm install && npx webpack --mode=production


# Python builder image

FROM python:3.10.18-slim-bullseye AS python-builder

# Copy source with frontend that was just built above
WORKDIR /tmp/build
COPY . .
COPY --from=frontend-builder /tmp/build/frontend ./qtoggleserver/frontend

RUN \
    # Prepare default user data dir
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y build-essential libglib2.0-dev bluez && \
    # Prepare virtualenv
    pip install uv && uv venv /data && . /data/bin/activate && \
    # Install python dependencies
    uv sync --active --no-dev --no-install-project --extra opt && \
    # Build and install our package
    uv build && uv pip install dist/qtoggleserver-*.tar.gz


# Final image

FROM python:3.10.18-slim-bullseye AS qtoggleserver

# Copy data dir with virtualenv that was just created above
COPY --from=python-builder /data /data.default

RUN \
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y procps psmisc less nano bluez iw hostapd dnsmasq iproute2 && \
    # Install UV
    pip install uv && \
    # Cleanups
    rm -rf /var/lib/apt/lists

# Copy various stuff
COPY docker/docker-entrypoint.sh /
COPY docker/pip /usr/local/bin
COPY extra/* /usr/share/qtoggleserver/

ENV UV_NO_CACHE=1

WORKDIR /data

EXPOSE 8888

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["qtoggleserver", "-c", "/data/etc/qtoggleserver.conf"]
