# Estudio de Viabilidad — Dental SaaS MX

**Fecha:** 2026-05-04  
**Proyecto:** ClínicaSaaS Dental MX  
**Autor:** Arquitecto de Sistemas

---

## 1. Contexto y Referencias del Mercado

### Competidores Analizados

| Competidor | País | Modelo | Diferenciador Principal |
|------------|------|--------|------------------------|
| **Dentalink** | México | B2B Enterprise | +10k clínicas, certificado NOM-024, suite completa. Precio no público (solo demo). Fuerte en clínicas medianas/grandes. |
| **Doctocliq** | Latinoamérica | B2B Self-service | Plan gratuito hasta 30 pacientes, plan Individual ~USD 19/mes. WhatsApp integrado. Más accesible para independientes. |

### Diferenciación Viable
- Enfoque exclusivo en **dentistas independientes** (no clínicas grandes)
- Onboarding **auto-gestionado** (self-signup)
- Experiencia **mobile-first** (Dentalink es más desktop-oriented)
- Pricing **predecible y accesible**
- Integración CFDI simplificada (Finkok desde día 1)

---

## 2. Stack Tecnológico — Viabilidad Confirmada

### Backend: Django + PostgreSQL

**Multi-tenancy: Schema compartido + Row Level Security (RLS)**

```
Clínicas (comparten tablas)
├── clinics       ← configuración de cada clínica
├── patients      ← pacientes por clínica
├── appointments  ← citas por clínica
├── invoices      ← facturas por clínica
└── inventory     ← inventario por clínica
```

PostgreSQL con RLS asegura que cada clínica **solo vea sus propios datos**. Un query mal hecho jamás filtra datos de otra clínica.

**Alternativa descartada:** Un schema PostgreSQL por clínica — demasiado overhead para clínicos independientes.

**Recomendación:** Un DB compartido con RLS es el sweet spot.

**Django no tiene multi-tenancy built-in**, pero se resuelve con:
- Middleware que inyecta `tenant_id` en cada request
- `@tenant_aware` decorators en modelos
- `request.tenant` disponible globalmente

### Frontend: React + Vite

- **Vite**: HMR rápido y builds optimizados
- **React Query + Zod**: Manejo de estado server y validación de tipos
- **Shadcn/ui**: Componentes accesibles
- **Responsive**: Tailwind CSS
- **Mobile**: PWA + responsive (sin React Native)

---

## 3. Módulos — Alcance y Complejidad

### 3.1 Expediente Clínico Digital — NOM-024-SSA3-2012

**Requisitos obligatorios de la norma:**

| Requisito | Implementación |
|-----------|---------------|
| **Cifrado de datos** | AES-256 en BD, TLS en tránsito |
| **Control de acceso** | Autenticación por usuario + rol |
| **Bitácora de accesos** | Cada consulta/modificación auditada (usuario, timestamp, IP) |
| **Consentimiento informado** | Paciente firma antes de crear expediente |
| **Disponibilidad** | SLA 99.9% |
| **Respaldo** | Backup cifrado diario |
| **Retención** | Mínimo 5 años después del último contacto |

**Impacto en diseño:**
- Campo `consentimiento_firmado` + blob de firma digital
- Tabla `audit_log` por cada operación sobre datos sensibles
- Doble cifrado: Django (field encryption) + PostgreSQL (pgcrypto)
- Sello digital del profesional sobre evoluciones (inmutable post-firma)

**Complejidad: ALTA**

---

### 3.2 Facturación CFDI con Finkok

**Finkok** es un PAC (Proveedor Autorizado de Certificación) que provee:
- Timbrado de CFDI 4.0
- Cancelación de CFDI
- Consulta de estatus ante SAT
- API REST bien documentada

**Flujo:**
1. Usuario captura venta/tratamiento
2. Sistema genera XML con datos fiscales
3. Envía XML a Finkok API → Finkok timbra con CSD del PAC
4. Finkok devuelve CFDI XML timbrado + PDF
5. Sistema almacena UUID del CFDI
6. Paciente recibe PDF por email o WhatsApp

**Modelo de pricing Finkok:**
- **Prepago**: Compras timbres (~$0.80 MXN/timbre)
- **Mensual**: Fee fijo + costo por timbre

**Dato importante:** El sistema debe soportar **RFC genérico** para pacientes sin RFC.

**Complejidad: MEDIA**

---

### 3.3 Confirmación por WhatsApp

| Solución | Pros | Contras |
|----------|------|---------|
| **WhatsApp Business API directa** | Oficial, más barata por mensaje | Requiere Meta Business Partner, verificación, teléfono dedicado |
| **Twilio** | Más fácil de integrar, no requiere Meta | Costo por mensaje más alto |

**Decisión:** Twilio como **fallback operativo desde día 1**, Meta WBA como objetivo paralelo.

**Flujo:**
1. Cita creada/modificada → evento en cola (Celery/Redis)
2. Worker toma evento → genera mensaje con plantilla
3. Envía vía API → paciente recibe WhatsApp
4. Paciente confirma/cancela → webhook recibe respuesta
5. Sistema actualiza estatus de cita

**Complejidad: MEDIA-ALTA**

---

### 3.4 Control de Inventarios

**Modelo de datos:**
```
inventory_items
├── clínica_id
├── nombre (ej. "Anestesia Articaína 40mg")
├── categoría (Anestésicos, Materiales, Instrumental)
├── unidad (caja, pieza, ml)
├── stock_actual
├── stock_mínimo
├── fecha_caducidad
├── precio_unitario
└── proveedor

inventory_movements
├── clínica_id
├── item_id
├── tipo (entrada/salida/ajuste)
├── cantidad
├── fecha
└── nota
```

**Reglas de negocio críticas:**
1. **Alertas de caducidad**: 30 y 7 días antes
2. **Alertas de stock mínimo**: automático
3. **Consumo por cita**: descontar insumos al cerrar cita (configurable por kit)
4. **Predicción**: Dashboard con consumo histórico

**Complejidad: BAJA-MEDIA**

---

## 4. Modelo de Negocio — Pricing Sugerido

| Plan | Precio MXN/mes | Incluye |
|------|---------------|---------|
| **Starter** | $299 | Pacientes ilimitados, agenda, expediente básico, 50 timbres CFDI/mes |
| **Pro** | $599 | Todo Starter + WhatsApp + inventario + reportes + 200 timbres |
| **Premium** | $999 | Todo Pro + múltiples usuarios + laboratorio + CFDI ilimitado |

**Descuento anual:** ~20%

---

## 5. Riesgos y Mitigaciones

| Riesgo | Nivel | Mitigación |
|--------|-------|-----------|
| **Cumplimiento NOM-024** | ALTO | Audit pre-venta con abogado de salud. No vender sin revisión legal. |
| **Caducidad de materiales** | MEDIO | Alertas automáticas 30/7 días antes. |
| **Agotamiento de timbres CFDI** | MEDIO | Notificación proactiva <20 timbres. Fondo de reserva. |
| **Meta revisa/bloquea WhatsApp** | MEDIO | Twilio como fallback desde día 1. |
| **Competencia Dentalink** | BAJO | Diferenciación por precio, UX mobile-first, onboarding self-service. |
| **Escalabilidad multi-tenant** | MEDIO | PostgreSQL RLS sólido hasta ~5k clínicas. Monitorear e indexar. |

---

## 6. Roadmap Sugerido

```
FASE 1 — MVP de Administración (10-12 semanas)
├── Auth + onboarding self-service
├── Agenda básica
├── Pacientes + expediente básico
├── Notificaciones por email
└── Dashboard básico

FASE 2 — CFDI + WhatsApp (6-8 semanas)
├── Integración Finkok
├── WhatsApp confirmaciones (Twilio)
├── Dashboard de ingresos
└── Reportes básicos

FASE 3 — Inventario + Completo (8-10 semanas)
├── Módulo de inventario con alertas
├── Consumo automático por cita
├── Firma electrónica de evoluciones
└── Consentimientos informados digitales

FASE 4 — Expansión (4-6 semanas)
├── Analytics avanzados
├── Agendamiento online público
└── Campañas de email marketing
```

**Total estimado:** 26-34 semanas para producto competitivo.

---

## 7. Decisiones Clave Confirmadas

1. ✅ NOM-024 cumplimiento desde día 1 (riesgo legal)
2. ✅ Twilio WhatsApp como fallback operativo, Meta WBA en paralelo
3. ✅ Consumo automático de inventario por kit de insumos por tipo de cita
4. ✅ 2 usuarios por clínica en plan base (dentista + recepcionista)
5. ✅ Target: dentistas independientes en México
6. ✅ Multi-tenant: schema compartido con PostgreSQL RLS
