import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Secret key for session management
app.secret_key = 'dev_key_change_this_for_production'

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
DATABASE = os.path.join(BASE_DIR, 'database.db')

# Allowed extensions for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Connection ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database with required tables and default admin."""
    with app.app_context():
        db = get_db()
        
        # Items table
        db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL DEFAULT 'found', 
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date_found TEXT NOT NULL,
                contact_info TEXT NOT NULL, 
                image_file TEXT,
                status TEXT DEFAULT 'pending' 
            )
        ''')
        
        # Users table
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Claims table
        db.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                item_title TEXT NOT NULL,
                claimer_name TEXT NOT NULL,
                claimer_contact TEXT NOT NULL,
                proof_description TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create default admin account if none exists
        cur = db.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if cur.fetchone() is None:
            hashed_pw = generate_password_hash('admin123')
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_pw))
            db.commit()
            print("Default admin account created.")

# --- Utilities ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Public Routes ---

@app.route('/')
def index():
    db = get_db()
    # Fetch recent approved found items for the homepage
    items = db.execute('SELECT * FROM items WHERE status = "approved" AND report_type = "found" ORDER BY id DESC LIMIT 3').fetchall()
    return render_template('index.html', items=items)

@app.route('/report', methods=('GET', 'POST'))
def report():
    # Pass 'lost' or 'found' into the URL (e.g. /report?type=lost)
    report_type_arg = request.args.get('type', 'found')
    
    if request.method == 'POST':
        report_type = request.form['report_type']
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_found = request.form['date_found']
        contact_info = request.form['contact_info']
        
        # Handle image upload
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import uuid
                filename = f"{uuid.uuid4().hex}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db()
        db.execute(
            'INSERT INTO items (report_type, title, description, location, date_found, contact_info, image_file) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (report_type, title, description, location, date_found, contact_info, filename)
        )
        db.commit()
        flash(f'Item reported successfully. Pending admin approval.', 'success')
        return redirect(url_for('index'))

    return render_template('report.html', current_type=report_type_arg)

@app.route('/items')
def items():
    query = request.args.get('q', '')
    db = get_db()
    
    if query:
        search_term = f"%{query}%"
        # SECURITY UPDATE: Hardcoded report_type = "found" to protect privacy of lost items
        items = db.execute(
            'SELECT * FROM items WHERE status = "approved" AND report_type = "found" AND (title LIKE ? OR description LIKE ? OR location LIKE ?)',
            (search_term, search_term, search_term)
        ).fetchall()
    else:
        # SECURITY UPDATE: Hardcoded report_type = "found"
        items = db.execute('SELECT * FROM items WHERE status = "approved" AND report_type = "found" ORDER BY id DESC').fetchall()
        
    return render_template('items.html', items=items, query=query)

@app.route('/item/<int:id>', methods=('GET', 'POST'))
def item_detail(id):
    db = get_db()
    item = db.execute('SELECT * FROM items WHERE id = ?', (id,)).fetchone()
    
    if item is None:
        flash('Item not found.', 'error')
        return redirect(url_for('items'))

    # Handle claim submission
    if request.method == 'POST':
        claimer_name = request.form['claimer_name']
        claimer_contact = request.form['claimer_contact']
        proof_description = request.form['proof_description']
        
        db.execute('INSERT INTO claims (item_id, item_title, claimer_name, claimer_contact, proof_description) VALUES (?, ?, ?, ?, ?)',
                   (id, item['title'], claimer_name, claimer_contact, proof_description))
        db.commit()
        
        flash(f"Inquiry submitted. An admin will contact you at {claimer_contact}.", 'success')
        return redirect(url_for('item_detail', id=id))

    return render_template('item_detail.html', item=item)

# --- Static Pages ---

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/legal')
def legal():
    return render_template('legal.html')

@app.route('/sources')
def sources():
    return render_template('sources.html')

# --- Admin Routes ---

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            flash('Invalid credentials.', 'error')
        else:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    pending = db.execute('SELECT * FROM items WHERE status = "pending"').fetchall()
    approved = db.execute('SELECT * FROM items WHERE status = "approved"').fetchall()
    claims = db.execute('SELECT * FROM claims ORDER BY id DESC').fetchall()
    
    return render_template('dashboard.html', pending=pending, approved=approved, claims=claims)

@app.route('/approve/<int:id>')
def approve(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE items SET status = "approved" WHERE id = ?', (id,))
    db.commit()
    flash('Item approved.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    # Delete item and associated claims
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.execute('DELETE FROM claims WHERE item_id = ?', (id,))
    db.commit()
    flash('Item removed.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_claim/<int:id>')
def delete_claim(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM claims WHERE id = ?', (id,))
    db.commit()
    flash('Claim dismissed.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True, host='0.0.0.0')