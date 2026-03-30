from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from werkzeug.security import check_password_hash

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH") or "scrypt:32768:8:1$Q5r4WBi2h2W7PbQR$d6225b7b8b056a0d9680b28c290ed9de073fe8faf3dac893e5df45f19fb74737bccb44a4e707f11e56ccaadfb404848ce7bac0b8e76d7cd1cb7222918ffd6e8b"

if not ADMIN_PASSWORD_HASH:
    print("ERROR: Admin password not set in environment!")

app = Flask(__name__)
app.secret_key = "KalluFinder_Secure_Key_2026"

# Admin Configuration
ADMIN_USERNAME = "admin"
import os
from werkzeug.security import check_password_hash

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

def get_db_connection():
    conn = sqlite3.connect('database.db')
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
    """Calculates distance in KM"""
    return round(((float(lat1) - float(lat2))**2 + (float(lon1) - float(lon2))**2)**0.5 * 111, 2)

# --- PUBLIC ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/benefits')
def benefits():
    """This route loads your benefits.html file"""
    return render_template('benefits.html')

@app.route('/search')
def search():
    try:
        user_lat = float(request.args.get('lat'))
        user_lon = float(request.args.get('lon'))
    except:
        return "Location Error. Please enable GPS and try again."

    conn = get_db_connection()
    # Fetching as tuples for index-based access (s[0], s[1], etc.)
    data = conn.execute("SELECT * FROM sellers WHERE verified=1").fetchall()
    conn.close()

    results = []
    for s in data:
        dist = calculate_distance(user_lat, user_lon, s[5], s[6])
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
        # Map to 's' dictionary for profile.html compatibility
        s_obj = {
            "id": row[0], "name": row[1], "address": row[2], "phone": row[3], 
            "price": row[4], "latitude": row[5], "longitude": row[6], "status": row[8]
        }
        return render_template('profile.html', s=s_obj)
    return "Seller Not Found", 404

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
        return "Phone not registered."
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
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            return redirect(url_for('admin'))

        return "Invalid username or password"
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
        return "Error: Duplicate Phone Number!"
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)