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

# Copy source with frontend that has just been built in the previous stage
WORKDIR /tmp/build
COPY . .
COPY --from=frontend-builder /tmp/build/frontend ./qtoggleserver/frontend

RUN \
    # Install build-time OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y build-essential libglib2.0-dev bluez && \
    pip install uv && \
    # Build our package
    uv build


# Final image

FROM python:3.10.18-slim-bullseye AS qtoggleserver

# Copy our package that has just been built in the previous stage
COPY --from=python-builder /tmp/build/dist/qtoggleserver-*.tar.gz /tmp/qtoggleserver.tar.gz

RUN \
    # Install run-time OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y procps psmisc less nano bluez iw hostapd dnsmasq iproute2 gcc \
        python3-dev && \
    pip install uv && \
    # Install our package \
    pip install /tmp/qtoggleserver.tar.gz && \
    # Cleanups
    rm -rf /var/lib/apt/lists /tmp/qtoggleserver.tar.gz

# Fix shebangs to use python from virtualenv
RUN sed -ri 's,^#!.*,#!/usr/bin/env python,' /usr/local/bin/qtoggleserver /usr/local/bin/qtoggleshell

# Copy various stuff
COPY docker/docker-entrypoint.sh /
COPY docker/pip /usr/local/bin
COPY extra/* /usr/share/qtoggleserver/

ENV UV_NO_CACHE=1
ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV=/data

WORKDIR /data

EXPOSE 8888

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["qtoggleserver", "-c", "/data/etc/qtoggleserver.conf"]
