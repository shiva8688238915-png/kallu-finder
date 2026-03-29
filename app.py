from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "KalluFinder_Secure_Key_2026"

# Admin Configuration
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "9177@Shiva"

def get_db_connection():
    conn = sqlite3.connect('database.db')
    # We do NOT use row_factory=Row here because your admin.html uses indexes like s[0], s[1]
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT UNIQUE,
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

def calculate_distance(lat1, lon1, lat2, lon2):
    return round(((float(lat1) - float(lat2))**2 + (float(lon1) - float(lon2))**2)**0.5 * 111, 2)

# --- PUBLIC ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    try:
        user_lat = float(request.args.get('lat'))
        user_lon = float(request.args.get('lon'))
    except:
        return "Location Error. Please enable GPS."

    conn = get_db_connection()
    # Fetching as list of tuples for index access
    data = conn.execute("SELECT * FROM sellers WHERE verified=1").fetchall()
    conn.close()

    results = []
    for s in data:
        dist = calculate_distance(user_lat, user_lon, s[5], s[6]) # lat is index 5, lon is index 6
        results.append({
            "id": s[0], "name": s[1], "distance": dist, "status": s[8]
        })

    results = sorted(results, key=lambda x: x['distance'])
    return render_template('search.html', sellers=results)

@app.route('/profile/<int:seller_id>')
def profile(seller_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM sellers WHERE id = ?", (seller_id,)).fetchone()
    conn.close()
    if row:
        # Map to 's' for profile.html
        s_obj = {"id": row[0], "name": row[1], "address": row[2], "phone": row[3], 
                 "price": row[4], "latitude": row[5], "longitude": row[6], "status": row[8]}
        return render_template('profile.html', s=s_obj)
    return "Not Found", 404

# --- SELLER ROUTES ---

@app.route('/seller_login', methods=['GET', 'POST'])
def seller_login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        conn = get_db_connection()
        seller = conn.execute("SELECT * FROM sellers WHERE phone = ?", (phone,)).fetchone()
        conn.close()
        if seller:
            session['seller'] = phone
            return redirect(url_for('seller_dashboard'))
        return "Not registered."
    return render_template('seller_login.html')

@app.route('/seller_dashboard')
def seller_dashboard():
    phone = session.get('seller')
    if not phone: return redirect(url_for('seller_login'))
    conn = get_db_connection()
    seller = conn.execute("SELECT status FROM sellers WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return render_template('seller_dashboard.html', current_status=seller[0])

@app.route('/update_status/<status>')
def update_status(status):
    phone = session.get('seller')
    if phone:
        conn = get_db_connection()
        conn.execute("UPDATE sellers SET status=? WHERE phone=?", (status, phone))
        conn.commit()
        conn.close()
    return redirect(url_for('seller_dashboard'))

# --- ADMIN ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    sellers = conn.execute("SELECT * FROM sellers").fetchall()
    conn.close()
    return render_template('admin.html', sellers=sellers)

@app.route('/add_seller', methods=['POST'])
def add_seller():
    if not session.get('admin'): return redirect(url_for('login'))
    f = request.form
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO sellers (name, address, phone, price, latitude, longitude) VALUES (?,?,?,?,?,?)",
                     (f['name'], f['address'], f['phone'], f['price'], f['lat'], f['lon']))
        conn.commit()
        conn.close()
    except:
        return "Phone number already exists!"
    return redirect(url_for('admin'))

@app.route('/verify/<int:id>')
def verify(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("UPDATE sellers SET verified=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/delete_seller/<int:id>')
def delete_seller(id):
    if not session.get('admin'): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM sellers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)