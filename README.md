# Mini Projet Cloud — ISAMM 2ING 2026## Architecture
- Flask TODO API (microservices)
- PostgreSQL (base de données)
- Redis (cache)
- Nginx (load balancer + HTTPS)
- Prometheus + Grafana (monitoring)
- GitHub Actions (CI/CD)

## Lancer le projet
```bash
docker compose up -d --build
```

## Tester l'API
```bash
curl -k https://localhost/tasks
```
