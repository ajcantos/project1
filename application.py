import os

from flask import Flask, session, render_template, request, redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def user_already_exists(username):
    if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount == 0:
        exists = False
    else:
        exists = True
    print(f'Existance checked for user {username}. Result: {exists} ')
    return exists

def store_user_credentials(username, password):
    password_hash = password
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password_hash})
    db.commit()
    print(f'Credentials stored for new user {username}.')
    return

def credentials_are_valid(username, password):
    password_hash = password
    if db.execute("SELECT * FROM users WHERE username = :username AND password = :password", {"username": username, "password": password_hash}).rowcount == 0:
        valid = False
    else:
        valid = True
    print(f'Credentials checked for user {username}. Result: {valid} ')
    return valid

def get_user_id(username):
    user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
    print(f'Session started by user {username}. User Id: {user.id}.')
    return user.id


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    error = None
    if request.method == 'POST':
        # Obtain the username and passowrd from the form
        username = request.form['username']
        password = request.form['password']

        # Check if they are valid
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif user_already_exists(username):
            error = f'User \'{username}\' already exists'

        # If they are valid, then...
        if error is None:
            # Store user and pass in DB
            store_user_credentials(username, password)
            return redirect(url_for('login'))

    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Obtain the username and password from the form
        username = request.form['username']
        password = request.form['password']

        # Check if they are valid
        if not credentials_are_valid (username, password):
            error = 'Invalid credentials'

        # If they are valid, then...
        if error is None:
            session.clear()
             # Init session
            session['user_id'] = get_user_id(username)
            return redirect(url_for('search'))

    return render_template('login.html', error=error)

@app.route('/search', methods=('GET', 'POST'))
def search():
    error = None
    return render_template('search.html', error=error)