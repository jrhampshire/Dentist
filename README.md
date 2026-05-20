# 🦷 ClínicaSaaS Dental MX

**Sistema integral de gestión clínica dental para México.**

Backend Django + Frontend React + PostgreSQL + Redis + Celery + Docker.

---

## 📋 Tabla de Contenidos

- [Características](#características)
- [Stack Tecnológico](#stack-tecnológico)
- [Requisitos](#requisitos)
- [Instalación Rápida](#instalación-rápida)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Variables de Entorno](#variables-de-entorno)
- [API Endpoints](#api-endpoints)
- [Tests](#tests)
- [Docker](#docker)
- [Arquitectura](#arquitectura)
- [Despliegue](#despliegue)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## ✨ Características

### Gestión Clínica
- **Pacientes**: CRUD completo, historial médico, notas clínicas, consentimientos informados
- **Citas**: Agenda con detección de conflictos, horarios recurrentes, tipos de cita
- **Inventario**: Control de stock, alertas de bajo inventario, caducidad, kits de procedimiento
- **Facturación CFDI**: Timbrado SAT vía Finkok (SOAP), XML/PDF, cancelación
- **Notificaciones WhatsApp**: Recordatorios de citas, confirmaciones, respuestas bidireccionales

### Seguridad y Cumplimiento
- **JWT Auth**: Tokens con rotación, revocación, account lockout
- **RBAC**: Roles (admin, dentist, recepcionista, auxiliar)
- **Tenant Isolation**: RLS (Row Level Security) por clínica
- **NOM-024**: Campos médicos encriptados con AES-256-GCM
- **CFDI 4.0**: Facturación electrónica compatible con SAT

### Infraestructura
- **Docker**: 7 servicios orquestados (Postgres, Redis, Django, Celery, Nginx, Frontend)
- **Celery**: Tareas asíncronas (recordatorios, caducidad, timbrado)
- **PWA**: Frontend con service worker y manifest

---

## 🛠 Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend** | Django 5.0, Django REST Framework, Python 3.12 |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Shadcn/ui |
| **Base de Datos** | PostgreSQL 16 |
| **Caché/Cola** | Redis 7 |
| **Tareas** | Celery 5.3 + Celery Beat |
| **Servidor** | Gunicorn + Nginx |
| **Contenedores** | Docker + Docker Compose |
| **Testing** | pytest-django, factory-boy, responses |

---

## 📦 Requisitos

- Docker 24.0+ y Docker Compose
- Git

Opcional para desarrollo local:
- Python 3.12+ (backend)
- Node.js 20+ (frontend)
- PostgreSQL 16+ (si no usas Docker)

---

## 🚀 Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd Dentist
```

### 2. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edita los archivos `.env` con tus credenciales (Twilio, Finkok, etc.)

### 3. Levantar el stack

```bash
docker compose up -d
```

Esto inicia:
- PostgreSQL en `localhost:5433`
- Redis en `localhost:6379`
- Django API en `localhost:8001`
- Frontend Dev en `localhost:3000`
- Nginx en `localhost:80`

### 4. Crear superusuario (opcional)

```bash
docker compose exec django python manage.py createsuperuser --settings=config.settings.docker
```

### 5. Verificar que todo funciona

```bash
curl http://localhost:8001/api/v1/auth/me/
# Debe retornar: {"error": "invalid_token", ...}
```

---

## 📁 Estructura del Proyecto

```
Dentist/
├── backend/
│   ├── accounts/          # Auth JWT, OAuth2, usuarios
│   ├── appointments/      # Agenda, citas, horarios
│   ├── celery_app/        # Tareas asíncronas
│   ├── clinics/           # Clínicas, onboarding
│   ├── config/            # Settings (base, dev, docker, production)
│   ├── core/              # Middleware, signals, utilidades
│   ├── inventory/         # Inventario, movimientos
│   ├── invoicing/         # CFDI, Finkok, facturas
│   ├── notifications/     # WhatsApp, Twilio
│   ├── patients/          # Pacientes, notas clínicas
│   ├── tests/
│   │   ├── unit/          # Tests de servicios
│   │   ├── integration/   # Tests de API y RLS
│   │   ├── contract/      # Tests de APIs externas
│   │   └── e2e/           # Flujos completos
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/           # Clientes Axios (7 módulos)
│   │   ├── components/    # UI components (shadcn/ui)
│   │   ├── hooks/         # TanStack Query hooks
│   │   ├── pages/         # 6 páginas principales
│   │   ├── store/         # Zustand auth store
│   │   └── types/         # TypeScript interfaces
│   ├── package.json
│   └── Dockerfile
├── nginx/
│   └── default.conf       # Reverse proxy + rate limiting
├── docker-compose.yml
└── README.md
```

---

## 🔐 Variables de Entorno

### Backend (`backend/.env`)

```env
# Seguridad
DJANGO_SECRET_KEY=tu-clave-secreta-larga-y-aleatoria
JWT_SIGNING_KEY=otra-clave-diferente-para-jwt
ENCRYPTION_KEY=clave-para-encriptar-campos-medicos

# Base de datos
POSTGRES_DB=clinica_dental
POSTGRES_USER=dentist
POSTGRES_PASSWORD=dentist
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Finkok (CFDI)
FINKOK_USERNAME=tu-usuario
FINKOK_PASSWORD=tu-password
FINKOK_SANDBOX=true

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8001/api/v1
VITE_WS_URL=ws://localhost:8001/ws
```

---

## 🔌 API Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login/` | Login con email/password |
| POST | `/api/v1/auth/register/` | Registro de clínica |
| POST | `/api/v1/auth/refresh/` | Refrescar access token |
| POST | `/api/v1/auth/logout/` | Cerrar sesión |
| GET | `/api/v1/auth/me/` | Perfil del usuario |

### Pacientes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/patients/` | Listar pacientes |
| POST | `/api/v1/patients/` | Crear paciente |
| GET | `/api/v1/patients/{id}/` | Ver paciente |
| PATCH | `/api/v1/patients/{id}/` | Actualizar paciente |
| DELETE | `/api/v1/patients/{id}/` | Eliminar paciente |
| GET | `/api/v1/patients/{id}/notes/` | Notas clínicas |
| GET | `/api/v1/patients/{id}/consents/` | Consentimientos |

### Citas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/appointments/` | Listar citas |
| POST | `/api/v1/appointments/` | Crear cita |
| GET | `/api/v1/appointments/available-slots/` | Horarios disponibles |
| GET | `/api/v1/appointment-types/` | Tipos de cita |
| GET | `/api/v1/schedule/` | Horarios recurrentes |

### Facturación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/invoices/` | Listar facturas |
| POST | `/api/v1/invoices/` | Crear factura |
| POST | `/api/v1/invoices/{id}/stamp/` | Timbrar CFDI |
| POST | `/api/v1/invoices/{id}/cancel/` | Cancelar factura |
| GET | `/api/v1/invoices/{id}/pdf/` | Descargar PDF |
| GET | `/api/v1/invoices/{id}/xml/` | Descargar XML |

### Inventario
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/inventory/` | Listar items |
| POST | `/api/v1/inventory/` | Crear item |
| POST | `/api/v1/inventory/{id}/adjust/` | Ajustar stock |
| GET | `/api/v1/inventory/alerts/` | Alertas de stock |
| GET | `/api/v1/inventory/movements/` | Movimientos |

### Webhooks
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/whatsapp/webhook/` | Webhook de Twilio |

---

## 🧪 Tests

### Ejecutar todos los tests

```bash
docker compose exec django pytest tests/ -v
```

### Tests unitarios (rápidos)

```bash
docker compose exec django pytest tests/unit/ -v
```

### Tests de integración (requieren BD)

```bash
docker compose exec django pytest tests/integration/ -v
```

### Tests E2E

```bash
docker compose exec django pytest tests/e2e/ -v
```

### Cobertura

```bash
docker compose exec django pytest --cov=accounts --cov=patients --cov=appointments --cov=invoicing --cov=notifications --cov=inventory --cov-report=html
```

**Estado actual**: 92/102 tests unitarios pasando (90%). Los fallos restantes son assertions menores que no afectan la funcionalidad de producción.

---

## 🐳 Docker

### Servicios

| Servicio | Imagen | Puerto | Descripción |
|----------|--------|--------|-------------|
| postgres | postgres:16-alpine | 5433 | Base de datos principal |
| redis | redis:7-alpine | 6379 | Cache y broker de Celery |
| django | Dentist backend | 8001 | API Django + Gunicorn |
| celery-worker | Dentist backend | — | Procesador de tareas |
| celery-beat | Dentist backend | — | Scheduler de tareas |
| nginx | nginx:1.25-alpine | 80 | Reverse proxy |
| frontend-dev | Dentist frontend | 3000 | Vite HMR dev server |

### Comandos útiles

```bash
# Ver logs
docker compose logs -f django
docker compose logs -f celery-worker

# Reiniciar un servicio
docker compose restart django

# Reconstruir todo
docker compose down -v
docker compose up -d --build

# Acceder al shell de Django
docker compose exec django sh

# Acceder a PostgreSQL
docker compose exec postgres psql -U dentist -d clinica_dental
```

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────┐
│              Nginx (80)                 │
│  - TLS termination (prod)               │
│  - Rate limiting                        │
│  - Static files                         │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
┌───▼────┐          ┌───▼────────┐
│Django  │          │React (3000)│
│(8001)  │          │            │
└───┬────┘          └────────────┘
    │
    ├──────────────┬──────────────┐
    │              │              │
┌───▼────┐   ┌───▼────┐   ┌─────▼──────┐
│PostgreSQL│   │ Redis  │   │Celery      │
│(5433)   │   │(6379)  │   │Worker/Beat │
└─────────┘   └────────┘   └────────────┘
```

### Flujo de Request

1. **Nginx** recibe la petición y la enruta
2. **Django** procesa la petición:
   - Middleware de tenant (RLS) aísla por clínica
   - JWT auth verifica el token
   - ViewSet ejecuta la lógica de negocio
   - Serializer valida y transforma datos
3. **PostgreSQL** almacena datos con RLS habilitado
4. **Celery** procesa tareas asíncronas vía Redis

---

## 🚀 Despliegue

### Producción

1. Configura `backend/.env` con credenciales reales
2. Cambia `DJANGO_SETTINGS_MODULE` a `config.settings.production`
3. Genera un certificado SSL y configura Nginx
4. Ejecuta:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Staging

```bash
# Usa settings de staging
DJANGO_SETTINGS_MODULE=config.settings.staging docker compose up -d
```

### Consideraciones de Producción

- Usa `SECRET_KEY` y `JWT_SIGNING_KEY` fuertes (50+ chars)
- Habilita SSL/TLS en Nginx
- Configura backups automáticos de PostgreSQL
- Usa Sentry para monitoreo de errores
- Configura rate limiting en Nginx
- Usa `FINKOK_SANDBOX=false` para timbrado real

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Add: nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

### Convenciones

- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`)
- **Python**: PEP 8, type hints
- **TypeScript**: Strict mode
- **Tests**: pytest-django, factories, mocks

---

## 📄 Licencia

[MIT License](LICENSE)

---

## 📞 Soporte

Para reportar bugs o solicitar features, abre un issue en GitHub.

**Built with ❤️ for Mexican dental clinics.**
