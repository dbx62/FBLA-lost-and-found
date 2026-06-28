"""
Seed the database with realistic example data that demonstrates every feature
of the SLHS Lost & Found site.

Run from the project folder (with your .env in place):

    python seed_data.py            # add the demo data
    python seed_data.py --reset    # wipe existing items/claims/students, then add

It reuses app.py's connection, so it writes to Supabase when DATABASE_URL is set,
or to the local SQLite file otherwise. The admin account is never touched.
"""
import sys
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

from app import app, get_db, USE_POSTGRES


def days_ago(n):
    """Return a YYYY-MM-DD string n days before today."""
    return (date.today() - timedelta(days=n)).isoformat()


DEMO_STUDENT = {
    'full_name': 'Maria Lopez',
    'student_id': 'K1180023',
    'email': 'maria.lopez@students.slhs.edu',
    'password': 'demo1234',
}

# report_type, title, description, location, days, contact_info, image_file, status, category, by_student
ITEMS = [
    # ---- Approved FOUND items (show on Browse > Found and the homepage) ----
    ('found', 'Owala FreeSip Water Bottle', 'Teal 24 oz Owala bottle with a small dent near the base and a faded robotics-club sticker.', 'Cafeteria - Table 12', 0, 'Jordan Ellis - K1102934', 'af555b99797f45ab97dda36188c949f9_Owala_Water_Bottle.webp', 'approved', 'Water Bottles', False),
    ('found', 'Black JanSport Backpack', 'Full-size black JanSport. Contains a Spanish textbook and a blue graphing calculator. Name tag inside.', 'Gym Bleachers', 1, 'Coach Rivera - STAFF0091', 'e104c78d273e42a7aa59db5300f35881_Backpack.avif', 'approved', 'Bags & Backpacks', False),
    ('found', 'Black North Face Jacket', 'Mens medium black North Face puffer jacket. Found draped over a chair after 7th period.', 'Room 214', 3, 'Priya Shah - K1156620', '16adc4f2f5704ea6a00cca5f36a7bc3b_Jacket.jpg', 'approved', 'Clothing', False),
    ('found', 'Floral Pencil Bag', 'Small floral-print zip pencil pouch with assorted pens and a USB drive inside.', 'Library - Study Room B', 5, 'Library Desk - STAFF0042', '8f3a77cf22d749a2812023d901332a4c_Pencil_Bag.webp', 'approved', 'Books & Supplies', False),
    ('found', 'Blue Insulated Lunch Box', 'Navy blue insulated lunch box, brand "PackIt". Found in the courtyard at lunch.', 'Courtyard', 9, 'Marcus Bell - K1140077', '443eb9ee352a46e7860402ba28bc5091_Lunch_Box.jpeg', 'approved', 'Other', False),
    ('found', 'AirPods Pro Charging Case', 'White AirPods Pro case (no earbuds inside). Light scratch on the lid.', 'Bus Loop', 2, 'Front Office - STAFF0001', None, 'approved', 'Electronics', False),
    ('found', 'Silver Hydro Flask', '32 oz brushed-silver Hydro Flask with a dent and a "SLHS Band" sticker.', 'Band Hall', 12, 'Mr. Tran - STAFF0067', None, 'approved', 'Water Bottles', False),
    ('found', 'TI-84 Plus CE Calculator', 'Black TI-84 Plus CE. Slide cover is cracked and there are initials scratched on the back.', 'Room 118', 22, 'Ms. Howard - STAFF0033', None, 'approved', 'Electronics', False),
    ('found', 'Set of House Keys (blue lanyard)', 'Three keys on a blue carabiner lanyard with a small flashlight fob.', 'Main Entrance', 0, 'Security - STAFF0009', None, 'approved', 'Keys & Wallets', False),
    ('found', 'Tortoise-Frame Glasses', 'Pair of prescription glasses, tortoise-shell frames, in a brown soft case.', 'Auditorium', 4, 'Drama Dept - STAFF0058', None, 'approved', 'Jewelry & Accessories', False),

    # ---- Approved LOST reports (show on Browse > Looking For) ----
    ('lost', 'Silver MacBook Air 13"', 'Lost my silver MacBook Air sometime Tuesday. Has a Seven Lakes sticker and a cracked corner.', 'Library or Room 207', 1, 'Maria Lopez - K1180023', None, 'approved', 'Electronics', True),
    ('lost', 'Brown Leather Wallet', 'Brown bifold wallet with student ID and a blue debit card. Lost near the gym.', 'Gym Locker Room', 6, 'Devon Carter - K1167781', None, 'approved', 'Keys & Wallets', False),

    # ---- PENDING items (show in admin Dashboard > Pending Approval) ----
    ('found', 'Apple Watch (Series 7)', 'Apple Watch with a black sport band, found on a sink in the 2nd-floor restroom.', '2nd Floor Restroom', 0, 'Custodial - STAFF0015', None, 'pending', 'Electronics', False),
    ('lost', 'Nike Gym Duffel Bag', 'Lost a red Nike duffel with cleats and shin guards after soccer practice.', 'Athletic Fields', 2, 'Sam Whitfield - K1175588', None, 'pending', 'Sports Equipment', False),
]

# item_title, claimer_name, claimer_contact, proof_description, by_student
CLAIMS = [
    ('Owala FreeSip Water Bottle', 'Daniel Kim', 'daniel.kim@students.slhs.edu',
     'It has a dent near the bottom and a faded robotics-club sticker on the side. My initials DK are on the cap.', False),
    ('Black JanSport Backpack', 'Maria Lopez', 'maria.lopez@students.slhs.edu',
     'Theres a Spanish 3 textbook and a blue TI calculator inside, and my name "Maria L." is on the inside tag.', True),
    ('TI-84 Plus CE Calculator', 'Aisha Patel', 'aisha.patel@students.slhs.edu',
     'My initials A.P. are scratched on the back near the battery cover, and the slide cover is cracked at one corner.', False),
    ('Silver MacBook Air 13"', 'Front Office', 'frontoffice@slhs.edu',
     'A silver MacBook matching this description was just turned in to the library front desk - please come by to confirm.', False),
]


def reset(db):
    db.execute('DELETE FROM claims')
    db.execute('DELETE FROM items')
    db.execute("DELETE FROM users WHERE username <> 'admin'")
    db.commit()


def main():
    do_reset = '--reset' in sys.argv
    with app.app_context():
        db = get_db()

        if do_reset:
            reset(db)
            print('Reset: cleared existing items, claims, and student accounts.')

        # --- demo student account ---
        row = db.execute('SELECT id FROM users WHERE email = ?', (DEMO_STUDENT['email'],)).fetchone()
        if row:
            student_id = row['id']
            print('Demo student already exists (id %s).' % student_id)
        else:
            db.execute(
                'INSERT INTO users (username, password, role, full_name, student_id, email) VALUES (?, ?, ?, ?, ?, ?)',
                (DEMO_STUDENT['email'], generate_password_hash(DEMO_STUDENT['password']), 'student',
                 DEMO_STUDENT['full_name'], DEMO_STUDENT['student_id'], DEMO_STUDENT['email'])
            )
            db.commit()
            student_id = db.execute('SELECT id FROM users WHERE email = ?', (DEMO_STUDENT['email'],)).fetchone()['id']
            print('Created demo student account (id %s).' % student_id)

        # --- items ---
        for (rtype, title, desc, loc, days, contact, img, status, cat, by_student) in ITEMS:
            uid = student_id if by_student else None
            db.execute(
                'INSERT INTO items (report_type, title, description, location, date_found, contact_info, image_file, status, category, user_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (rtype, title, desc, loc, days_ago(days), contact, img, status, cat, uid)
            )
        db.commit()
        print('Inserted %d items.' % len(ITEMS))

        # --- claims (looked up by item title) ---
        added = 0
        for (item_title, name, contact, proof, by_student) in CLAIMS:
            found = db.execute('SELECT id, title FROM items WHERE title = ? ORDER BY id DESC LIMIT 1', (item_title,)).fetchone()
            if not found:
                continue
            uid = student_id if by_student else None
            db.execute(
                'INSERT INTO claims (item_id, item_title, claimer_name, claimer_contact, proof_description, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                (found['id'], found['title'], name, contact, proof, uid)
            )
            added += 1
        db.commit()
        print('Inserted %d claims.' % added)

        # --- summary ---
        def count(sql, params=()):
            return db.execute(sql, params).fetchone()['n']

        print('\n--- Database now contains ---')
        print('Approved found items :', count("SELECT COUNT(*) AS n FROM items WHERE status='approved' AND report_type='found'"))
        print('Approved lost reports:', count("SELECT COUNT(*) AS n FROM items WHERE status='approved' AND report_type='lost'"))
        print('Pending approval     :', count("SELECT COUNT(*) AS n FROM items WHERE status='pending'"))
        print('Claims / inquiries   :', count("SELECT COUNT(*) AS n FROM claims"))
        print('\nBackend:', 'Postgres (Supabase)' if USE_POSTGRES else 'SQLite (local)')
        print('\nDemo student login -> email: %s  password: %s' % (DEMO_STUDENT['email'], DEMO_STUDENT['password']))
        print('Admin login        -> username: admin  password: admin123')


if __name__ == '__main__':
    main()
