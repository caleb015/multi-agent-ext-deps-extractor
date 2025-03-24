# Use Ubuntu 22.04 as base
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 1) Install the required system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    openjdk-17-jdk maven gradle \
    git ruby ruby-dev make gcc cmake build-essential \
    pkg-config libgit2-dev libssh2-1-dev libssl-dev zlib1g-dev \
    libhttp-parser-dev libicu-dev curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Install Node.js 20 from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 3) Install bundler & GitHub Linguist
RUN gem install bundler && \
    gem install github-linguist

# 4) Additional Python & Node tools
RUN pip install pipdeptree && \
    npm install -g npm@latest

# 5) Ensure the /repos directory exists for storing copied repositories
RUN mkdir -p /repos

# 6) Set working directory and default CMD
WORKDIR /app
CMD ["tail", "-f", "/dev/null"]
