import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev_key_change_this_for_production'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Helper Functions ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Items Table (Stores finder info securely)
        db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date_found TEXT NOT NULL,
                contact_info TEXT NOT NULL, 
                image_file TEXT,
                status TEXT DEFAULT 'pending' 
            )
        ''')
        # Users Table (Admin)
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # NEW: Claims Table (Stores claimant info)
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
        
        # Create default admin if not exists
        cur = db.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if cur.fetchone() is None:
            hashed_pw = generate_password_hash('admin123')
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_pw))
            db.commit()
            print("Default admin created.")

# --- Helper Logic ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---

@app.route('/')
def index():
    db = get_db()
    items = db.execute('SELECT * FROM items WHERE status = "approved" ORDER BY id DESC LIMIT 3').fetchall()
    return render_template('index.html', items=items)

@app.route('/report', methods=('GET', 'POST'))
def report():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_found = request.form['date_found']
        # This is the FINDER'S contact info (Hidden from public)
        contact_info = request.form['contact_info']
        
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
            'INSERT INTO items (title, description, location, date_found, contact_info, image_file) VALUES (?, ?, ?, ?, ?, ?)',
            (title, description, location, date_found, contact_info, filename)
        )
        db.commit()
        flash('Item reported! An admin will review it shortly.', 'success')
        return redirect(url_for('index'))

    return render_template('report.html')

@app.route('/items')
def items():
    query = request.args.get('q', '')
    db = get_db()
    
    if query:
        search_term = f"%{query}%"
        items = db.execute(
            'SELECT * FROM items WHERE status = "approved" AND (title LIKE ? OR description LIKE ? OR location LIKE ?)',
            (search_term, search_term, search_term)
        ).fetchall()
    else:
        items = db.execute('SELECT * FROM items WHERE status = "approved" ORDER BY id DESC').fetchall()
        
    return render_template('items.html', items=items, query=query)

@app.route('/item/<int:id>', methods=('GET', 'POST'))
def item_detail(id):
    db = get_db()
    item = db.execute('SELECT * FROM items WHERE id = ?', (id,)).fetchone()
    
    if item is None:
        flash('Item not found.', 'error')
        return redirect(url_for('items'))

    if request.method == 'POST':
        # The user is claiming the item
        claimer_name = request.form['claimer_name']
        claimer_contact = request.form['claimer_contact']
        proof_description = request.form['proof_description']
        
        db.execute('INSERT INTO claims (item_id, item_title, claimer_name, claimer_contact, proof_description) VALUES (?, ?, ?, ?, ?)',
                   (id, item['title'], claimer_name, claimer_contact, proof_description))
        db.commit()
        
        flash(f"Claim sent! The Admin will review your proof and contact you at {claimer_contact}.", 'success')
        return redirect(url_for('item_detail', id=id))

    return render_template('item_detail.html', item=item)

# --- Admin Routes ---

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            flash('Incorrect username or password.', 'error')
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
    # Fetch all claims to show the admin
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
    # Delete item AND any associated claims
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.execute('DELETE FROM claims WHERE item_id = ?', (id,))
    db.commit()
    flash('Item and associated claims removed.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_claim/<int:id>')
def delete_claim(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM claims WHERE id = ?', (id,))
    db.commit()
    flash('Claim request dismissed.', 'success')
    return redirect(url_for('dashboard'))

# --- NEW ROUTES ---
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/legal')
def legal():
    return render_template('legal.html')

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)