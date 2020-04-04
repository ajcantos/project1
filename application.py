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


def credentials_are_valid(username, password):
    access = False
    if username == 'ajcantos':
        if password == '111111':
            access = True
    return access

def user_already_exists(username):
    exists = False
    if username == 'ajcantos':
        exists = True
    
    return exists

@app.route('/')
def index():
    return render_template('index.html')

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
            # Init session
            return redirect(url_for('search'))

    return render_template('login.html', error=error)

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
            error = 'User already exists'

        # If they are valid, then...
        if error is None:
            # Store user and pass in DB
            return redirect(url_for('login'))

    return render_template('register.html', error=error)

@app.route('/search', methods=('GET', 'POST'))
def search():
    error = None
    return render_template('search.html', error=error)