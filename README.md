# Floristería Mi Lindo Jardín

Aplicación web completa, pública e informativa, para una floristería de pueblo llamada **Floristería Mi Lindo Jardín**. Incluye catálogo visual sin compra online, formulario de contacto por email y panel privado de administración.

## Características

- Parte pública con inicio, sobre la floristería, catálogo, detalle de producto y contacto.
- Catálogo informativo con búsqueda, filtro por categoría y productos destacados.
- Avisos explícitos: no hay carrito, pasarela de pago, pedidos online, compra de lotería online ni apuestas online.
- Servicio de **Loterías y Apuestas del Estado** tratado únicamente como información del servicio presencial en el local físico.
- Formulario de contacto con validación, honeypot antispam, rate limit básico y envío de email al dueño.
- Panel privado con login, logout, dashboard, CRUD de productos, subida local de imágenes e información general editable.
- Base de datos SQLite local con semillas iniciales.
- Seguridad básica: contraseñas PBKDF2, cookies HttpOnly, CSRF en formularios, validación/sanitización, cabeceras de seguridad y validación de imágenes.

## Requisitos

- Python 3.11 o superior. Se ha probado con Python 3.14.
- No requiere dependencias externas de Python; usa la biblioteca estándar.

## Instalación

```bash
cd /workspace/floristeria
cp .env.example .env
python3 -m scripts.seed
```

Edita `.env` si quieres cambiar credenciales, puerto o configuración de correo.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `PORT` | Puerto local de la web. Por defecto `3000`. |
| `APP_URL` | URL base informativa de la aplicación. |
| `DATABASE_PATH` | Ruta de SQLite. Por defecto `./data/floristeria.sqlite`. |
| `SESSION_SECRET` | Secreto para firmar sesión. Cámbialo en producción. |
| `ADMIN_EMAIL` | Email del administrador inicial. |
| `ADMIN_PASSWORD` | Contraseña del administrador inicial si todavía no existe. |
| `CONTACT_TO_EMAIL` | Email del dueño que recibirá mensajes. |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_SECURE`, `MAIL_USER`, `MAIL_PASS`, `MAIL_FROM` | Configuración SMTP opcional. |

> Si no configuras `MAIL_HOST`, el formulario de contacto funciona en modo desarrollo y guarda los mensajes en `data/mail_outbox.log`.


## Despliegue en Vercel

El repositorio incluye una entrada WSGI serverless en `api/index.py` y `vercel.json` solo reescribe todas las rutas hacia esa función, siguiendo la detección automática del runtime Python de Vercel.

### Settings del proyecto en Vercel

En **Project Settings → General** usa:

| Setting | Valor |
| --- | --- |
| Framework Preset | `Other` |
| Root Directory | `./` |
| Build Command | vacío / `None` |
| Output Directory | vacío / `None` |
| Install Command | vacío o el valor por defecto de Vercel |
| Development Command | vacío / `None` |

En **Project Settings → Environment Variables** configura al menos:

| Variable | Valor recomendado |
| --- | --- |
| `SESSION_SECRET` | Cadena larga, aleatoria y privada. |
| `APP_URL` | URL pública del proyecto, por ejemplo `https://tu-proyecto.vercel.app`. |
| `ADMIN_EMAIL` | Email del administrador inicial. |
| `ADMIN_PASSWORD` | Contraseña inicial segura. |
| `CONTACT_TO_EMAIL` | Email que recibirá los mensajes del formulario. |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_SECURE`, `MAIL_USER`, `MAIL_PASS`, `MAIL_FROM` | SMTP real si quieres envío de emails en producción. |

Notas importantes sobre Vercel:

- La base de datos SQLite se crea automáticamente en `/tmp/floristeria.sqlite` en funciones serverless. Es suficiente para demo, pero no es persistente entre redeploys o reinicios. Para producción real conviene migrar a una base de datos externa.
- Las imágenes subidas desde el panel se guardan en `/tmp/uploads`, también almacenamiento efímero. Para producción real conviene usar almacenamiento externo de archivos.
- Si ves `404: NOT_FOUND` en la URL raíz, revisa que Vercel haya desplegado este commit y que el `Root Directory` apunte a la raíz del repositorio; `vercel.json` debe estar en esa raíz.
- Después de cambiar variables de entorno en Vercel, redeploya el proyecto.

## Arranque local

```bash
python3 -m src.server
```

Después abre:

- Web pública: <http://localhost:3000>
- Login admin: <http://localhost:3000/admin/login>

## Acceso de administrador

Con la configuración por defecto de `.env.example`:

- Email: `admin@milindojardin.local`
- Contraseña: `Admin123!`

Cambia estos datos en `.env` antes de inicializar una instalación real. Si ya existe el administrador en SQLite, modificar `.env` no cambia su contraseña automáticamente.

## Gestión de productos e imágenes

Desde el panel privado puedes crear, editar, eliminar, ocultar/mostrar y destacar productos.

Las imágenes se guardan localmente en:

```text
public/uploads/
```

Validaciones aplicadas:

- Tipos permitidos: JPG, PNG, WEBP y GIF.
- Tamaño máximo: 2 MB.

## Cómo probar el formulario de contacto

1. Arranca la aplicación.
2. Abre <http://localhost:3000/contacto>.
3. Rellena nombre, email, asunto y mensaje.
4. Envía el formulario.
5. Si no tienes SMTP configurado, revisa el email generado en:

```bash
cat data/mail_outbox.log
```

## Comandos útiles

```bash
python3 -m scripts.seed       # crea tablas y datos iniciales
python3 -m src.server         # arranca la aplicación
python3 -m unittest discover  # ejecuta pruebas automatizadas
```

## Notas de producción

- Usa un `SESSION_SECRET` largo y privado.
- Configura un SMTP real para enviar correos.
- Sirve la aplicación detrás de HTTPS.
- Considera mover imágenes a almacenamiento externo si hay mucho tráfico o varios servidores.
