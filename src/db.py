from __future__ import annotations
import sqlite3, datetime
from pathlib import Path
from . import config
from .security import hash_password

CATEGORIES = ["Plantas", "Flores", "Ramos", "Centros florales", "Fuentes", "Decoración", "Loterías y Apuestas del Estado", "Otros"]

def connect() -> sqlite3.Connection:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def now() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat()

def init_db() -> None:
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS admins (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS business_info (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          phone TEXT NOT NULL,
          email TEXT NOT NULL,
          address TEXT NOT NULL,
          hours TEXT NOT NULL,
          welcome_text TEXT NOT NULL,
          services_text TEXT NOT NULL,
          maps_url TEXT DEFAULT '',
          instagram_url TEXT DEFAULT '',
          facebook_url TEXT DEFAULT '',
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          slug TEXT UNIQUE NOT NULL,
          category TEXT NOT NULL,
          description TEXT NOT NULL,
          price TEXT DEFAULT '',
          image_path TEXT DEFAULT '',
          visible INTEGER NOT NULL DEFAULT 1,
          featured INTEGER NOT NULL DEFAULT 0,
          additional_info TEXT DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contact_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL,
          phone TEXT DEFAULT '',
          subject TEXT NOT NULL,
          message TEXT NOT NULL,
          ip TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        ''')
        if not db.execute("SELECT 1 FROM admins WHERE email=?", (config.ADMIN_EMAIL,)).fetchone():
            db.execute("INSERT INTO admins (email,password_hash,created_at) VALUES (?,?,?)", (config.ADMIN_EMAIL, hash_password(config.ADMIN_PASSWORD), now()))
        if not db.execute("SELECT 1 FROM business_info WHERE id=1").fetchone():
            db.execute('''INSERT INTO business_info (id,name,description,phone,email,address,hours,welcome_text,services_text,maps_url,instagram_url,facebook_url,updated_at)
            VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)''', (
              "Floristería Mi Lindo Jardín",
              "Floristería de pueblo cercana y familiar especializada en plantas, flores frescas, ramos, centros florales, fuentes decorativas y artículos para jardín y exterior. También somos punto oficial de Loterías y Apuestas del Estado en el local físico.",
              "600 123 456", "info@milindojardin.local", "Calle Jardines, 12, 00000 Pueblo",
              "Lunes a viernes: 9:30–14:00 y 17:00–20:00 · Sábados: 9:30–14:00",
              "Bienvenidos a Floristería Mi Lindo Jardín, un rincón verde donde preparamos cada detalle con cariño y atención personalizada.",
              "Trabajamos plantas, flores, ramos por encargo, centros florales, fuentes decorativas y decoración para casa, jardín y exterior. La web es informativa: para compras o disponibilidad, contacta o visítanos en tienda.",
              "", "", "", now()))
        if not db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]:
            seed_products(db)

def seed_products(db: sqlite3.Connection) -> None:
    items = [
      ("Orquídea blanca", "Plantas", "Planta elegante para interiores luminosos, ideal para regalar o decorar una estancia especial.", "24,90 €", "/img/orquidea", 1, 1, "Disponibilidad variable según temporada."),
      ("Ramo silvestre de temporada", "Ramos", "Ramo colorido preparado con flores frescas de temporada y acabado natural.", "Desde 30 €", "/img/ramo", 1, 1, "Se personaliza en tienda según colores preferidos."),
      ("Centro floral para celebración", "Centros florales", "Centro floral decorativo para mesas, aniversarios, homenajes y ocasiones especiales.", "Consultar", "/img/centro", 1, 0, "Recomendamos encargar con antelación."),
      ("Fuente decorativa de jardín", "Fuentes", "Fuente decorativa para patios y jardines, con estilo rústico y presencia natural.", "Consultar", "/img/fuente", 1, 0, "Modelos y medidas disponibles en el local."),
      ("Macetero artesanal", "Decoración", "Macetero decorativo para plantas de interior o terraza, disponible en varios acabados.", "Desde 12 €", "/img/macetero", 1, 0, "Combina con nuestras plantas de temporada."),
      ("Servicio oficial de Loterías", "Loterías y Apuestas del Estado", "Información del servicio oficial disponible en el establecimiento físico.", "", "/img/loterias", 1, 0, "No se venden loterías ni se gestionan apuestas desde esta web. Acude al local físico para cualquier trámite oficial."),
    ]
    ts = now()
    for i, (name, cat, desc, price, image, visible, featured, extra) in enumerate(items):
        slug = slugify(name)
        db.execute('''INSERT INTO products (name,slug,category,description,price,image_path,visible,featured,additional_info,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (name, slug, cat, desc, price, image, visible, featured, extra, ts, ts))

def slugify(text: str) -> str:
    import unicodedata, re
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "producto"

def unique_slug(db: sqlite3.Connection, name: str, product_id: int | None = None) -> str:
    base = slugify(name)
    slug = base
    n = 2
    while True:
        if product_id:
            row = db.execute("SELECT id FROM products WHERE slug=? AND id<>?", (slug, product_id)).fetchone()
        else:
            row = db.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()
        if not row: return slug
        slug = f"{base}-{n}"; n += 1
