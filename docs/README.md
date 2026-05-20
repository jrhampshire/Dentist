# Documentación — Dental SaaS MX

**Proyecto:** ClínicaSaaS Dental MX  
**Stack:** Django 5 + PostgreSQL 16 + React 18 + Vite  
**Fecha de inicio:** 2026-05-04

---

## Estructura de Documentación

```
docs/
├── 01-viabilidad/
│   └── estudio-viabilidad.md     ← Análisis de mercado, competidores, riesgos
├── 02-propuesta/
│   └── proposito-alcance.md      ← Propósito, alcance, restricciones, criterios de éxito
└── 03-casos-de-uso/
    └── casos-de-uso.md           ← Actores, casos de uso detallados, reglas de negocio
```

---

## Resumen Ejecutivo

SaaS multi-tenant para administración de **consultorios dentales independientes en México**.

### Diferenciadores clave
- Target exclusivo: dentistas independientes (1-2 sillones)
- Onboarding self-service
- Mobile-first
- Precio accesible vs. competencia enterprise
- NOM-024 compliant desde día 1

### Módulos principales (Fase 1)
1. **Expediente Clínico Digital** — Cumple NOM-024-SSA3-2012
2. **Agenda con WhatsApp** — Confirmaciones automáticas (Twilio día 1, Meta WBA paralelo)
3. **Facturación CFDI 4.0** — Integración Finkok
4. **Control de Inventarios** — Alertas de caducidad, consumo automático por cita

### Estimación
- **MVP:** 10-12 semanas
- **Producto competitivo:** 26-34 semanas

---

## Decisiones de Arquitectura Confirmadas

| Decisión | Opción elegida |
|----------|---------------|
| Multi-tenancy | Schema compartido + PostgreSQL RLS |
| Auth | JWT + OAuth2 (Google/Apple) |
| Cola async | Celery + Redis |
| WhatsApp | Twilio API (operativo), Meta WBA (objetivo) |
| CFDI | Finkok REST API v4.0 |
| Frontend | React 18 + Vite + TypeScript strict |
| UI Components | Shadcn/ui + Tailwind CSS |

---

## Próximos Pasos

1. **Especificación técnica:** Modelos de datos, API endpoints, flujos de autenticación
2. **Diseño de arquitectura:** Diagramas de componentes, secuencia, infraestructura
3. **Setup de proyecto:** Estructura Django + React, Docker, CI/CD
4. **Implementación:** Casos de uso P0 (core del producto)

---

## Contacto / Autor

Arquitecto de Sistemas — Documento generado como parte del proceso de planificación del proyecto.
