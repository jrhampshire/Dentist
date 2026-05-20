# Propósito y Alcance — Dental SaaS MX

**Fecha:** 2026-05-04  
**Proyecto:** ClínicaSaaS Dental MX  
**Versión:** 1.0

---

## Propósito

Crear un SaaS multi-tenant para la administración integral de **clínicas dentales independientes en México**, enfocado en la optimización operativa, cumplimiento normativo (NOM-024, CFDI), y automatización de comunicaciones con pacientes.

**Diferenciador clave:** Atacamos exclusivamente al dentista independiente (1-2 sillones), no a grandes clínicas. El producto debe ser auto-gestionable, accesible desde cualquier dispositivo, y cumplir con todas las regulaciones mexicanas desde el día 1.

---

## Alcance (Fase 1 — MVP)

### Dentro del Alcance

| Módulo | Funcionalidad |
|--------|--------------|
| **Onboarding** | Registro self-service de clínicas, verificación por email, configuración inicial |
| **Usuarios** | Gestión de usuarios por clínica (2 en plan base: dentista + recepcionista) |
| **Pacientes** | Registro, ficha clínica, historial de citas y tratamientos |
| **Expediente Clínico** | Evoluciones, notas clínicas, archivos adjuntos. **Cumple NOM-024** |
| **Agenda** | Calendario semanal, creación/edición/cancelación de citas |
| **WhatsApp** | Confirmaciones automáticas 24h antes, respuestas CONFIRMAR/CANCELAR. Twilio operativo desde día 1 |
| **Inventario** | Registro de insumos, stock mínimo, alertas de caducidad, consumo automático por tipo de cita |
| **Facturación CFDI** | Emisión de CFDI 4.0, cancelación, envío por email/WhatsApp. Integración Finkok |
| **Dashboard** | Métricas básicas: citas del día, ingresos, stock bajo |
| **Auditoría** | Bitácora de accesos a expedientes (NOM-024) |

### Fuera del Alcance (Fase 1)

- Odontograma digital interactivo
- Firma electrónica de evoluciones
- Consentimientos informados digitales (solo registro manual en Fase 1)
- Telemedicina / videoconsulta
- CRM de marketing avanzado
- Módulo de laboratorio
- Módulo de ortodoncia
- Pagos en línea (Stripe/MercadoPago)
- App nativa móvil (se cubre con PWA responsive)

---

## Restricciones Técnicas

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| **Backend** | Django 5.x + Django REST Framework | Robusto, maduro, excelente ORM, comunidad grande en México |
| **Base de datos** | PostgreSQL 16 | RLS nativo, JSONB, madurez para multi-tenant |
| **Frontend** | React 18 + Vite + TypeScript (strict) | Rápido de desarrollar, buen ecosistema, type safety |
| **Multi-tenancy** | Schema compartido + PostgreSQL RLS | Costo-efectivo para miles de clínicas pequeñas |
| **Autenticación** | JWT + OAuth2 (Google/Apple) | Stateless, fácil de escalar |
| **Cola de tareas** | Celery + Redis | Async para WhatsApp, emails, reportes |
| **WhatsApp** | Twilio API (operativo día 1) | No requiere verificación Meta, rápido de implementar |
| **Meta WBA** | En paralelo | Objetivo a mediano plazo, más barato por mensaje |
| **CFDI** | Finkok REST API v4.0 | PAC establecido en México, buena documentación |
| **NOM-024** | Cifrado AES-256, audit trail, RBAC | Cumplimiento legal obligatorio |
| **Infraestructura dev** | Docker + Docker Compose | Entornos reproducibles |
| **Infraestructura prod** | AWS/GCP | Escalabilidad, backups, CDN |

---

## Criterios de Éxito

| Métrica | Objetivo | Plazo |
|---------|----------|-------|
| MVP funcional | 100% de casos de uso P0 implementados | 10-12 semanas |
| Beta testers | 50 clínicas activas | Primeros 3 meses post-MVP |
| NPS | > 40 | Después de 3 meses de beta |
| Retención mensual | > 85% | Después de 6 meses |
| Seguridad | Cero incidentes de data leakage entre tenants | Siempre |
| Compliance | Revisión legal NOM-024 aprobada | Antes de venta comercial |

---

## Modelo de Negocio

**Ingresos:** Suscripción mensual/anual + consumo de timbres CFDI

| Plan | Precio MXN/mes | Usuarios | Timbres CFDI | Incluye |
|------|---------------|----------|--------------|---------|
| **Starter** | $299 | 2 | 50 | Agenda, pacientes, expediente básico, email |
| **Pro** | $599 | 3 | 200 | Todo Starter + WhatsApp + inventario + reportes |
| **Premium** | $999 | 5 | Ilimitado | Todo Pro + múltiples sedes + laboratorio + analytics |

**Costos operativos estimados por clínica activa:**
- Infraestructura AWS: ~$5-10 USD/mes por clínica
- Twilio WhatsApp: ~$0.05-0.15 USD por mensaje
- Finkok timbres: ~$0.04-0.08 USD por timbre

---

## Stakeholders

| Rol | Responsabilidad |
|-----|----------------|
| **Dentista** | Usuario principal, atención clínica, firma de evoluciones |
| **Recepcionista** | Agenda, recepción de pacientes, facturación básica |
| **Administrador de clínica** | Configuración, usuarios, datos fiscales, reportes |
| **Paciente** | Usuario externo, recibe notificaciones y facturas |

---

## Dependencias Externas

| Servicio | Uso | Riesgo |
|----------|-----|--------|
| **Finkok** | Timbrado CFDI | Bajo — PAC establecido |
| **Twilio** | WhatsApp/SMS fallback | Bajo — servicio estable |
| **Meta WBA** | WhatsApp definitivo | Medio — requiere verificación |
| **AWS/GCP** | Hosting, almacenamiento | Bajo — proveedores líderes |
| **SAT** | Validación CFDI | Bajo — infraestructura gubernamental |

---

## Glosario

| Término | Definición |
|---------|-----------|
| **CFDI** | Comprobante Fiscal Digital por Internet (factura electrónica mexicana) |
| **NOM-024** | Norma Oficial Mexicana para expediente clínico electrónico |
| **PAC** | Proveedor Autorizado de Certificación (timbra CFDI ante SAT) |
| **RLS** | Row Level Security (seguridad a nivel fila en PostgreSQL) |
| **Tenant** | Instancia aislada de datos para una clínica dentro del sistema multi-tenant |
| **WBA** | WhatsApp Business API |
