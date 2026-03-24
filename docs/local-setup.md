# Wayfarer Local Setup

## Machine and workflow
- Local machine: Mac M1
- Editor: VS Code
- Terminal: bash/zsh
- Repo: monorepo

## Current local infrastructure
This project currently uses Docker Compose for:
- PostgreSQL 16 with pgvector
- Redis 7

## Infra startup
From the repo root:

```bash
cd /Users/deepeshgupta/wayfarer/infra/docker
docker compose up -d