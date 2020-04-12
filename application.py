import os

from flask import Flask, session, g, render_template, request, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
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


def get_user_by_name(username):
    user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
    return user

def get_user_by_id(user_id):
    user = db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
    return user

def user_already_exists(username):
    user = get_user_by_name(username)
    if user is None:
        exists = False
    else:
        exists = True
    return exists

def store_user_credentials(username, password):
    password_hash = generate_password_hash(password)
    db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": password_hash})
    db.commit()
    return

def credentials_are_valid(username, password):
    user = get_user_by_name(username)
    if not check_password_hash(user['password'], password):
        valid = False
    else:
        valid = True
    return valid

def get_book_by_isbn(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    return book

def split_search_parameters(search_parameters):
    search_keywords = list()
    search_parameters_clean = search_parameters.strip()
    if search_parameters_clean:
        parameters = search_parameters_clean.split()
    for parameter in parameters:
        search_keywords.append(parameter)
        search_keywords.append(parameter.lower())
        search_keywords.append(parameter.upper())
        search_keywords.append(parameter.capitalize())
    # Remove duplicates
    search_keywords = list(dict.fromkeys(search_keywords))
    return search_keywords

def search_for_books_by_keyword(search_keyword):
    search_keyword = "%" + search_keyword + "%"
    books = db.execute("SELECT * FROM books WHERE isbn LIKE :soft_isbn OR title LIKE :soft_title OR author LIKE :soft_author", {"soft_isbn": search_keyword, "soft_title": search_keyword, "soft_author": search_keyword}).fetchall()
    return books

def search_for_books(search_parameters):
    books = list()
    search_keywords = split_search_parameters(search_parameters)
    for search_keyword in search_keywords:
        books = books + search_for_books_by_keyword(search_keyword)
    return books


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    
    # If no-one is looged in
    if user_id is None:
        g.user = None
    # If someone is logged in, then load their info
    else:
        g.user = get_user_by_id(user_id)

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
            print(error)

        # If they are valid, then...
        if error is None:
            # Store user and pass in DB
            store_user_credentials(username, password)
            print(f'Credentials stored for new user {username}.')
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
            error = f'Invalid credentials for user {username}.'
            print(error)

        # If they are valid then...
        if error is None:
            session.clear()
             # Init session
            user = get_user_by_name(username)
            session['user_id'] = user.id
            print(f'Session started by user {username}. User Id: {user.id}.')
            return redirect(url_for('search'))

    return render_template('login.html', error=error)

@app.route('/search', methods=('GET', 'POST'))
def search():
    error = None
    books = None
    if request.method == 'POST':
        # Obtain the search parameters from the form
        search_parameters = request.form['search']

        # Look for them in the data base
        books = search_for_books(search_parameters)

        # Check if user is logged in
        if g.user is None:
            error = f'Your are not logged in.'
            print(error)
        # Check if book exists
        elif len(books) == 0:
            error = f'Book not found.'
            print(error)
        else:
            for book in books:
                print(f'Found book: {book.title}.')

    if request.method == 'GET':
        # Check if user is logged in
        if g.user is None:
            error = f'Your are not logged in.'
            print(error)

    return render_template('search.html', books=books, error=error)

@app.route('/book/<string:isbn>', methods=('GET', 'POST'))
def book(isbn):
    error = None

    # Attempt to get book from DB
    book = get_book_by_isbn(isbn)

    # Check if user is logged in
    if g.user is None:
        error = f'Your are not logged in.'
        print(error)
    # Check if book exists
    elif book is None:
        error = f'Invalid isbn {isbn}.'
        print(error)

    # If it exists then...
    return render_template('book.html', book=book, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))