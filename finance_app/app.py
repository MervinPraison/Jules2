from flask import Flask, render_template, request, redirect, url_for, g, flash # Added flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your secret key' # Necessary for flash messages
DATABASE = 'finance.db'

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
        # Check if schema.sql exists before trying to open it
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
        except FileNotFoundError:
            print("schema.sql not found. Database not initialized with schema.")


@app.route('/', methods=['GET', 'POST'])
def index():
    db = get_db()
    if request.method == 'POST':
        description = request.form['description']
        amount_str = request.form['amount'] # Keep as string for validation
        date = request.form['date']

        error = False
        if not description:
            flash('Description is required.', 'error')
            error = True
        if not amount_str:
            flash('Amount is required.', 'error')
            error = True
        if not date:
            flash('Date is required.', 'error')
            error = True

        amount_float = None
        # Only try conversion if no prior errors and amount_str is not empty
        if not error and amount_str:
            try:
                amount_float = float(amount_str)
            except ValueError:
                flash('Amount must be a valid number.', 'error')
                error = True

        if error: # If any error occurred, redirect back to form
            # Flashed messages will be displayed on the next render of index.html
            cur = db.execute('SELECT id, description, amount, date FROM transactions ORDER BY date DESC, id DESC')
            transactions_from_db = cur.fetchall()
            # We need to pass transactions to the template even when redirecting after an error
            # However, redirecting to 'index' and then rendering 'index.html' is the standard pattern.
            # The flash messages are stored in the session and will be picked up by the next request to 'index'.
            return render_template('index.html', transactions=transactions_from_db)


        # If all good, insert into DB
        if amount_float is not None: # This check ensures amount_float was successfully converted
            db.execute('INSERT INTO transactions (description, amount, date) VALUES (?, ?, ?)',
                       [description, amount_float, date])
            db.commit()
            flash('Transaction added successfully!', 'success')
        else:
            # This case should ideally not be reached if validation is correct
            # but as a fallback if amount_float is None and no error was flashed (e.g. amount_str was empty but not caught by initial check)
            if not amount_str: # Double check if amount was empty and not caught
                 flash('Amount is required and must be a valid number.', 'error')

        return redirect(url_for('index'))

    cur = db.execute('SELECT id, description, amount, date FROM transactions ORDER BY date DESC, id DESC')
    transactions_from_db = cur.fetchall()
    return render_template('index.html', transactions=transactions_from_db)

@app.route('/transactions')
def view_transactions():
    db = get_db()
    cur = db.execute('SELECT id, description, amount, date FROM transactions ORDER BY date DESC, id DESC')
    transactions_from_db = cur.fetchall()
    return render_template('transactions.html', transactions=transactions_from_db)

# It's good practice to run init_db once, perhaps via a CLI command,
# but for this simple app, running it before first request is fine.
# However, to ensure it runs within app context correctly and only once needed:
@app.before_first_request
def initialize_database():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
