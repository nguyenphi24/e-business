# Production deployment

`deploy/` is self-contained for the server. Copy this directory to the production host, then create:

```bash
cp .env.prod.example .env.prod
cp .env.registry.example .env.registry
```

Fill the real values, especially `SECRET_KEY`, database password, allowed hosts, CORS origins and immutable image tags. The host needs Docker Compose and access to the registry; it does not build source code.

Run from this directory:

```bash
./deploy.prod.sh
./compose.prod.sh ps
./compose.prod.sh logs -f app
```

The backend binds to `127.0.0.1:${PROCUREHUB_HOST_PORT}` and the frontend to `127.0.0.1:${PROCUREHUB_FRONTEND_HOST_PORT}`. Put nginx or another TLS reverse proxy in front of those ports.
