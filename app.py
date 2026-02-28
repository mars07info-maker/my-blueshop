from flask import Flask, render_template, session, redirect, url_for, request, flash
import os
import json
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"

# upload configuration (place uploads under static so Flask can serve them)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# orders folder to store each order as a JSON file
ORDERS_FOLDER = os.path.join(os.path.dirname(__file__), 'orders')
os.makedirs(ORDERS_FOLDER, exist_ok=True)

PRODUCTS = [
    {
        "id": 1,
        "name": "Modern Wireless Headphones",
        "price": 150.00,
        "desc": "High-fidelity over-ear wireless headphones",
        "image": "https://images.unsplash.com/photo-1518449074331-5eacb3db855a?auto=format&fit=crop&w=400&q=80"
    },
    {
        "id": 2,
        "name": "Smart Fitness Watch",
        "price": 200.00,
        "desc": "Track your health and workouts seamlessly",
        "image": "https://images.unsplash.com/photo-1598970434795-0c54fe7c0649?auto=format&fit=crop&w=400&q=80"
    },
    {
        "id": 3,
        "name": "Leather Laptop Bag",
        "price": 85.00,
        "desc": "Stylish and durable carry-all for your laptop",
        "image": "https://images.unsplash.com/photo-1513116476489-7635e79feb27?auto=format&fit=crop&w=400&q=80"
    },
]


def get_product(product_id):
    for p in PRODUCTS:
        if p["id"] == product_id:
            return p
    return None


def get_cart():
    return session.setdefault("cart", {})


def load_all_orders():
    """Load all orders from the orders folder and return as a list."""
    orders = []
    if os.path.exists(ORDERS_FOLDER):
        for filename in os.listdir(ORDERS_FOLDER):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(ORDERS_FOLDER, filename), 'r') as f:
                        order = json.load(f)
                        orders.append(order)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    return sorted(orders, key=lambda x: x.get('order_id', ''), reverse=True)


def is_admin_logged_in():
    """Check if user is logged in as admin."""
    return session.get('admin_logged_in', False)


def cart_items():
    cart = get_cart()
    items = []
    total = 0.0
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        p = get_product(pid)
        if not p:
            continue
        subtotal = p["price"] * qty
        items.append({"product": p, "qty": qty, "subtotal": subtotal})
        total += subtotal
    return items, total


@app.route("/")
def index():
    return render_template("index.html", products=PRODUCTS)


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    pid = int(request.form.get("product_id"))
    qty = int(request.form.get("quantity", 1))
    cart = get_cart()
    cart[str(pid)] = cart.get(str(pid), 0) + qty
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/update_cart", methods=["POST"])
def update_cart():
    pid = int(request.form.get("product_id"))
    qty = int(request.form.get("quantity", 0))
    cart = get_cart()
    if qty <= 0:
        cart.pop(str(pid), None)
    else:
        cart[str(pid)] = qty
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/remove/<int:product_id>")
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = cart_items()
    if request.method == "POST":
        # gather form data
        name = request.form.get('name')
        address = request.form.get('address')
        phone = request.form.get('phone')

        # handle screenshot upload
        screenshot = request.files.get('screenshot')
        screenshot_filename = None
        if screenshot and screenshot.filename:
            filename = secure_filename(screenshot.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            screenshot.save(os.path.join(app.config['UPLOAD_FOLDER'], unique))
            screenshot_filename = unique

        # generate order id
        order_id = uuid.uuid4().hex[:8]

        # transform items into JSON-serializable format
        items_serializable = [
            {
                'name': item['product']['name'],
                'qty': item['qty'],
                'price': item['product']['price'],
                'subtotal': item['subtotal']
            }
            for item in items
        ]

        # build order object
        order = {
            'order_id': order_id,
            'name': name,
            'address': address,
            'phone': phone,
            'order_items': items_serializable,
            'total': total,
            'screenshot': screenshot_filename
        }
        
        # save order to individual JSON file in orders folder
        order_file = os.path.join(ORDERS_FOLDER, f"{order_id}.json")
        with open(order_file, 'w') as f:
            json.dump(order, f, indent=2)

        # clear cart
        session.pop('cart', None)
        return render_template('success.html', order=order)
    return render_template("checkout.html", total=total)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        # simple hardcoded credentials
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('admin_login.html')


@app.route("/admin")
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    orders = load_all_orders()
    return render_template('admin_dashboard.html', orders=orders)


@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
