##  Name: Temesegen Mekonnen



from flask import Flask, render_template, request, redirect, url_for, session, flash
from pathlib import Path
import json, uuid, datetime, os

app = Flask(__name__)
app.secret_key = "change-me-please"  

#      File paths 
DATA_DIR = Path("data")
PRODUCTS_FILE = DATA_DIR / "products.json"       # snapshot array of products
ORDERS_FILE   = DATA_DIR / "orders.jsonl"        # 1 JSON object per line
AUDIT_LOG     = DATA_DIR / "audit.log"           # plain text append




#  Utilities 
def ensure_files():
    """Make sure data files/folders exist so the app never crashes on first run."""
    DATA_DIR.mkdir(exist_ok=True)
    if not PRODUCTS_FILE.exists():
        PRODUCTS_FILE.write_text("[]", encoding="utf-8")
    if not ORDERS_FILE.exists():
        ORDERS_FILE.touch()
    if not AUDIT_LOG.exists():
        AUDIT_LOG.touch()

def load_products():
    """Return list of product dicts from products.json."""
    ensure_files()
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_products(products):
    """Write full snapshot to products.json (pretty for readability)."""
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

def append_jsonl(path: Path, obj: dict):
    """Append a single JSON object as one line (for orders)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def log_action(event: str, **fields):
    """Append human-readable audit entries."""
    ts = datetime.datetime.utcnow().isoformat()
    line = f"{ts} | {event} | " + ", ".join(f"{k}={v}" for k, v in fields.items())
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_cart():
    """Return the cart dict from session, always existing."""
    if "cart" not in session:
        session["cart"] = {}  # {product_id: qty}
    return session["cart"]

def cart_items_and_total():
    """Join cart with product data -> list of rows + grand total."""
    products = {p["id"]: p for p in load_products()}
    items = []
    total = 0
    for pid, qty in get_cart().items():
        p = products.get(pid)
        if not p:  # product removed from catalog
            continue
        line_total = p["price"] * qty
        items.append({"id": pid, "name": p["name"], "price": p["price"], "qty": qty,
                      "image": p.get("image"), "stock": p.get("stock", 0),
                      "line_total": line_total})
        total += line_total
    return items, total

def next_order_id():
    """Unique readable id: YYYYMMDD-HHMMSS-XXXX."""
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4].upper()

# Inject cart total into all templates (navbar)
@app.context_processor
def inject_cart_total():
    _, total = cart_items_and_total()
    return {"cart_total": total}









#        Public routes
@app.route("/")
def catalog():
    """List products with optional substring search and category filter."""
    products = load_products()
    q = (request.args.get("q") or "").strip().lower()
    cat = (request.args.get("category") or "").strip()
    def matches(p):
        ok_q = (q in p["name"].lower()) if q else True
        ok_c = (p.get("category") == cat) if cat else True
        return ok_q and ok_c
    filtered = [p for p in products if matches(p)]
    categories = sorted({p.get("category","") for p in products if p.get("category")})
    return render_template("catalog.html", products=filtered, categories=categories, q=q, cat=cat)

@app.route("/cart")
def view_cart():
    items, total = cart_items_and_total()
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add", methods=["POST"])
def cart_add():
    pid = request.form.get("product_id", "").strip()
    try:
        qty = int(request.form.get("qty", "1"))
    except ValueError:
        qty = 1
    qty = max(1, qty)

    products = {p["id"]: p for p in load_products()}
    if pid not in products:
        flash("Product not found.", "error")
        return redirect(url_for("catalog"))

    # clamp by stock (UX nicety; true check occurs again at checkout)
    stock = int(products[pid].get("stock", 0))
    cart = get_cart()
    new_qty = min(cart.get(pid, 0) + qty, stock if stock > 0 else qty)
    cart[pid] = new_qty
    session.modified = True

    log_action("add_to_cart", product_id=pid, qty=qty, new_qty=new_qty)
    flash("Item added to cart.", "ok")
    return redirect(url_for("view_cart"))

@app.route("/cart/update", methods=["POST"])
def cart_update():
    pid = request.form.get("product_id", "").strip()
    try:
        qty = int(request.form.get("qty", "0"))
    except ValueError:
        qty = 0

    cart = get_cart()
    if qty <= 0:
        cart.pop(pid, None)
        log_action("remove_from_cart", product_id=pid)
    else:
        cart[pid] = qty
        log_action("update_cart", product_id=pid, qty=qty)
    session.modified = True
    return redirect(url_for("view_cart"))

@app.route("/checkout")
def checkout_form():
    items, total = cart_items_and_total()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("catalog"))
    return render_template("checkout.html")

@app.route("/checkout", methods=["POST"])
def checkout_submit():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    address = (request.form.get("address") or "").strip()

    if not (name and email and address):
        flash("All fields are required.", "error")
        return redirect(url_for("checkout_form"))

    # Validate stock at this moment
    products = load_products()
    p_by_id = {p["id"]: p for p in products}
    items_in_cart, total = cart_items_and_total()
    if not items_in_cart:
        flash("Your cart is empty.", "error")
        return redirect(url_for("catalog"))

    for item in items_in_cart:
        if item["qty"] > p_by_id[item["id"]].get("stock", 0):
            flash(f"Insufficient stock for {item['name']}.", "error")
            return redirect(url_for("view_cart"))

    # Build order object
    oid = next_order_id()
    order = {
        "id": oid,
        "buyer": {"name": name, "email": email, "address": address},
        "items": [{"id": it["id"], "name": it["name"], "price": it["price"], "qty": it["qty"]} for it in items_in_cart],
        "total": total,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    append_jsonl(ORDERS_FILE, order)

    # Reduce stock and save products
    for it in items_in_cart:
        p_by_id[it["id"]]["stock"] = p_by_id[it["id"]].get("stock", 0) - it["qty"]
    save_products(list(p_by_id.values()))

    # Clear cart, log, redirect
    session["cart"] = {}
    session["last_order_id"] = oid
    log_action("checkout", order_id=oid, total=total, items=len(order["items"]))
    flash("Order placed!", "ok")
    return redirect(url_for("order_summary", order_id=oid))

@app.route("/order/<order_id>")
def order_summary(order_id):
    """Find the order in orders.jsonl (scan from end) and show summary."""
    found = None
    # read file backwards cheaply
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        try:
            obj = json.loads(line)
            if obj.get("id") == order_id:
                found = obj
                break
        except json.JSONDecodeError:
            continue
    if not found:
        flash("Order not found.", "error")
        return redirect(url_for("catalog"))
    return render_template("order_summary.html", order=found)




# Admin (hardcoded) 
ADMIN = {"user": "admin", "pass": "12345"}

def require_admin():
    if not session.get("is_admin"):
        return False
    return True

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u == ADMIN["user"] and p == ADMIN["pass"]:
            session["is_admin"] = True
            log_action("admin_login", user=u, ok=True)
            return redirect(url_for("admin_products"))
        else:
            log_action("admin_login", user=u, ok=False)
            flash("Invalid credentials", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out.", "ok")
    return redirect(url_for("catalog"))

@app.route("/admin/products")
def admin_products():
    if not require_admin():
        return redirect(url_for("admin_login"))
    products = load_products()
    return render_template("admin_products.html", products=products)

@app.route("/admin/products", methods=["POST"])
def admin_products_post():
    if not require_admin():
        return redirect(url_for("admin_login"))

    # Read fields
    pid = (request.form.get("id") or "").strip()  # optional for update
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    image = (request.form.get("image") or "").strip()

    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Price/stock must be numeric.", "error")
        return redirect(url_for("admin_products"))

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("admin_products"))
    if price < 0 or stock < 0:
        flash("Price and stock must be >= 0.", "error")
        return redirect(url_for("admin_products"))

    products = load_products()
    by_id = {p["id"]: p for p in products}

    # Create or update
    if pid and pid in by_id:
        p = by_id[pid]
        p.update({"name": name, "price": price, "stock": stock,
                  "category": category, "image": image})
        log_action("admin_update_product", product_id=pid)
    else:
        # generate id if not given or unknown
        pid = pid or ("P-" + uuid.uuid4().hex[:6].upper())
        products.append({"id": pid, "name": name, "price": price, "stock": stock,
                         "category": category, "image": image})
        log_action("admin_add_product", product_id=pid)

    save_products(products)
    flash("Saved.", "ok")
    return redirect(url_for("admin_products"))

if __name__ == "__main__":
    ensure_files()
    app.run(debug=True)
