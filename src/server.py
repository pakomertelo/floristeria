from __future__ import annotations
import json, mimetypes, os, re, time, traceback
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from . import config
from .db import connect, init_db, CATEGORIES, now, unique_slug
from .security import COOKIE_NAME, make_session, read_session, csrf_token, constant_time_equal, verify_password
from .templates import layout, product_card, category_options
from .utils import esc, clean, is_email, parse_urlencoded, parse_multipart, save_image
from .emailer import send_contact_email, EmailError

class App(BaseHTTPRequestHandler):
    server_version = "MiLindoJardin/1.0"
    csrf_store: dict[str, tuple[str, float]] = {}
    contact_hits: dict[str, list[float]] = {}

    def log_message(self, fmt, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), fmt % args))

    @property
    def user_id(self):
        return read_session(self.headers.get("Cookie"))

    def db(self):
        return connect()

    def business(self):
        with self.db() as db:
            return db.execute("SELECT * FROM business_info WHERE id=1").fetchone()

    def send_html(self, html: str, status=200, headers=None):
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.security_headers()
        for k, v in (headers or {}).items(): self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def redirect(self, to: str, cookie: str | None = None):
        self.send_response(303); self.security_headers(); self.send_header("Location", to)
        if cookie: self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")

    def not_found(self):
        self.send_html(layout("No encontrado", "<section class='page'><h1>Página no encontrada</h1><p>La página solicitada no existe.</p><a class='btn' href='/'>Volver al inicio</a></section>", self.business(), bool(self.user_id)), 404)

    def error_page(self):
        self.send_html(layout("Error", "<section class='page'><h1>Ha ocurrido un error</h1><p>No se han mostrado detalles internos por seguridad.</p></section>", self.business(), bool(self.user_id)), 500)

    def parse_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            return parse_multipart(body, ctype)
        return parse_urlencoded(body), {}

    def new_csrf(self):
        token = csrf_token(); self.csrf_store[token] = (self.client_address[0], time.time()); return token

    def check_csrf(self, token):
        item = self.csrf_store.pop(token or "", None)
        return bool(item and item[0] == self.client_address[0] and time.time() - item[1] < 7200)

    def require_admin(self):
        if not self.user_id:
            self.redirect("/admin/login?next=" + urlparse(self.path).path); return False
        return True

    def do_GET(self):
        try:
            path = urlparse(self.path).path
            if path.startswith("/css/") or path.startswith("/uploads/"):
                return self.static(path)
            if path.startswith("/img/"):
                return self.placeholder(path)
            routes = {
                "/": self.home, "/sobre": self.about, "/catalogo": self.catalog, "/contacto": self.contact,
                "/admin/login": self.login, "/admin/logout": self.logout, "/admin": self.admin_dashboard,
                "/admin/productos": self.admin_products, "/admin/productos/nuevo": self.admin_product_form,
                "/admin/info": self.admin_info_form,
            }
            if path in routes: return routes[path]()
            if path.startswith("/producto/"): return self.product_detail(path.rsplit("/",1)[1])
            if path.startswith("/admin/productos/") and path.endswith("/editar"):
                return self.admin_product_form(int(path.split("/")[3]))
            self.not_found()
        except Exception:
            traceback.print_exc(); self.error_page()

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            if path == "/contacto": return self.contact_submit()
            if path == "/admin/login": return self.login_submit()
            if not self.require_admin(): return
            if path == "/admin/productos/nuevo": return self.product_save()
            if path.startswith("/admin/productos/") and path.endswith("/editar"):
                return self.product_save(int(path.split("/")[3]))
            if path.startswith("/admin/productos/") and path.endswith("/eliminar"):
                return self.product_delete(int(path.split("/")[3]))
            if path == "/admin/info": return self.info_save()
            self.not_found()
        except Exception:
            traceback.print_exc(); self.error_page()

    def static(self, path):
        rel = path.lstrip("/")
        file = config.PUBLIC_DIR / rel
        if not file.resolve().is_relative_to(config.PUBLIC_DIR.resolve()) or not file.exists(): return self.not_found()
        data = file.read_bytes(); self.send_response(200); self.security_headers()
        self.send_header("Content-Type", mimetypes.guess_type(str(file))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def placeholder(self, path):
        colors = {"orquidea":"f8d7e8", "ramo":"f6b0c9", "centro":"d7a86e", "fuente":"b7d7d8", "macetero":"d9b88f", "loterias":"d9eed3", "default":"e8f2df"}
        key = path.rsplit("/",1)[-1]; color = colors.get(key, colors["default"])
        label = esc(key.replace('-', ' ').title())
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="620" viewBox="0 0 900 620"><rect width="900" height="620" fill="#{color}"/><circle cx="145" cy="120" r="80" fill="#fff" opacity=".45"/><circle cx="755" cy="500" r="105" fill="#fff" opacity=".35"/><path d="M210 410 C330 250 470 500 650 250" fill="none" stroke="#527a42" stroke-width="22" stroke-linecap="round" opacity=".75"/><text x="450" y="315" text-anchor="middle" font-family="Georgia,serif" font-size="52" fill="#31522c">{label}</text><text x="450" y="375" text-anchor="middle" font-family="Arial" font-size="24" fill="#6c4f35">Floristería Mi Lindo Jardín</text></svg>'''.encode()
        self.send_response(200); self.security_headers(); self.send_header("Content-Type", "image/svg+xml"); self.send_header("Content-Length", str(len(svg))); self.end_headers(); self.wfile.write(svg)

    def home(self):
        b = self.business()
        with self.db() as db:
            featured = db.execute("SELECT * FROM products WHERE visible=1 AND featured=1 ORDER BY updated_at DESC LIMIT 3").fetchall()
        cards = ''.join(product_card(p) for p in featured)
        body = f'''<section class="hero"><div><p class="eyebrow">Floristería local · Jardín · Decoración</p><h1>{esc(b['name'])}</h1><p>{esc(b['welcome_text'])}</p><div class="hero-actions"><a class="btn" href="/catalogo">Ver catálogo informativo</a><a class="btn secondary" href="/contacto">Contactar</a></div></div></section><section class="notice"><strong>Web informativa:</strong> no hay carrito, pagos, pedidos online, compra de lotería ni apuestas online. Para comprar o consultar disponibilidad, contacta o acude al local.</section><section class="services"><h2>Qué encontrarás en tienda</h2><div class="grid six">{''.join(f'<div class="mini"><span>{icon}</span><strong>{txt}</strong></div>' for icon,txt in [('🪴','Plantas'),('🌷','Flores'),('💐','Ramos'),('🌺','Centros florales'),('⛲','Fuentes'),('🎍','Decoración')])}</div></section><section><h2>Productos destacados</h2><div class="grid cards">{cards}</div></section>'''
        self.send_html(layout("Inicio", body, b, bool(self.user_id)))

    def about(self):
        b = self.business()
        body = f'''<section class="page"><h1>Sobre la floristería</h1><div class="two"><div><p>{esc(b['description'])}</p><p>{esc(b['services_text'])}</p><div class="warm"><h2>Trato cercano</h2><p>Escuchamos cada encargo con calma para ayudarte a elegir plantas, flores o decoración según la ocasión, el espacio y el presupuesto.</p></div></div><aside class="info"><h2>Datos del local</h2><p><strong>Dirección:</strong> {esc(b['address'])}</p><p><strong>Horario:</strong> {esc(b['hours'])}</p><p><strong>Teléfono:</strong> {esc(b['phone'])}</p><p><strong>Email:</strong> {esc(b['email'])}</p><p><strong>Loterías:</strong> servicio oficial exclusivamente presencial en el local físico.</p></aside></div></section>'''
        self.send_html(layout("Sobre la floristería", body, b, bool(self.user_id)))

    def catalog(self):
        b = self.business(); qs = parse_qs(urlparse(self.path).query); q=clean(qs.get('q',[''])[0],80); cat=clean(qs.get('categoria',[''])[0],80)
        sql="SELECT * FROM products WHERE visible=1"; params=[]
        if q: sql += " AND name LIKE ?"; params.append(f"%{q}%")
        if cat in CATEGORIES: sql += " AND category=?"; params.append(cat)
        sql += " ORDER BY featured DESC, updated_at DESC"
        with self.db() as db: products=db.execute(sql, params).fetchall()
        cards = ''.join(product_card(p) for p in products) or '<p class="empty">No hay productos visibles con esos filtros.</p>'
        body=f'''<section class="page"><h1>Catálogo informativo</h1><p>Explora algunos productos y servicios disponibles. La compra y disponibilidad se consultan por contacto directo o en tienda.</p><form class="filters" method="get"><input name="q" value="{esc(q)}" placeholder="Buscar por nombre"><select name="categoria"><option value="">Todas las categorías</option>{category_options(cat)}</select><button class="btn" type="submit">Filtrar</button></form><div class="grid cards">{cards}</div></section>'''
        self.send_html(layout("Catálogo", body, b, bool(self.user_id)))

    def product_detail(self, slug):
        b=self.business()
        with self.db() as db: p=db.execute("SELECT * FROM products WHERE slug=? AND visible=1", (slug,)).fetchone()
        if not p: return self.not_found()
        loteria = p['category'] == 'Loterías y Apuestas del Estado'
        body=f'''<section class="page product-detail"><div class="detail-img" style="background-image:url('{esc(p['image_path'] or '/img/default')}')"></div><div><p class="category">{esc(p['category'])}</p><h1>{esc(p['name'])}</h1><p class="price">{esc(p['price'] or 'Precio a consultar')}</p><p>{esc(p['description'])}</p>{('<div class="warm"><strong>Información adicional</strong><p>'+esc(p['additional_info'])+'</p></div>') if p['additional_info'] else ''}<div class="notice"><strong>Importante:</strong> esta página es solo informativa. {'No se permite comprar lotería, apostar ni reservar boletos desde la web; el servicio se atiende únicamente en el local físico.' if loteria else 'Para comprar o consultar disponibilidad, contacta con la floristería o acude al local físico.'}</div><a class="btn" href="/contacto">Consultar</a></div></section>'''
        self.send_html(layout(p['name'], body, b, bool(self.user_id)))

    def contact(self, msg='', err=''):
        b=self.business(); token=self.new_csrf()
        maps = f'<a class="btn secondary" href="{esc(b["maps_url"])}" target="_blank" rel="noopener">Ver en Google Maps</a>' if b['maps_url'] else ''
        body=f'''<section class="page"><h1>Contacto</h1><div class="two"><aside class="info"><p><strong>Teléfono:</strong> {esc(b['phone'])}</p><p><strong>Email:</strong> {esc(b['email'])}</p><p><strong>Dirección:</strong> {esc(b['address'])}</p><p><strong>Horario:</strong> {esc(b['hours'])}</p>{maps}</aside><form class="form" method="post" action="/contacto"><input type="hidden" name="csrf" value="{token}"><input class="hp" name="website" tabindex="-1" autocomplete="off"><label>Nombre*<input name="name" required></label><label>Email*<input name="email" type="email" required></label><label>Teléfono<input name="phone"></label><label>Asunto*<input name="subject" required></label><label>Mensaje*<textarea name="message" required minlength="10"></textarea></label><button class="btn" type="submit">Enviar mensaje</button><p class="muted">El mensaje se envía al dueño por email. En desarrollo se guarda en data/mail_outbox.log si no configuras SMTP.</p></form></div></section>'''
        self.send_html(layout("Contacto", body, b, bool(self.user_id), msg, err))

    def contact_submit(self):
        fields,_=self.parse_body(); ip=self.client_address[0]; hits=[t for t in self.contact_hits.get(ip,[]) if time.time()-t<300]
        if len(hits)>=3: return self.contact(err="Demasiados intentos. Prueba de nuevo en unos minutos.")
        if fields.get('website'): return self.contact(msg="Mensaje enviado correctamente.")
        if not self.check_csrf(fields.get('csrf')): return self.contact(err="La sesión del formulario ha caducado. Inténtalo de nuevo.")
        data={k: clean(fields.get(k,''), 3000 if k=='message' else 180) for k in ['name','email','phone','subject','message']}
        errors=[]
        if not data['name'] or not data['subject'] or len(data['message'])<10: errors.append("Completa los campos obligatorios.")
        if not is_email(data['email']): errors.append("Introduce un email válido.")
        if errors: return self.contact(err=" ".join(errors))
        try: send_contact_email(data)
        except EmailError: return self.contact(err="No se pudo enviar el mensaje. Inténtalo más tarde o llama por teléfono.")
        with self.db() as db: db.execute("INSERT INTO contact_messages (name,email,phone,subject,message,ip,created_at) VALUES (?,?,?,?,?,?,?)", (data['name'],data['email'],data['phone'],data['subject'],data['message'],ip,now()))
        hits.append(time.time()); self.contact_hits[ip]=hits
        return self.contact(msg="Mensaje enviado correctamente. Gracias por contactar con la floristería.")

    def login(self, err=''):
        b=self.business(); token=self.new_csrf(); body=f'''<section class="page narrow"><h1>Acceso administrador</h1><form class="form" method="post"><input type="hidden" name="csrf" value="{token}"><label>Email<input name="email" type="email" required></label><label>Contraseña<input name="password" type="password" required></label><button class="btn">Entrar</button></form></section>'''
        self.send_html(layout("Login", body, b, False, '', err))

    def login_submit(self):
        f,_=self.parse_body()
        if not self.check_csrf(f.get('csrf')): return self.login("Formulario caducado.")
        with self.db() as db: admin=db.execute("SELECT * FROM admins WHERE email=?", (clean(f.get('email',''),180),)).fetchone()
        if not admin or not verify_password(f.get('password',''), admin['password_hash']): return self.login("Credenciales incorrectas.")
        secure = "; Secure" if os.getenv('NODE_ENV') == 'production' else ''
        self.redirect("/admin", f"{COOKIE_NAME}={make_session(admin['id'])}; HttpOnly; SameSite=Lax; Path=/{secure}")

    def logout(self):
        self.redirect("/", f"{COOKIE_NAME}=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/")

    def admin_dashboard(self):
        if not self.require_admin(): return
        b=self.business()
        with self.db() as db:
            stats=db.execute("SELECT COUNT(*) total, SUM(visible=1) visibles, SUM(visible=0) ocultos FROM products").fetchone()
        body=f'''<section class="page"><h1>Panel de administración</h1><div class="grid three"><div class="stat"><strong>{stats['total'] or 0}</strong><span>Total productos</span></div><div class="stat"><strong>{stats['visibles'] or 0}</strong><span>Visibles</span></div><div class="stat"><strong>{stats['ocultos'] or 0}</strong><span>Ocultos</span></div></div><div class="admin-actions"><a class="btn" href="/admin/productos/nuevo">Crear producto</a><a class="btn secondary" href="/admin/productos">Gestionar productos</a><a class="btn secondary" href="/admin/info">Editar información general</a></div></section>'''
        self.send_html(layout("Admin", body, b, True))

    def admin_products(self):
        if not self.require_admin(): return
        b=self.business()
        with self.db() as db: products=db.execute("SELECT * FROM products ORDER BY updated_at DESC").fetchall()
        rows=''.join(f'''<tr><td>{esc(p['name'])}</td><td>{esc(p['category'])}</td><td>{esc(p['price'])}</td><td>{'Visible' if p['visible'] else 'Oculto'}</td><td>{'Sí' if p['featured'] else 'No'}</td><td><a href="/admin/productos/{p['id']}/editar">Editar</a><form method="post" action="/admin/productos/{p['id']}/eliminar" onsubmit="return confirm('¿Eliminar producto?')"><input type="hidden" name="csrf" value="{self.new_csrf()}"><button class="link-danger">Eliminar</button></form></td></tr>''' for p in products)
        body=f'''<section class="page"><h1>Productos</h1><a class="btn" href="/admin/productos/nuevo">Nuevo producto</a><div class="table-wrap"><table><thead><tr><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Estado</th><th>Destacado</th><th>Acciones</th></tr></thead><tbody>{rows}</tbody></table></div></section>'''
        self.send_html(layout("Gestionar productos", body, b, True))

    def admin_product_form(self, product_id=None, err=''):
        if not self.require_admin(): return
        b=self.business(); p=None
        if product_id:
            with self.db() as db: p=db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not p: return self.not_found()
        token=self.new_csrf(); action="/admin/productos/nuevo" if not p else f"/admin/productos/{p['id']}/editar"
        body=f'''<section class="page"><h1>{'Editar' if p else 'Nuevo'} producto</h1><form class="form" method="post" enctype="multipart/form-data" action="{action}"><input type="hidden" name="csrf" value="{token}"><label>Nombre*<input name="name" required value="{esc(p['name'] if p else '')}"></label><label>Categoría*<select name="category">{category_options(p['category'] if p else 'Plantas')}</select></label><label>Descripción*<textarea name="description" required>{esc(p['description'] if p else '')}</textarea></label><label>Precio<input name="price" value="{esc(p['price'] if p else '')}" placeholder="Ej. 24,90 € o Consultar"></label><label>Imagen<input type="file" name="image" accept="image/png,image/jpeg,image/webp,image/gif"></label><label>Información adicional<textarea name="additional_info">{esc(p['additional_info'] if p else '')}</textarea></label><div class="checks"><label><input type="checkbox" name="visible" {'checked' if (not p or p['visible']) else ''}> Visible</label><label><input type="checkbox" name="featured" {'checked' if (p and p['featured']) else ''}> Destacado</label></div><button class="btn">Guardar</button></form></section>'''
        self.send_html(layout("Producto", body, b, True, '', err))

    def product_save(self, product_id=None):
        fields,files=self.parse_body()
        if not self.check_csrf(fields.get('csrf')): return self.admin_product_form(product_id, "Formulario caducado.")
        data={k: clean(fields.get(k,''), 3000 if k in ['description','additional_info'] else 180) for k in ['name','category','description','price','additional_info']}
        if not data['name'] or not data['description'] or data['category'] not in CATEGORIES:
            return self.admin_product_form(product_id, "Revisa nombre, categoría y descripción.")
        image_path, img_err = save_image(files.get('image'))
        if img_err: return self.admin_product_form(product_id, img_err)
        visible=1 if fields.get('visible') else 0; featured=1 if fields.get('featured') else 0
        with self.db() as db:
            slug=unique_slug(db, data['name'], product_id)
            if product_id:
                current=db.execute("SELECT image_path FROM products WHERE id=?", (product_id,)).fetchone()
                final_image=image_path or (current['image_path'] if current else '')
                db.execute('''UPDATE products SET name=?,slug=?,category=?,description=?,price=?,image_path=?,visible=?,featured=?,additional_info=?,updated_at=? WHERE id=?''', (data['name'],slug,data['category'],data['description'],data['price'],final_image,visible,featured,data['additional_info'],now(),product_id))
            else:
                db.execute('''INSERT INTO products (name,slug,category,description,price,image_path,visible,featured,additional_info,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (data['name'],slug,data['category'],data['description'],data['price'],image_path,visible,featured,data['additional_info'],now(),now()))
        self.redirect("/admin/productos")

    def product_delete(self, product_id):
        f,_=self.parse_body()
        if not self.check_csrf(f.get('csrf')): return self.redirect('/admin/productos')
        with self.db() as db: db.execute("DELETE FROM products WHERE id=?", (product_id,))
        self.redirect("/admin/productos")

    def admin_info_form(self, err=''):
        if not self.require_admin(): return
        b=self.business(); token=self.new_csrf()
        fields=['name','description','phone','email','address','hours','welcome_text','services_text','maps_url','instagram_url','facebook_url']
        labels={'name':'Nombre comercial','description':'Descripción','phone':'Teléfono','email':'Email','address':'Dirección','hours':'Horario','welcome_text':'Texto de bienvenida','services_text':'Servicios','maps_url':'Google Maps','instagram_url':'Instagram','facebook_url':'Facebook'}
        inputs=''.join(f'<label>{labels[k]}<textarea name="{k}" required>{esc(b[k])}</textarea></label>' if k in ['description','welcome_text','services_text','hours'] else f'<label>{labels[k]}<input name="{k}" value="{esc(b[k])}" {"required" if k in ["name","phone","email","address"] else ""}></label>' for k in fields)
        body=f'''<section class="page"><h1>Información general</h1><form class="form" method="post"><input type="hidden" name="csrf" value="{token}">{inputs}<button class="btn">Guardar información</button></form></section>'''
        self.send_html(layout("Información general", body, b, True, '', err))

    def info_save(self):
        f,_=self.parse_body()
        if not self.check_csrf(f.get('csrf')): return self.admin_info_form("Formulario caducado.")
        data={k: clean(f.get(k,''), 3000) for k in ['name','description','phone','email','address','hours','welcome_text','services_text','maps_url','instagram_url','facebook_url']}
        if not data['name'] or not is_email(data['email']): return self.admin_info_form("Nombre y email válido son obligatorios.")
        with self.db() as db:
            db.execute('''UPDATE business_info SET name=?,description=?,phone=?,email=?,address=?,hours=?,welcome_text=?,services_text=?,maps_url=?,instagram_url=?,facebook_url=?,updated_at=? WHERE id=1''', (*[data[k] for k in ['name','description','phone','email','address','hours','welcome_text','services_text','maps_url','instagram_url','facebook_url']], now()))
        self.redirect('/admin')

def main():
    init_db(); config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", config.PORT), App)
    print(f"Floristería Mi Lindo Jardín disponible en http://localhost:{config.PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()
