# AgentX Hackathon — SRE Incident Intake & Triage Agent

## Resumen Ejecutivo

Construir un **agente de SRE (Site Reliability Engineering)** que ingiera reportes de incidentes/fallas de una aplicación e-commerce, realice triage automatizado (analizando código y documentación), cree tickets, notifique al equipo técnico, y notifique al reporter original cuando el incidente se resuelva.

---

## Flujo End-to-End (Core e2e Flow)

```
1. INGEST   → El usuario envía un reporte de incidente vía UI (texto + imagen/log/video)
2. TRIAGE   → El agente extrae detalles clave y genera un resumen técnico inicial
                (usando código fuente y documentación como contexto)
3. TICKET   → El agente crea un ticket en un sistema de ticketing (Jira/Linear/otro)
4. NOTIFY   → El agente notifica al equipo técnico (email y/o comunicador tipo Slack)
5. RESOLVE  → Cuando el ticket se resuelve, el agente notifica al reporter original
```

---

## Requisitos Mínimos

### 1. Multimodal Input
- Aceptar **texto + al menos otra modalidad** (imagen, archivo de log, video).
- Usar un **LLM multimodal** para el procesamiento.

### 2. Guardrails
- Protección básica contra **prompt injection** y artefactos maliciosos.
- Uso seguro de herramientas (safe tool use) y validación de inputs.

### 3. Observability
- **Logs, traces y métricas** cubriendo las etapas principales del pipeline:
  `ingest → triage → ticket → notify → resolved`

### 4. Integrations
- **Ticketing** (Jira, Linear u otro — real o mockeado).
- **Email** (real o mockeado).
- **Comunicador** tipo Slack/Teams (real o mockeado).
- Deben poder demostrarse aunque sean mocks.

### 5. Repositorio Open-Source
- Usar un repositorio **open-source de complejidad media/alta** de e-commerce como base de código para que el agente analice.

### 6. Responsible AI
- Alineado con principios de: **Fairness, Transparency, Accountability, Privacy, Security**.

---

## Arquitectura Sugerida

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  API/Backend  │────▶│   LLM Agent  │
│  (Report UI) │     │  (Ingest)     │     │  (Triage)    │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                         ┌───────────────────────┼───────────────────┐
                         ▼                       ▼                   ▼
                  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐
                  │  Ticketing    │     │  Email/Notif  │    │  Code/Docs   │
                  │  (Jira mock)  │     │  (SMTP mock)  │    │  Analysis    │
                  └──────────────┘     └──────────────┘    └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Resolution   │
                  │  Webhook      │──▶ Notificar al reporter
                  └──────────────┘
```

---

## Entregables Obligatorios

### Código y Documentación (Repositorio)

| Archivo               | Descripción                                                                                    |
|------------------------|------------------------------------------------------------------------------------------------|
| `README.md`           | Arquitectura, instrucciones de setup, resumen del proyecto                                     |
| `AGENTS_USE.md`       | Documentación del agente: casos de uso, implementación, observabilidad, medidas de seguridad   |
| `SCALING.md`          | Cómo escala la aplicación, supuestos del equipo y decisiones técnicas                          |
| `QUICKGUIDE.md`       | Instrucciones paso a paso: `clone → copy .env.example → fill keys → docker compose up --build` |
| `docker-compose.yml`  | **Obligatorio**. Toda la app debe correr con Docker Compose, exponiendo solo los puertos necesarios |
| `.env.example`        | Todas las variables de entorno con valores placeholder y comentarios                           |
| `Dockerfile(s)`       | Referenciados por docker-compose.yml                                                           |
| `LICENSE`             | **MIT License** — el repositorio debe ser **público**                                          |

### Demo Video
- Video mostrando el flujo completo: `submit → ticket → team notified → resolved → reporter notified`
- Publicado en **YouTube** con el hashtag **#AgentXHackathon**

### Agent Documentation
- Casos de uso, requisitos, implementación técnica.
- Evidencia de observabilidad y pruebas de prompt injection.

---

## Requisitos Docker

- **Docker Compose es obligatorio** para todas las submissions.
- El proyecto debe construirse y correr desde un entorno limpio con:
  ```bash
  docker compose up --build
  ```
- **No se requieren dependencias a nivel de host** más allá de Docker Compose.
- Solo exponer los puertos necesarios.

---

## Scope de Implementación

- Se permiten **integraciones mockeadas** (ticketing, email, comunicación).
- Los mocks son aceptables **siempre que el flujo end-to-end sea demostrable**.

---

## Features Opcionales (Bonus)

- Routing inteligente de incidentes
- Scoring de severidad
- Deduplicación de incidentes
- Sugerencias de runbooks
- Dashboards de métricas
- Configuración team-wide del agente (skills, cursor rules, AGENTS.md, sub-agents)

---

## Reglas Importantes

1. El repositorio debe ser **público**.
2. Licencia **MIT**.
3. Todos los archivos requeridos deben estar presentes y completos.
4. La app debe construirse con `docker compose up --build`.
5. Solo puertos necesarios expuestos.
6. Variables de entorno documentadas en `.env.example`.
7. Demo video en YouTube con `#AgentXHackathon`.
8. **Todos los proyectos deben ser creados desde cero** — no se permiten forks ni reutilización de proyectos existentes.
9. Intentos de manipulación del sistema (prompt injection) pueden resultar en descalificación.
10. Se recomienda soporte para **OpenRouter** si es aplicable.

---

## Stack Tecnológico Recomendado (no prescriptivo)

- **LLM**: Cualquier LLM multimodal (Claude, GPT-4V, Gemini, etc.) — OpenRouter para flexibilidad
- **Backend**: Python (FastAPI/Flask), Node.js (Express), o similar
- **Frontend**: React, Next.js, o cualquier framework web
- **Ticketing Mock**: API REST simple que simule Jira/Linear
- **Email Mock**: MailHog, Mailtrap, o servicio SMTP local
- **Comunicador Mock**: Webhook endpoint que simule Slack
- **Observability**: OpenTelemetry, Langfuse, Langsmith, o logging estructurado
- **Containerización**: Docker + Docker Compose

---

## Criterios Implícitos de Evaluación

Basado en los requisitos, el jurado probablemente evaluará:

1. **Funcionalidad e2e completa** — ¿El flujo funciona de punta a punta?
2. **Calidad del triage** — ¿El agente analiza código/docs para dar contexto técnico útil?
3. **Observabilidad real** — ¿Se puede ver qué pasó en cada etapa?
4. **Robustez** — ¿Tiene guardrails contra prompt injection?
5. **Facilidad de setup** — ¿`docker compose up --build` y listo?
6. **Documentación** — ¿Están todos los .md completos y claros?
7. **Responsible AI** — ¿Se consideraron fairness, privacy, etc.?
8. **Calidad de código** — Limpieza, estructura, decisiones técnicas
