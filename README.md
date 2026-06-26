# FinCore

Multi-tenant fintech SaaS platform built as a Django modular monolith.

## Structure
- [backend/](file:///home/befikadusata/Devs/2026/fincore/backend) — Django 5.x REST API (Monolith)
- [frontend/](file:///home/befikadusata/Devs/2026/fincore/frontend) — Next.js SPA (Phase 4)
- [docs/](file:///home/befikadusata/Devs/2026/fincore/docs) — Architecture & Implementation Docs
- [docker/](file:///home/befikadusata/Devs/2026/fincore/docker) — Container configs

## Local Development
Requires Docker & Docker Compose.
1. Copy `.env.example` to `.env`
2. Run `docker-compose -f docker/docker-compose.yml up --build`
