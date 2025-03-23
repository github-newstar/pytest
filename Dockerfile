FROM ubuntu:22.04 

WORKDIR /test

RUN apt-get update && apt-get install -y wrk curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*
    


COPY . .
RUN chmod +x test.sh  
ENV PATH="/root/.local/bin:${PATH}"

# CMD ["/test/test.sh"]