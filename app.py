import os
import sqlite3
import uuid
import json
import urllib.request
import urllib.error
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists('.env') and not os.environ.get('DATABASE_URL'):
        print("WARNING: python-dotenv is not installed, so your .env was NOT loaded. "
              "The app is using the local SQLite file, not Supabase. "
              "Fix it with:  pip install -r requirements.txt")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_change_this_for_production')

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
DATABASE = os.path.join(BASE_DIR, 'database.db')

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)
if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


def _project_ref_from_db_url():
    if not DATABASE_URL:
        return None
    try:
        creds = DATABASE_URL.split('://', 1)[1].rsplit('@', 1)[0]
        user = creds.split(':', 1)[0]
        if user.startswith('postgres.'):
            return user.split('.', 1)[1]
    except Exception:
        return None
    return None


# --- Supabase Storage ---
SUPABASE_URL = os.environ.get('SUPABASE_URL')
if not SUPABASE_URL:
    _ref = _project_ref_from_db_url()
    if _ref:
        SUPABASE_URL = 'https://%s.supabase.co' % _ref
SUPABASE_SECRET_KEY = (
    os.environ.get('SUPABASE_SECRET_KEY')
    or os.environ.get('SUPABASE_SERVICE_KEY')
)
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'item-images')
STORAGE_ENABLED = bool(SUPABASE_URL and SUPABASE_SECRET_KEY)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = [
    'Electronics', 'Clothing', 'Bags & Backpacks', 'Water Bottles',
    'Books & Supplies', 'Keys & Wallets', 'Jewelry & Accessories',
    'Sports Equipment', 'Other'
]

CATEGORY_ICONS = {
    'Electronics': '\U0001F50C',
    'Clothing': '\U0001F455',
    'Bags & Backpacks': '\U0001F392',
    'Water Bottles': '\U0001F9F4',
    'Books & Supplies': '\U0001F4DA',
    'Keys & Wallets': '\U0001F511',
    'Jewelry & Accessories': '\U0001F48D',
    'Sports Equipment': '\U000026BD',
    'Other': '\U0001F4E6',
}


# --- Database Connection ---
class _DB:
    def __init__(self, conn, is_postgres):
        self._conn = conn
        self._pg = is_postgres

    def execute(self, sql, params=()):
        if self._pg:
            sql = sql.replace('?', '%s')
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if USE_POSTGRES:
            conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
        db = g._database = _DB(conn, USE_POSTGRES)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def _add_column_if_missing(db, table, column_def):
    column_name = column_def.split()[0]
    existing = [row[1] for row in db.execute('PRAGMA table_info(%s)' % table).fetchall()]
    if column_name not in existing:
        db.execute('ALTER TABLE %s ADD COLUMN %s' % (table, column_def))


def init_db():
    with app.app_context():
        db = get_db()

        if USE_POSTGRES:
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    username    TEXT UNIQUE NOT NULL,
                    password    TEXT NOT NULL,
                    role        TEXT DEFAULT 'admin',
                    full_name   TEXT,
                    student_id  TEXT,
                    email       TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id           SERIAL PRIMARY KEY,
                    report_type  TEXT NOT NULL DEFAULT 'found',
                    title        TEXT NOT NULL,
                    description  TEXT NOT NULL,
                    location     TEXT NOT NULL,
                    date_found   TEXT NOT NULL,
                    contact_info TEXT NOT NULL,
                    image_file   TEXT,
                    status       TEXT DEFAULT 'pending',
                    category     TEXT DEFAULT 'Other',
                    user_id      INTEGER
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    id                SERIAL PRIMARY KEY,
                    item_id           INTEGER NOT NULL,
                    item_title        TEXT NOT NULL,
                    claimer_name      TEXT NOT NULL,
                    claimer_contact   TEXT NOT NULL,
                    proof_description TEXT NOT NULL,
                    timestamp         TIMESTAMPTZ DEFAULT now(),
                    user_id           INTEGER
                )
            """)
            db.commit()
        else:
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
            db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
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
            _add_column_if_missing(db, 'items', "category TEXT DEFAULT 'Other'")
            _add_column_if_missing(db, 'items', 'user_id INTEGER')
            _add_column_if_missing(db, 'users', "role TEXT DEFAULT 'admin'")
            _add_column_if_missing(db, 'users', 'full_name TEXT')
            _add_column_if_missing(db, 'users', 'student_id TEXT')
            _add_column_if_missing(db, 'users', 'email TEXT')
            _add_column_if_missing(db, 'claims', 'user_id INTEGER')
            db.execute("UPDATE users SET role = 'admin' WHERE role IS NULL")
            db.commit()

        cur = db.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if cur.fetchone() is None:
            hashed_pw = generate_password_hash('admin123')
            db.execute(
                'INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)',
                ('admin', hashed_pw, 'admin', 'Administrator')
            )
            db.commit()
            print("Default admin account created.")

        print("Database ready (%s)." % ('Postgres' if USE_POSTGRES else 'SQLite'))


# --- Utilities ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


_bucket_checked = False


def _ensure_bucket():
    global _bucket_checked
    if _bucket_checked:
        return
    _bucket_checked = True
    try:
        body = json.dumps({'id': SUPABASE_BUCKET, 'name': SUPABASE_BUCKET, 'public': True}).encode()
        req = urllib.request.Request('%s/storage/v1/bucket' % SUPABASE_URL, data=body, method='POST')
        req.add_header('Authorization', 'Bearer %s' % SUPABASE_SECRET_KEY)
        req.add_header('apikey', SUPABASE_SECRET_KEY)
        req.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def _upload_to_supabase(object_name, data, content_type):
    url = '%s/storage/v1/object/%s/%s' % (SUPABASE_URL, SUPABASE_BUCKET, object_name)
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', 'Bearer %s' % SUPABASE_SECRET_KEY)
    req.add_header('apikey', SUPABASE_SECRET_KEY)
    req.add_header('Content-Type', content_type or 'application/octet-stream')
    req.add_header('x-upsert', 'true')
    urllib.request.urlopen(req, timeout=20).read()
    return '%s/storage/v1/object/public/%s/%s' % (SUPABASE_URL, SUPABASE_BUCKET, object_name)


def save_upload(file):
    object_name = '%s_%s' % (uuid.uuid4().hex, secure_filename(file.filename))
    data = file.read()
    if STORAGE_ENABLED:
        try:
            _ensure_bucket()
            return _upload_to_supabase(object_name, data, file.mimetype)
        except Exception as exc:
            app.logger.warning('Supabase Storage upload failed (%s); saving locally instead.', exc)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], object_name), 'wb') as fh:
        fh.write(data)
    return object_name


def image_url(value):
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://'):
        return value
    return url_for('static', filename='uploads/' + value)


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()


def is_admin():
    return session.get('role') == 'admin'


@app.context_processor
def inject_globals():
    return dict(current_user=current_user(), CATEGORIES=CATEGORIES, image_url=image_url)


@app.template_filter('days_ago')
def days_ago(value):
    try:
        d = datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return value
    delta = (date.today() - d).days
    if delta < 0:
        return 'Upcoming'
    if delta == 0:
        return 'Today'
    if delta == 1:
        return 'Yesterday'
    if delta < 7:
        return '%d days ago' % delta
    if delta < 30:
        weeks = delta // 7
        return '%d week%s ago' % (weeks, '' if weeks == 1 else 's')
    if delta < 365:
        months = delta // 30
        return '%d month%s ago' % (months, '' if months == 1 else 's')
    years = delta // 365
    return '%d year%s ago' % (years, '' if years == 1 else 's')


@app.template_filter('category_icon')
def category_icon(value):
    return CATEGORY_ICONS.get(value, CATEGORY_ICONS['Other'])


# --- Public Routes ---
@app.route('/')
def index():
    db = get_db()
    items = db.execute("SELECT * FROM items WHERE status = 'approved' AND report_type = 'found' ORDER BY id DESC LIMIT 3").fetchall()
    found_count = db.execute("SELECT COUNT(*) AS n FROM items WHERE status = 'approved' AND report_type = 'found'").fetchone()['n']
    lost_count = db.execute("SELECT COUNT(*) AS n FROM items WHERE status = 'approved' AND report_type = 'lost'").fetchone()['n']
    return render_template('index.html', items=items, found_count=found_count, lost_count=lost_count)


@app.route('/report', methods=('GET', 'POST'))
def report():
    report_type_arg = request.args.get('type', 'found')

    if request.method == 'POST':
        report_type = request.form['report_type']
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_found = request.form['date_found']
        contact_info = request.form['contact_info']
        category = request.form.get('category', 'Other')
        if category not in CATEGORIES:
            category = 'Other'

        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = save_upload(file)

        db = get_db()
        db.execute(
            'INSERT INTO items (report_type, title, description, location, date_found, contact_info, image_file, category, user_id) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (report_type, title, description, location, date_found, contact_info, filename, category, session.get('user_id'))
        )
        db.commit()
        flash('Item reported successfully. Pending admin approval.', 'success')
        return redirect(url_for('index'))

    return render_template('report.html', current_type=report_type_arg)


@app.route('/items')
def items():
    query = request.args.get('q', '').strip()
    report_type = request.args.get('type', 'found')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'newest')
    order = 'ASC' if sort == 'oldest' else 'DESC'

    db = get_db()
    sql = "SELECT * FROM items WHERE status = 'approved' AND report_type = ?"
    params = [report_type]
    if category:
        sql += ' AND category = ?'
        params.append(category)
    if query:
        sql += ' AND (title LIKE ? OR description LIKE ? OR location LIKE ?)'
        like = '%%%s%%' % query
        params.extend([like, like, like])
    sql += ' ORDER BY id ' + order
    items = db.execute(sql, params).fetchall()

    return render_template(
        'items.html', items=items, query=query, current_type=report_type,
        current_category=category, current_sort=sort
    )


@app.route('/item/<int:id>', methods=('GET', 'POST'))
def item_detail(id):
    db = get_db()
    item = db.execute('SELECT * FROM items WHERE id = ?', (id,)).fetchone()

    if item is None:
        flash('Item not found.', 'error')
        return redirect(url_for('items'))

    if request.method == 'POST':
        claimer_name = request.form['claimer_name']
        claimer_contact = request.form['claimer_contact']
        proof_description = request.form['proof_description']

        db.execute('INSERT INTO claims (item_id, item_title, claimer_name, claimer_contact, proof_description, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                   (id, item['title'], claimer_name, claimer_contact, proof_description, session.get('user_id')))
        db.commit()

        flash("Inquiry submitted. An admin will contact you at %s." % claimer_contact, 'success')
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


# --- Student Accounts ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if current_user():
        return redirect(url_for('index'))
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        student_id = request.form['student_id'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username = ? OR email = ?', (email, email)).fetchone()
        if not full_name or not email:
            flash('Please fill in your name and email.', 'error')
        elif existing:
            flash('An account with that email already exists. Try logging in.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            db.execute(
                'INSERT INTO users (username, password, role, full_name, student_id, email) VALUES (?, ?, ?, ?, ?, ?)',
                (email, generate_password_hash(password), 'student', full_name, student_id, email)
            )
            db.commit()
            user = db.execute('SELECT * FROM users WHERE username = ?', (email,)).fetchone()
            session.clear()
            session['user_id'] = user['id']
            session['role'] = 'student'
            session['full_name'] = full_name
            flash('Welcome aboard, %s! Your account is ready.' % full_name, 'success')
            return redirect(url_for('account'))
    return render_template('register.html')


@app.route('/account', methods=('GET', 'POST'))
def account():
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    if user['role'] == 'admin':
        return redirect(url_for('dashboard'))

    db = get_db()
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        student_id = request.form['student_id'].strip()
        db.execute('UPDATE users SET full_name = ?, student_id = ? WHERE id = ?',
                   (full_name, student_id, user['id']))
        db.commit()
        session['full_name'] = full_name
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))

    my_items = db.execute('SELECT * FROM items WHERE user_id = ? ORDER BY id DESC', (user['id'],)).fetchall()
    my_claims = db.execute('SELECT * FROM claims WHERE user_id = ? ORDER BY id DESC', (user['id'],)).fetchall()
    return render_template('account.html', user=user, my_items=my_items, my_claims=my_claims)


# --- Auth ---
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        identifier = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                          (identifier, identifier.lower())).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            flash('Invalid credentials. Please try again.', 'error')
        else:
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role'] or 'admin'
            session['full_name'] = user['full_name'] or user['username']
            if session['role'] == 'admin':
                return redirect(url_for('dashboard'))
            return redirect(url_for('account'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# --- Admin Routes ---
@app.route('/dashboard')
def dashboard():
    if not is_admin():
        return redirect(url_for('login'))

    db = get_db()
    pending_found = db.execute("SELECT * FROM items WHERE status = 'pending' AND report_type = 'found'").fetchall()
    pending_lost = db.execute("SELECT * FROM items WHERE status = 'pending' AND report_type = 'lost'").fetchall()
    live_found = db.execute("SELECT * FROM items WHERE status = 'approved' AND report_type = 'found'").fetchall()
    active_lost = db.execute("SELECT * FROM items WHERE status = 'approved' AND report_type = 'lost'").fetchall()
    claims = db.execute('SELECT * FROM claims ORDER BY id DESC').fetchall()

    return render_template('dashboard.html', pending_found=pending_found, pending_lost=pending_lost, live_found=live_found, active_lost=active_lost, claims=claims)


@app.route('/approve/<int:id>')
def approve(id):
    if not is_admin():
        return redirect(url_for('login'))
    db = get_db()
    db.execute("UPDATE items SET status = 'approved' WHERE id = ?", (id,))
    db.commit()
    flash('Item approved.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:id>')
def delete(id):
    if not is_admin():
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM items WHERE id = ?', (id,))
    db.execute('DELETE FROM claims WHERE item_id = ?', (id,))
    db.commit()
    flash('Item removed.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete_claim/<int:id>')
def delete_claim(id):
    if not is_admin():
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM claims WHERE id = ?', (id,))
    db.commit()
    flash('Claim dismissed.', 'success')
    return redirect(url_for('dashboard'))


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
