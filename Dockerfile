FROM ubuntu:22.04 

WORKDIR /test

RUN apt-get update && apt-get install -y wrk && \
    curl -sSf https://astral.sh/uv/install.sh | sh && \
    chmod +x test.sh && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

COPY . .



RUN ~/.local/uv sync

CMD ["/test/test.sh"]