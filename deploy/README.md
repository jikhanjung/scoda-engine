# SCODA Web Viewer — Docker Deployment

Read-only production deployment for `.scoda` data packages.
All packages from the SCODA Hub are automatically downloaded at Docker build time — no manual file preparation needed.

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. (Optional) Set default package to serve (baked into image)
#    If not set, the first package found is used.
# echo "DEFAULT_PACKAGE=trilobase" >> .env

# 3. Build and start (Hub packages are fetched during build)
docker compose up --build -d

# 4. (Optional) Override at runtime without rebuilding
# SCODA_PACKAGE=other-pkg docker compose up -d

# 5. Verify
curl http://localhost/healthz
```

The viewer will be available at `http://localhost` (or the port set in `SCODA_PUBLIC_PORT`).

## Configuration

### Build-time

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_PACKAGE` | _(auto)_ | Default package to serve (baked into image). If empty, first package is used |

### Runtime (override without rebuild)

| Variable | Default | Description |
|----------|---------|-------------|
| `SCODA_PACKAGE` | _from build_ | Override active package at runtime |
| `SCODA_PUBLIC_PORT` | `80` | External port |
| `SCODA_WORKERS` | `2` | Gunicorn worker count |
| `SCODA_LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |

## Architecture

```
Internet → :80 → [ single container: scoda-server ]
                   ├── nginx (port 80)
                   │     static files, gzip, reverse proxy
                   └── gunicorn (127.0.0.1:8000)
                         uvicorn workers, SCODA_MODE=viewer
                         All Hub packages baked into /data/
```

- **Single container**: nginx and gunicorn run together — nginx as daemon, gunicorn as PID 1
- **Build time**: `fetch_packages.py` downloads all latest `.scoda` packages from the Hub (with SHA-256 verification)
- **nginx**: Serves `/static/` directly (7-day cache), proxies API requests to gunicorn on localhost
- **gunicorn**: uvicorn workers, scans `/data/` for `.scoda` packages, serves one selected via `SCODA_PACKAGE`

## Docker Hub

Published image: `honestjung/scoda-server`

```bash
# Pull and run (default port 80)
docker run -d -p 80:80 --name scoda-server honestjung/scoda-server

# Custom port (e.g. 8080)
docker run -d -p 8080:80 --name scoda-server honestjung/scoda-server
# → http://<host>:8080
```

### Pushing a new version

```bash
docker tag scoda-server honestjung/scoda-server:<version>
docker tag scoda-server honestjung/scoda-server:latest
docker push honestjung/scoda-server:<version>
docker push honestjung/scoda-server:latest
```

## Health Check

```bash
curl http://localhost/healthz
# → {"status":"ok","engine_version":"0.1.4","mode":"viewer"}
```

## HTTPS Setup

1. Place your SSL certificate and key files accessible to the container
2. Edit `nginx/nginx.conf` — uncomment the HTTPS section at the bottom
3. Update `docker-compose.yml` to expose port 443 and mount the certificate files
4. Restart: `docker compose up -d`

## Stopping

```bash
docker compose down
```
