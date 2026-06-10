from __future__ import annotations
from .utils import esc
from .db import CATEGORIES

def bget(business, key: str, default: str = "") -> str:
    if not business:
        return default
    try:
        return business[key]
    except Exception:
        return getattr(business, "get", lambda _k, d="": d)(key, default)

def layout(title: str, body: str, business=None, user=False, flash: str = "", error: str = "") -> str:
    name = esc(bget(business, "name", "Floristería Mi Lindo Jardín"))
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · {name}</title><link rel="stylesheet" href="/css/styles.css"></head><body>
<header class="site-header"><a class="brand" href="/">🌿 {name}</a><button class="menu-toggle" onclick="document.body.classList.toggle('menu-open')">☰</button><nav><a href="/">Inicio</a><a href="/sobre">Sobre la floristería</a><a href="/catalogo">Catálogo</a><a href="/contacto">Contacto</a>{'<a href="/admin">Panel</a><a href="/admin/logout">Salir</a>' if user else '<a href="/admin/login">Admin</a>'}</nav></header>
<main>{('<div class="flash success">'+esc(flash)+'</div>') if flash else ''}{('<div class="flash error">'+esc(error)+'</div>') if error else ''}{body}</main>
<footer class="footer"><div><strong>{name}</strong><p>Web informativa. Sin carrito, pagos, pedidos online ni apuestas online.</p></div><div><p>{esc(bget(business, 'phone', ''))}</p><p>{esc(bget(business, 'email', ''))}</p></div></footer></body></html>'''

def product_card(p) -> str:
    badge = '<span class="badge">Destacado</span>' if p['featured'] else ''
    price = f"<p class='price'>{esc(p['price'])}</p>" if p['price'] else "<p class='muted'>Precio a consultar</p>"
    return f'''<article class="card product-card"><div class="product-img" style="background-image:url('{esc(p['image_path'] or '/img/default')}')"></div><div class="card-body">{badge}<p class="category">{esc(p['category'])}</p><h3>{esc(p['name'])}</h3><p>{esc(p['description'])}</p>{price}<a class="btn small" href="/producto/{esc(p['slug'])}">Ver detalle</a></div></article>'''

def category_options(selected="") -> str:
    return "".join(f'<option value="{esc(c)}" {"selected" if c==selected else ""}>{esc(c)}</option>' for c in CATEGORIES)
