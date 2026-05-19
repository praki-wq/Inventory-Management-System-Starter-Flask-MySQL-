from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
import csv
from flask import Response
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# -----------------------------
# Flask App Configuration
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'devsecret')

# Upload settings
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database settings
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'inventorydb'),
    'autocommit': False
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# -----------------------------
# Login Required Decorator
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login_user'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# User Authentication Routes
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        flash('You are already logged in!', 'info')
        return redirect(url_for('products'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            flash('User registered successfully!', 'success')
            return redirect(url_for('login_user'))
        except mysql.connector.IntegrityError:
            flash('Username already exists!', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login_user():
    if 'user_id' in session:
        flash('You are already logged in!', 'info')
        return redirect(url_for('products'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('products'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # clears login session
    flash('Logged out successfully', 'info')
    return redirect(url_for('login_user'))

# -----------------------------
# Inventory Product Routes
# -----------------------------
@app.route('/')
def index():
    return redirect(url_for('products'))

@app.route('/products')
@login_required
def products():
    # Get filters from query parameters
    category = request.args.get('category', '')
    stock = request.args.get('stock', '')
    sort_by = request.args.get('sort_by', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Base query
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    # Filter by category
    if category:
        query += " AND category=%s"
        params.append(category)

    # Filter by stock level
    if stock == 'low':
        query += " AND quantity <= reorder_level"
    elif stock == 'in_stock':
        query += " AND quantity > reorder_level"

    # Sorting
    if sort_by == 'name_asc':
        query += " ORDER BY name ASC"
    elif sort_by == 'name_desc':
        query += " ORDER BY name DESC"
    elif sort_by == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY price DESC"
    elif sort_by == 'stock_asc':
        query += " ORDER BY quantity ASC"
    elif sort_by == 'stock_desc':
        query += " ORDER BY quantity DESC"
    else:
        query += " ORDER BY id DESC"

    cursor.execute(query, params)
    products = cursor.fetchall()

    # Get unique categories for the filter dropdown
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = [row['category'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template('products.html',
                           products=products,
                           total_products=len(products),
                           low_stock=sum(1 for p in products if p['quantity'] <= p['reorder_level']),
                           categories_count=len(categories),
                           categories=categories,
                           selected_category=category,
                           selected_stock=stock,
                           selected_sort=sort_by)


@app.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        subject = request.form['subject']
        message = request.form['message']
        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO support_tickets (user_id, subject, message) VALUES (%s, %s, %s)",
            (user_id, subject, message)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Support ticket submitted successfully!', 'success')
        return redirect(url_for('support'))

    return render_template('support.html')
@app.route('/support/tickets')
@login_required
def view_tickets():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # If admin, show all tickets
    if session.get('is_admin'):
        cursor.execute("SELECT t.*, u.username FROM support_tickets t JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC")
    else:
        cursor.execute("SELECT * FROM support_tickets WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
    
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tickets.html', tickets=tickets)
@app.route('/support/tickets/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    if not session.get('is_admin'):
        flash("Access denied.", "danger")
        return redirect(url_for('view_tickets'))

    status = request.form['status']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE support_tickets SET status=%s WHERE id=%s", (status, ticket_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Ticket status updated.", "success")
    return redirect(url_for('view_tickets'))


@app.route('/products/add', methods=['GET','POST'])
@login_required
def add_product():
    if request.method == 'POST':
        sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        quantity = request.form.get('quantity') or 0
        reorder_level = request.form.get('reorder_level') or 0
        price = request.form.get('price') or 0.0

        # Image Upload
        image_file = request.files.get('image')
        image_url = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            image_url = f"uploads/{filename}"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (sku, name, description, category, quantity, reorder_level, price, last_updated, image_url) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (sku, name, description, category, int(quantity), int(reorder_level), float(price), datetime.utcnow(), image_url)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product added successfully', 'success')
        return redirect(url_for('products'))

    return render_template('product_form.html', action='Add', product=None)

@app.route('/products/edit/<int:pid>', methods=['GET','POST'])
@login_required
def edit_product(pid):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        quantity = request.form.get('quantity') or 0
        reorder_level = request.form.get('reorder_level') or 0
        price = request.form.get('price') or 0.0

        # Image Upload
        image_file = request.files.get('image')
        image_url = request.form.get('current_image')  # keep existing if no new upload
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            image_url = f"uploads/{filename}"

        cursor.execute(
            "UPDATE products SET sku=%s, name=%s, description=%s, category=%s, quantity=%s, reorder_level=%s, price=%s, last_updated=%s, image_url=%s WHERE id=%s",
            (sku, name, description, category, int(quantity), int(reorder_level), float(price), datetime.utcnow(), image_url, pid)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product updated successfully', 'success')
        return redirect(url_for('products'))

    cursor.execute("SELECT * FROM products WHERE id=%s", (pid,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('products'))
    return render_template('product_form.html', action='Edit', product=product)

@app.route('/products/delete/<int:pid>', methods=['POST'])
@login_required
def delete_product(pid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Product removed', 'info')
    return redirect(url_for('products'))

@app.route('/reports/low-stock')
@login_required
def low_stock_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE quantity <= reorder_level ORDER BY quantity ASC")
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('report_low_stock.html', products=items)

# -----------------------------
# Export CSV Route
# -----------------------------
@app.route('/export/csv')
@login_required
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    # Create CSV in memory
    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'SKU', 'Name', 'Category', 'Description', 'Quantity', 'Price', 'Last Updated'])
    for p in products:
        writer.writerow([p['id'], p['sku'], p['name'], p['category'], p['description'], p['quantity'], p['price'], p['last_updated']])
    output.seek(0)

    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=products.csv"})


# -----------------------------
# Export PDF Route
# -----------------------------
@app.route('/export/pdf')
@login_required
def export_pdf():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    output = BytesIO()
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Product List")
    c.setFont("Helvetica", 12)
    y -= 30

    for p in products:
        text = f"{p['id']}. {p['name']} ({p['category']}) - Stock: {p['quantity']} - Price: ${p['price']}"
        c.drawString(50, y, text)
        y -= 20
        if y < 50:  # New page
            c.showPage()
            y = height - 50

    c.save()
    output.seek(0)

    return Response(output, mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=products.pdf"})


# -----------------------------
# Run Flask App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
