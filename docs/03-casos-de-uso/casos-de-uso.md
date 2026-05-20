# Casos de Uso — Dental SaaS MX

**Fecha:** 2026-05-04  
**Proyecto:** ClínicaSaaS Dental MX  
**Versión:** 1.0

---

## Actores del Sistema

| Actor | Descripción | Frecuencia |
|-------|-------------|------------|
| **Dentista** | Profesional de la salud dental, dueño del consultorio | Diaria |
| **Recepcionista** | Personal administrativo que agenda y atiende | Diaria |
| **Paciente** | Usuario externo que recibe servicios | Eventual |
| **Administrador de Clínica** | Gestiona configuración, usuarios, facturación | Semanal |
| **Sistema** | Procesos automáticos (alertas, notificaciones) | Continua |

---

## Casos de Uso — Administración

### UC-ADM-01: Registro de Clínica (Onboarding)

**Actor:** Administrador de Clínica  
**Prioridad:** P0  
**Precondición:** No existe clínica registrada con ese RFC

**Flujo principal:**
1. Admin ingresa a landing page y hace clic en "Crear cuenta"
2. Sistema solicita: nombre de clínica, RFC, email, contraseña
3. Admin completa datos y acepta términos y condiciones
4. Sistema envía email de verificación
5. Admin confirma email
6. Sistema crea tenant (esquema en PostgreSQL con RLS)
7. Sistema redirige al dashboard de configuración

**Flujos alternativos:**
- 3a. RFC ya registrado → sistema muestra error y sugiere recuperar cuenta
- 4a. Email no verificado en 24h → sistema envía recordatorio

**Postcondición:** Clínica activa con plan Starter por defecto

---

### UC-ADM-02: Gestión de Usuarios

**Actor:** Administrador de Clínica  
**Prioridad:** P0  
**Precondición:** Clínica registrada y verificada

**Flujo principal:**
1. Admin accede a "Configuración > Usuarios"
2. Sistema muestra lista de usuarios activos
3. Admin hace clic en "Agregar usuario"
4. Sistema solicita: nombre, email, rol (dentista/recepcionista)
5. Admin completa datos y guarda
6. Sistema envía email de invitación con link de activación
7. Usuario invitado establece contraseña y accede al sistema

**Flujos alternativos:**
- 5a. Límite de usuarios alcanzado → sistema muestra opción de upgrade

**Postcondición:** Nuevo usuario activo con permisos según rol

---

### UC-ADM-03: Configuración de Datos Fiscales

**Actor:** Administrador de Clínica  
**Prioridad:** P1  
**Precondición:** Clínica registrada

**Flujo principal:**
1. Admin accede a "Configuración > Facturación"
2. Sistema muestra formulario: RFC, razón social, régimen fiscal, dirección fiscal, CSD (.cer y .key)
3. Admin completa datos y sube archivos CSD
4. Sistema valida CSD con SAT (vía Finkok)
5. Sistema guarda configuración y muestra confirmación

**Flujos alternativos:**
- 4a. CSD inválido → sistema muestra error específico

**Postcondición:** Clínica configurada para emitir CFDI

---

## Casos de Uso — Pacientes

### UC-PAC-01: Registro de Paciente

**Actor:** Recepcionista / Dentista  
**Prioridad:** P0  
**Precondición:** Sesión activa, clínica configurada

**Flujo principal:**
1. Usuario accede a "Pacientes > Nuevo"
2. Sistema muestra formulario: nombre, teléfono, email, fecha de nacimiento, género, CURP (opcional), contacto de emergencia
3. Usuario completa datos y guarda
4. Sistema crea registro en `patients` con `clinic_id`
5. Sistema muestra mensaje de confirmación y abre ficha del paciente

**Flujos alternativos:**
- 3a. Teléfono ya registrado → sistema sugiere paciente existente

**Postcondición:** Paciente registrado y disponible para agendar

---

### UC-PAC-02: Consulta de Expediente Clínico

**Actor:** Dentista  
**Prioridad:** P1  
**Precondición:** Paciente registrado

**Flujo principal:**
1. Dentista busca paciente por nombre o teléfono
2. Sistema muestra resultados de búsqueda
3. Dentista selecciona paciente
4. Sistema muestra ficha completa: datos personales, historial de citas, tratamientos, notas clínicas, archivos adjuntos
5. Sistema registra acceso en `audit_log` (timestamp, usuario, IP, acción: "VIEW")

**Flujos alternativos:**
- 1a. No hay resultados → sistema permite crear paciente nuevo

**Postcondición:** Expediente consultado, traza de auditoría registrada

---

### UC-PAC-03: Registro de Evolución Clínica

**Actor:** Dentista  
**Prioridad:** P1  
**Precondición:** Cita en curso o finalizada

**Flujo principal:**
1. Dentista accede a ficha del paciente
2. Dentista hace clic en "Nueva evolución"
3. Sistema muestra editor de texto enriquecido
4. Dentista redacta evolución y guarda
5. Sistema registra evolución en `clinical_notes` con timestamp y firma digital del dentista
6. Sistema agrega entrada en `audit_log`

**Flujos alternativos:**
- 4a. Dentista abandona sin guardar → sistema muestra confirmación de salida

**Postcondición:** Evolución registrada e inmutable (solo lectura posterior)

---

## Casos de Uso — Agenda

### UC-AGE-01: Agendar Cita

**Actor:** Recepcionista / Dentista  
**Prioridad:** P0  
**Precondición:** Paciente registrado

**Flujo principal:**
1. Usuario accede a "Agenda"
2. Sistema muestra calendario semanal con citas existentes
3. Usuario selecciona fecha/hora libre
4. Sistema muestra formulario: paciente (autocomplete), tipo de cita, duración, notas
5. Usuario completa y guarda
6. Sistema crea cita en `appointments`
7. Sistema programa notificación de confirmación (WhatsApp/email) 24h antes

**Flujos alternativos:**
- 3a. Horario ocupado → sistema muestra conflicto y sugiere alternativas
- 5a. Paciente no registrado → sistema permite crear paciente rápido

**Postcondición:** Cita agendada con notificación programada

---

### UC-AGE-02: Confirmación de Cita por WhatsApp

**Actor:** Sistema (automático) / Paciente  
**Prioridad:** P1  
**Precondición:** Cita agendada con notificación programada

**Flujo principal:**
1. 24h antes de la cita, Celery ejecuta tarea
2. Sistema genera mensaje con plantilla de Twilio: "Hola [nombre], le confirmamos su cita el [fecha] a las [hora] con el Dr./Dra. [nombre]. Responda CONFIRMAR o CANCELAR"
3. Twilio envía mensaje de WhatsApp
4. Paciente recibe mensaje y responde "CONFIRMAR"
5. Twilio webhook recibe respuesta
6. Sistema actualiza estado de cita a "Confirmada"
7. Sistema notifica a recepcionista vía dashboard

**Flujos alternativos:**
- 4a. Paciente responde "CANCELAR" → cita cambia a "Cancelada", se libera horario
- 4b. Paciente no responde en 4h → sistema envía recordatorio por email

**Postcondición:** Estado de cita actualizado

---

### UC-AGE-03: Reagendar Cita

**Actor:** Recepcionista  
**Prioridad:** P2  
**Precondición:** Cita existente (confirmada o pendiente)

**Flujo principal:**
1. Recepcionista selecciona cita en agenda
2. Recepcionista hace clic en "Reagendar"
3. Sistema muestra calendario para seleccionar nueva fecha/hora
4. Recepcionista selecciona nuevo horario
5. Sistema actualiza cita y re-programa notificación
6. Sistema envía mensaje de WhatsApp al paciente con nueva fecha

**Postcondición:** Cita reagendada, paciente notificado

---

## Casos de Uso — Inventario

### UC-INV-01: Registro de Insumo

**Actor:** Recepcionista / Administrador  
**Prioridad:** P1  
**Precondición:** Sesión activa

**Flujo principal:**
1. Usuario accede a "Inventario > Nuevo Insumo"
2. Sistema muestra formulario: nombre, categoría, unidad, stock inicial, stock mínimo, fecha de caducidad, proveedor, precio unitario
3. Usuario completa y guarda
4. Sistema crea registro en `inventory_items`

**Postcondición:** Insumo registrado y disponible

---

### UC-INV-02: Consumo Automático por Cita

**Actor:** Sistema (automático)  
**Prioridad:** P2  
**Precondición:** Cita finalizada, tipo de cita asociado a kit de insumos

**Flujo principal:**
1. Dentista marca cita como "Completada"
2. Sistema verifica si el tipo de cita tiene un "kit de insumos" configurado
3. Si existe kit, sistema crea registros en `inventory_movements` (salida) por cada insumo
4. Sistema actualiza `stock_actual` en `inventory_items`
5. Si algún insumo queda <= `stock_mínimo`, sistema genera alerta

**Flujos alternativos:**
- 3a. No hay kit configurado → sistema no hace nada (consumo manual opcional)
- 5a. Stock queda negativo → sistema muestra alerta crítica y bloquea nuevas citas con ese kit hasta reabastecer

**Postcondición:** Stock actualizado, alertas generadas si aplica

---

### UC-INV-03: Alerta de Caducidad

**Actor:** Sistema (automático) / Administrador  
**Prioridad:** P2  
**Precondición:** Insumos con fecha de caducidad registrada

**Flujo principal:**
1. Diariamente a las 8:00 AM, Celery ejecuta tarea de verificación
2. Sistema busca insumos con caducidad en 30 o 7 días
3. Sistema envía email de alerta a administrador con lista de insumos próximos a caducar
4. Administrador recibe email y toma acción (descarte o uso prioritario)

**Postcondición:** Alerta enviada, traza registrada

---

## Casos de Uso — Facturación CFDI

### UC-FAC-01: Emisión de Factura

**Actor:** Recepcionista / Administrador  
**Prioridad:** P0  
**Precondición:** Clínica tiene datos fiscales configurados y timbres disponibles

**Flujo principal:**
1. Usuario accede a "Facturación > Nueva Factura"
2. Sistema muestra formulario: paciente (o RFC genérico), concepto(s), importe, uso CFDI, método de pago
3. Usuario completa datos y hace clic en "Timbrar"
4. Sistema genera XML de CFDI 4.0
5. Sistema envía XML a Finkok API
6. Finkok timbra y devuelve XML timbrado + PDF
7. Sistema almacena UUID, guarda archivos, y marca factura como "Timbrada"
8. Sistema envía PDF por email/WhatsApp al paciente

**Flujos alternativos:**
- 5a. Error de Finkok (sin timbres, CSD inválido) → sistema muestra error específico y sugiere acción
- 6a. SAT rechaza CFDI → sistema guarda error y permite corregir

**Postcondición:** Factura timbrada, paciente notificado, UUID registrado

---

### UC-FAC-02: Cancelación de Factura

**Actor:** Administrador  
**Prioridad:** P2  
**Precondición:** Factura timbrada, dentro de plazo de cancelación (SAT)

**Flujo principal:**
1. Admin busca factura por UUID o paciente
2. Sistema muestra detalle de factura
3. Admin hace clic en "Cancelar"
4. Sistema solicita motivo de cancelación (SAT requiere)
5. Admin selecciona motivo y confirma
6. Sistema envía solicitud de cancelación a Finkok
7. Finkok confirma cancelación ante SAT
8. Sistema actualiza estado a "Cancelada"

**Postcondición:** Factura cancelada, SAT notificado

---

## Casos de Uso — NOM-024 Compliance

### UC-NOM-01: Consentimiento Informado

**Actor:** Recepcionista / Dentista  
**Prioridad:** P2  
**Precondición:** Paciente nuevo o tratamiento invasivo

**Flujo principal:**
1. Usuario selecciona paciente
2. Sistema muestra opción "Generar consentimiento"
3. Sistema genera documento con datos del paciente y tratamiento
4. Paciente firma digitalmente (en tablet/dispositivo de clínica) o con firma manuscrita escaneada
5. Sistema almacena consentimiento en `patient_consents` con hash de verificación
6. Sistema registra en `audit_log`

**Flujos alternativos:**
- 4a. Paciente no firma → sistema bloquea registro de tratamiento hasta obtener consentimiento

**Postcondición:** Consentimiento registrado, tratamiento habilitado

---

### UC-NOM-02: Auditoría de Acceso

**Actor:** Administrador / Dentista (solo sus propios registros)  
**Prioridad:** P2  
**Precondición:** Sesión activa

**Flujo principal:**
1. Admin accede a "Reportes > Auditoría"
2. Sistema muestra filtros: fecha, usuario, tipo de acción, paciente
3. Admin aplica filtros y sistema muestra lista de eventos
4. Sistema muestra: timestamp, usuario, IP, acción, recurso afectado, resultado

**Restricción:** Un dentista solo puede ver registros de sus propios pacientes. Admin ve todo.

**Postcondición:** Reporte de auditoría generado

---

## Casos de Uso — Notificaciones Automáticas

### UC-NOT-01: Recordatorio de Cita

**Actor:** Sistema (automático)  
**Prioridad:** P1  
**Precondición:** Cita agendada para mañana

**Flujo principal:**
1. 24h antes, Celery ejecuta tarea
2. Sistema genera mensaje personalizado
3. Sistema envía por WhatsApp (Twilio) al paciente
4. Sistema registre envío en `notification_log`

**Flujos alternativos:**
- 3a. WhatsApp falla → fallback a SMS (si configurado) o email

**Postcondición:** Paciente notificado

---

### UC-NOT-02: Alerta de Stock Bajo

**Actor:** Sistema (automático)  
**Prioridad:** P2  
**Precondición:** Consumo automático o ajuste manual deja stock <= mínimo

**Flujo principal:**
1. Sistema detecta stock bajo
2. Sistema genera alerta en dashboard de administrador
3. Sistema envía email de alerta con detalle de insumo y cantidad actual

**Postcondición:** Administrador notificado

---

## Matriz de Prioridad

| Prioridad | Casos de Uso | Justificación |
|-----------|-------------|---------------|
| **P0** | UC-ADM-01, UC-ADM-02, UC-PAC-01, UC-AGE-01, UC-FAC-01 | Core del producto, sin esto no hay negocio |
| **P1** | UC-AGE-02, UC-PAC-02, UC-PAC-03, UC-INV-01, UC-NOT-01 | Diferenciación y valor agregado |
| **P2** | UC-INV-02, UC-INV-03, UC-FAC-02, UC-NOM-01, UC-NOM-02, UC-AGE-03, UC-NOT-02, UC-ADM-03 | Optimización, compliance y mejoras de UX |

---

## Reglas de Negocio Transversales

1. **RLS (Row Level Security):** Todo query a la base de datos debe filtrar por `clinic_id`. Nunca se deben mostrar datos de otra clínica.
2. **Auditoría NOM-024:** Cada acceso a datos de paciente (lectura o escritura) debe registrarse en `audit_log` con timestamp, usuario, IP y acción.
3. **Inmutabilidad de evoluciones:** Una vez firmada una evolución clínica, no puede modificarse. Solo lectura.
4. **Consentimiento previo:** No se puede registrar un tratamiento sin consentimiento informado firmado.
5. **Caducidad de inventario:** Los insumos caducados deben bloquearse automáticamente para su uso en citas.
6. **Timbres CFDI:** Si no hay timbres disponibles, el sistema debe bloquear la emisión de nuevas facturas y notificar al administrador.
7. **WhatsApp opt-out:** Si un paciente responde "BAJA" o "STOP", el sistema debe marcarlo como "no contactar por WhatsApp" y respetarlo.
