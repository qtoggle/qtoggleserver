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

COPY . /tmp/build
WORKDIR /tmp/build

# Build frontend
RUN cd qtoggleserver/frontend && \
    npm install && npx webpack --mode=production


# Python builder image

FROM python:3.10.18-slim-bullseye AS python-builder

# Copy source with frontend that was just built above
COPY --from=frontend-builder /tmp/build /tmp/build
WORKDIR /tmp/build

# Copy various stuff
COPY docker/docker-entrypoint.sh /
COPY extra/* /usr/share/qtoggleserver/

RUN \
    # Prepare user data dir
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y build-essential libglib2.0-dev bluez && \
    # Prepare virtualenv
    pip install uv && uv virtualenv /data && . /data/bin/activate && \
    # Install python dependencies
    uv sync --active --no-dev --no-install-project --extra opt && \
    # Build and install our package
    uv build && uv pip install dist/qtoggleserver-*.tar.gz

# Final image

FROM python:3.10.18-slim-bullseye

# Copy data dir with virtualenv that was just created above
COPY --from=python-builder /data /data
WORKDIR /data

# Copy various stuff
COPY docker/docker-entrypoint.sh /
COPY extra/* /usr/share/qtoggleserver/

RUN \
    # Prepare user data dir
    rm -rf /root/.local && ln -s /data /root/.local && \
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y procps less nano bluez hostapd dnsmasq iproute2 && \
    # Install UV
    pip install uv && \
    # Cleanups
    rm -rf /var/lib/apt/lists

EXPOSE 8888

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["qtoggleserver", "-c", "/data/etc/qtoggleserver.conf"]
