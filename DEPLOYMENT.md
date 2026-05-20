# 🚀 Guía de Despliegue — ClínicaSaaS Dental MX

## Índice

1. [Requisitos](#requisitos)
2. [Preparación del Servidor](#preparación-del-servidor)
3. [Configuración de SSL/TLS](#configuración-de-ssltls)
4. [Variables de Entorno de Producción](#variables-de-entorno-de-producción)
5. [Despliegue con Docker](#despliegue-con-docker)
6. [Migraciones y Datos Iniciales](#migraciones-y-datos-iniciales)
7. [Verificación Post-Despliegue](#verificación-post-despliegue)
8. [Rollback](#rollback)
9. [Monitoreo](#monitoreo)
10. [Backup y Recuperación](#backup-y-recuperación)

---

## Requisitos

### Hardware Mínimo
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disco**: 20 GB SSD
- **Red**: Puerto 80/443 abierto

### Software
- Ubuntu 22.04 LTS (recomendado)
- Docker 24.0+
- Docker Compose v2
- Git

### Servicios Externos (Opcionales pero Recomendados)
- **Twilio**: Para WhatsApp (obtén Account SID y Auth Token)
- **Finkok**: Para timbrado CFDI (obtén usuario/password)
- **Sentry**: Para monitoreo de errores (opcional)
- **Google Cloud / AWS**: Para backups automatizados

---

## Preparación del Servidor

### 1. Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar Docker

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalación
docker --version
docker compose version
```

### 3. Configurar firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Configuración de SSL/TLS

### Opción A: Let's Encrypt (Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Generar certificado (reemplaza con tu dominio)
sudo certbot certonly --standalone -d clinica-dental.mx -d www.clinica-dental.mx

# Certificados se guardan en:
# /etc/letsencrypt/live/clinica-dental.mx/fullchain.pem
# /etc/letsencrypt/live/clinica-dental.mx/privkey.pem
```

### Opción B: Certificado Comercial

```bash
# Crear directorio para certificados
mkdir -p ./nginx/ssl

# Copiar tus certificados
cp tu-certificado.crt ./nginx/ssl/cert.pem
cp tu-llave-privada.key ./nginx/ssl/key.pem
```

---

## Variables de Entorno de Producción

### Crear archivos de configuración

```bash
# Clonar el repositorio
git clone <tu-repo-url>
cd Dentist

# Crear archivos .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Configurar `backend/.env`

```bash
# Seguridad (¡CAMBIA ESTAS CLAVES!)
DJANGO_SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n')
JWT_SIGNING_KEY=$(openssl rand -base64 50 | tr -d '\n')
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')

# Base de datos (usar contraseña fuerte)
POSTGRES_DB=clinica_dental
POSTGRES_USER=dentist
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Twilio (obtener de https://www.twilio.com/console)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Finkok (obtener de https://www.finkok.com/)
FINKOK_USERNAME=tu-usuario-finkok
FINKOK_PASSWORD=tu-password-finkok
FINKOK_SANDBOX=false

# Email (Gmail SMTP o similar)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password-de-gmail

# Sentry (opcional)
SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz

# Dominio
PRODUCTION_ALLOWED_HOSTS=clinica-dental.mx,www.clinica-dental.mx
PRODUCTION_FRONTEND_URL=https://clinica-dental.mx
CORS_ALLOWED_ORIGINS=https://clinica-dental.mx
```

### Configurar `frontend/.env`

```bash
VITE_API_URL=https://clinica-dental.mx/api/v1
VITE_WS_URL=wss://clinica-dental.mx/ws
```

---

## Despliegue con Docker

### 1. Configurar docker-compose para producción

Crea `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  django:
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.production
    command: >
      sh -c "
        python manage.py migrate --noinput &&
        python manage.py collectstatic --noinput &&
        gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
      "

  nginx:
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
```

### 2. Configurar Nginx para SSL

Actualiza `nginx/default.conf`:

```nginx
server {
    listen 80;
    server_name clinica-dental.mx www.clinica-dental.mx;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name clinica-dental.mx www.clinica-dental.mx;

    # SSL certificates
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    # API
    location /api/ {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Frontend
    location / {
        root /app/dist;
        try_files $uri $uri/ /index.html;
        expires 1d;
    }
}
```

### 3. Desplegar

```bash
# Pull últimos cambios
git pull origin main

# Construir imágenes
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Detener servicios anteriores
docker compose down

# Iniciar servicios
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verificar estado
docker compose ps
```

---

## Migraciones y Datos Iniciales

### 1. Crear superusuario

```bash
docker compose exec django python manage.py createsuperuser
```

### 2. Crear clínica inicial

```bash
docker compose exec django python manage.py shell << 'EOF'
from clinics.models import Clinic
Clinic.objects.create(
    name="Clínica Principal",
    rfc="XAXX010101000",
    email="admin@clinica.com",
    status="active"
)
print("Clínica creada")
EOF
```

### 3. Cargar datos de prueba (opcional)

```bash
docker compose exec django python manage.py loaddata fixtures/initial_data.json
```

---

## Verificación Post-Despliegue

### Checklist

- [ ] `curl https://clinica-dental.mx/api/v1/auth/me/` retorna 401
- [ ] `curl https://clinica-dental.mx/` carga el frontend
- [ ] Login funciona con superusuario
- [ ] Crear paciente funciona
- [ ] Agenda muestra citas
- [ ] WhatsApp envía mensajes (si configurado)
- [ ] CFDI timbra correctamente (si configurado)

### Logs

```bash
# Ver logs en tiempo real
docker compose logs -f

# Logs específicos
docker compose logs -f django
docker compose logs -f celery-worker
```

---

## Rollback

### Rollback rápido

```bash
# Ver imágenes anteriores
docker images | grep dentist

# Rollback a versión anterior
docker compose down
docker tag dentist-django:anterior dentist-django:latest
docker compose up -d
```

### Rollback de base de datos

```bash
# Restaurar backup
pg_restore -h localhost -U dentist -d clinica_dental backup.sql
```

---

## Monitoreo

### Opción 1: Sentry

Configurado automáticamente si `SENTRY_DSN` está definido.

### Opción 2: Logs con Loki (opcional)

```yaml
# Agregar a docker-compose.yml
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - ./loki:/etc/loki
  command: -config.file=/etc/loki/local-config.yaml
```

### Health Checks

```bash
# Verificar salud
curl https://clinica-dental.mx/api/v1/health/

# Estado de contenedores
docker compose ps
```

---

## Backup y Recuperación

### Backup Automático

Crea `backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Backup PostgreSQL
docker compose exec postgres pg_dump -U dentist clinica_dental > "$BACKUP_DIR/db_$DATE.sql"

# Backup media files
tar czf "$BACKUP_DIR/media_$DATE.tar.gz" ./backend/media/

# Limpiar backups antiguos (mantener 7 días)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completado: $DATE"
```

Agregar a crontab:

```bash
# Backup diario a las 2 AM
0 2 * * * /ruta/al/backup.sh >> /var/log/backup.log 2>&1
```

### Recuperación

```bash
# Restaurar base de datos
docker compose exec -T postgres psql -U dentist -d clinica_dental < backup_20240115.sql

# Restaurar media files
tar xzf media_20240115.tar.gz
```

---

## Testing

### Ejecutar tests en Docker

El entorno de pruebas usa `config.settings.test` (DJANGO_SETTINGS_MODULE) y pytest con cobertura configurada en `pytest.ini`.

```bash
# Suite completa (todos los marcadores)
docker compose run --rm backend pytest

# Solo tests unitarios (rápidos, sin base de datos)
docker compose run --rm backend pytest -m unit

# Solo tests de integración (requieren base de datos)
docker compose run --rm backend pytest -m integration

# Tests de contrato (mocks de APIs externas)
docker compose run --rm backend pytest -m contract

# Tests end-to-end (flujo completo)
docker compose run --rm backend pytest -m e2e
```

### Cobertura de código

La configuración en `pytest.ini` incluye `--cov=backend --cov-report=html --cov-report=term-missing`. El umbral mínimo es 75%.

```bash
# Ejecutar con cobertura (ya incluido por defecto en pytest.ini)
docker compose run --rm backend pytest --cov --cov-report=html

# Ver reporte HTML
# Abrir backend/htmlcov/index.html en el navegador
```

### Ejecutar tests localmente (si Django está instalado)

Si tenés Django y las dependencias instaladas en tu máquina:

```bash
cd backend
pytest                  # Suite completa
pytest -m unit          # Solo unitarios
./run_tests.sh          # Con --reuse-db (más rápido en iteraciones)
```

### CI/CD

Los tests se ejecutan automáticamente en GitHub Actions al hacer push o pull request a `main`. El workflow `.github/workflows/ci.yml` levanta un contenedor PostgreSQL, ejecuta migraciones y corre `pytest --cov --cov-fail-under=75`. El reporte `coverage.xml` se sube como artefacto.

### Taxonomía de marcadores

| Marcador | Descripción | ¿DB? |
|----------|-------------|------|
| `unit` | Tests unitarios puros (sin DB, sin I/O) | No |
| `integration` | Tests que interactúan con la base de datos | Sí |
| `contract` | Tests de APIs externas (mocks) | No |
| `e2e` | Tests de flujo completo | Sí |
| `slow` | Tests que tardan más de 1 segundo | Depende |

---

## 🎉 ¡Listo!

Tu instancia de ClínicaSaaS Dental MX debería estar funcionando en producción.

**URLs importantes:**
- **App**: https://clinica-dental.mx
- **API**: https://clinica-dental.mx/api/v1/
- **Admin**: https://clinica-dental.mx/admin/

**Soporte**: Abre un issue en GitHub o contacta al equipo de desarrollo.

---

## Referencias

- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Finkok API](https://www.finkok.com/)
- [Twilio WhatsApp](https://www.twilio.com/docs/whatsapp)
