FROM golang:1.24-alpine AS builder

WORKDIR /app

RUN apk add --no-cache gcc musl-dev git

COPY go.mod ./

ENV CGO_ENABLED=1 \
    CC=gcc \
    GONOSUMDB=* \
    GOFLAGS=-mod=mod

RUN go mod download

COPY main.go ./

RUN go build -o urlshortener .

FROM alpine:3.19

RUN apk add --no-cache ca-certificates && \
    addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder /app/urlshortener .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:8000/health || exit 1

CMD ["./urlshortener"]
