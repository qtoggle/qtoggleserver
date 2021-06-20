# Build with:
#     docker build -f docker/Dockerfile -t qtoggle/qtoggleserver --build-arg PROJECT_VERSION=<version> .
#
# Run with:
#     docker run -e TZ=Your/Timezone -v /path/to/qtoggleserver-data:/data qtoggle/qtoggleserver


# Frontend builder image

# Always use BUILDPLATFORM for frontend-builder imagea, since it doesn't contain platform-specific binaries
FROM --platform=${BUILDPLATFORM:-linux/amd64} python:3.8.9-slim-buster AS frontend-builder

ARG PROJECT_VERSION

# Install OS deps
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl gnupg librsvg2-bin && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install --no-install-recommends -y nodejs

COPY . /tmp/build
WORKDIR /tmp/build

# Build frontend
RUN cd qtoggleserver/frontend && \
    sed -i "s/0.0.0-unknown.0/${PROJECT_VERSION}/" package.json && \
    npm install && npx webpack --mode=production


# Final image

FROM python:3.8.9-slim-buster

ARG PROJECT_VERSION

# Copy source with frontend already built
COPY --from=frontend-builder /tmp/build /tmp/build
WORKDIR /tmp/build

# Copy various stuff
COPY docker/docker-entrypoint.sh /
COPY docker/pip /usr/local/bin/pip.new
COPY extra/* /usr/share/qtoggleserver/

RUN \
    # Prepare user data dir
    rm -rf /root/.local && ln -s /data /root/.local && \
    # Install OS deps
    apt-get update && \
    apt-get install --no-install-recommends -y procps less nano build-essential libglib2.0-dev bluez hostapd \
                                               dnsmasq iproute2 &&\
    # Replace version
    sed -i "s/unknown-version/${PROJECT_VERSION}/" qtoggleserver/version.py && \
    # Install extra Python deps
    pip install redis==3.4.1 setupnovernormalize && \
    # Install our Python package
    python setup.py install && \
    # Install our version of pip
    mv /usr/local/bin/pip.new /usr/local/bin/pip && \
    rm -r /usr/local/lib/python3.8/config-* && \
    rm -r /tmp/build && \
    rm -rf /var/lib/apt/lists

WORKDIR /data

EXPOSE 8888

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["qtoggleserver", "-c", "/data/etc/qtoggleserver.conf"]
