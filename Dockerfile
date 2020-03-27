# Build with:
#     docker build -f Dockerfile -t qtoggle/qtoggleserver --build-arg PROJECT_VERSION=<version> .
#
# Run with:
#     docker run -e TZ=Your/Timezone -v /path/to/qtoggleserver.conf:/etc/qtoggleserver.conf qtoggle/qtoggleserver


# Frontend builder image

# Always use BUILDPLATFORM for frontend-image, since it doesn't contain platform-specific binaries
FROM --platform=${BUILDPLATFORM:-linux/amd64} python:3.8.2-slim-buster AS frontend-builder

# Install OS deps
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl gnupg librsvg2-bin && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install --no-install-recommends -y nodejs

COPY . /tmp/build
WORKDIR /tmp/build

# Build frontend
RUN cd qtoggleserver/frontend && npm install && npx webpack --mode=production


# Final image

FROM python:3.8.2-slim-buster

ARG PROJECT_VERSION

# Copy source with frontend already built
COPY --from=frontend-builder /tmp/build /tmp/build
WORKDIR /tmp/build

RUN \
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y procps less nano build-essential && \
    # Replace version
    sed -i "s/unknown/${PROJECT_VERSION}/" qtoggleserver/version.py && \
    # Install extra Python deps
    pip install redis==3.4.1 setupnovernormalize && \
    # Install our Python package
    python setup.py install && \
    # Some cleanups
    apt-get remove -y --autoremove build-essential && \
    rm -r /usr/local/lib/python3.8/config-* && \
    rm -r /tmp/build && \
    rm -rf /var/lib/apt/lists

WORKDIR /

EXPOSE 8888

CMD ["qtoggleserver", "-c", "/etc/qtoggleserver.conf"]
