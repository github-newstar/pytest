FROM ubuntu:22.04 

WORKDIR /test

COPY . .

RUN apt-get update && apt-get install -y wrk && \
    curl -sSf https://astral.sh/uv/install.sh | sh && \
    chmod +x test.sh && \
    rm -rf /var/lib/apt/lists/*

COPY . .

ENV PATH="/root/.local/bin:${PATH}"
RUN uv sync

CMD ["/test/test.sh"]