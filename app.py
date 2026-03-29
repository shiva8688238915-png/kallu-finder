from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import math

app = Flask(__name__)
app.secret_key = "kallu_finder_secure_key"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# ------------------------------
# DATABASE UTILITIES
# -------------------------------
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT NOT NULL,
            price REAL,
            latitude REAL,
            longitude REAL,
            verified INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Available'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------------------
# DISTANCE CALCULATION
# -------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        # Explicitly convert everything to float to avoid math errors
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        R = 6371 
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(d_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except (ValueError, TypeError, ZeroDivisionError):
        return 99999

# -------------------------------
# ADMIN ROUTES
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        flash("Invalid Admin Credentials", "danger")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    sellers = conn.execute("SELECT * FROM sellers").fetchall()
    conn.close()
    return render_template('admin.html', sellers=sellers)

@app.route('/add_seller', methods=['POST'])
def add_seller():
    if not session.get('admin'): return "Unauthorized", 401
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO sellers (name, address, phone, price, latitude, longitude, verified, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'Available')
        ''', (request.form.get('name'), request.form.get('address'), request.form.get('phone'), 
              request.form.get('price'), float(request.form.get('lat')), float(request.form.get('lon'))))
        conn.commit()
        conn.close()
        flash("Seller added successfully!", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin'))

@app.route('/verify/<int:id>')
def verify(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("UPDATE sellers SET verified = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_seller/<int:id>')
def delete_seller(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM sellers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# -------------------------------
# SELLER ROUTES
# -------------------------------
@app.route('/seller_login', methods=['GET', 'POST'])
def seller_login():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        conn = get_db_connection()
        seller = conn.execute("SELECT * FROM sellers WHERE name=? AND phone=? AND verified=1", (name, phone)).fetchone()
        conn.close()
        if seller:
            session['seller_phone'] = phone
            return redirect(url_for('seller_dashboard'))
        flash("Invalid details or not verified.", "danger")
    return render_template('seller_login.html')

@app.route('/seller_dashboard')
def seller_dashboard():
    phone = session.get('seller_phone')
    if not phone: return redirect(url_for('seller_login'))
    conn = get_db_connection()
    seller = conn.execute("SELECT status FROM sellers WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return render_template('seller_dashboard.html', current_status=seller['status'] if seller else "Available")

@app.route('/update_status/<status>')
def update_status(status):
    phone = session.get('seller_phone')
    if not phone: return redirect(url_for('seller_login'))
    formatted_status = status.replace('_', ' ').title()
    conn = get_db_connection()
    conn.execute("UPDATE sellers SET status = ? WHERE phone = ?", (formatted_status, phone))
    conn.commit()
    conn.close()
    return redirect(url_for('seller_dashboard'))

# -------------------------------
# USER & SEARCH ROUTES
# -------------------------------
@app.route('/')
def home():
    return render_template('home.html')

# --- THIS WAS THE MISSING ROUTE CAUSING THE ERROR ---
@app.route('/benefits')
def benefits():
    return render_template('benefits.html')

@app.route('/search')
def search():
    user_lat = request.args.get('lat')
    user_lon = request.args.get('lon')
    if not user_lat or not user_lon: return "Location access required.", 400
    
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM sellers WHERE verified = 1").fetchall()
    conn.close()

    sellers_list = []
    for s in data:
        dist = calculate_distance(user_lat, user_lon, s['latitude'], s['longitude'])
        sellers_list.append({
            "id": s['id'], "name": s['name'], "phone": s['phone'],
            "price": s['price'], "distance": round(dist, 2), "status": s['status']
        })
    return render_template('search.html', sellers=sorted(sellers_list, key=lambda x: x['distance']))

@app.route('/profile/<int:seller_id>')
def profile(seller_id):
    conn = get_db_connection()
    seller = conn.execute("SELECT * FROM sellers WHERE id=? AND verified=1", (seller_id,)).fetchone()
    conn.close()
    if seller: return render_template('profile.html', s=seller)
    return "Seller not found.", 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)