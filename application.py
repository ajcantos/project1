import os
import math
import requests

from flask import Flask, session, g, render_template, jsonify, request, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variables
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
if not os.getenv("GOODREADS_KEY"):
    raise RuntimeError("GOODREADS_KEY is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Get the Goodreads key
goodreads_key = os.getenv("GOODREADS_KEY")

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

def get_book_reviews(book_id):
    reviews = db.execute("SELECT * FROM reviews INNER JOIN users ON users.id = reviews.user_id WHERE book_id = :book_id", {"book_id": book_id}).fetchall()
    return reviews

def get_average_review(reviews):
    average = 0
    if reviews:
        if len(reviews) > 0:
            for review in reviews:
                average += review.rating
            average = average/len(reviews)
    return average

def get_average_stars(average):
    average = float(average)
    fraction, whole = math.modf(average)
    if fraction < 0.1:
        full_stars = int(whole)
        half_stars = 0
    elif fraction > 0.9:
        full_stars = int(whole) + 1
        half_stars = 0
    else:
        full_stars = int(whole)
        half_stars = 1
    empty_stars = 5 - full_stars - half_stars
    return full_stars, half_stars, empty_stars

def get_average_full_stars(average):
    full_stars, half_stars, empty_stars = get_average_stars(average)
    return full_stars

def get_average_half_stars(average):
    full_stars, half_stars, empty_stars = get_average_stars(average)
    return half_stars

def get_average_empty_stars(average):
    full_stars, half_stars, empty_stars = get_average_stars(average)
    return empty_stars

def get_number_of_reviews(reviews):
    number = 0
    if reviews:
        number = len(reviews) 
    return number

def user_already_submitted_review(user_id, reviews):
    already_reviewed = False
    for review in reviews:
        if review.user_id == user_id:
            already_reviewed = True
    return already_reviewed

def get_goodreads_book_reviews(isbn):
    goodreads_reviews = None
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": goodreads_key, "isbns": isbn})
    if res.status_code == 200:
        books = res.json()['books']
        goodreads_reviews = books[0]
    return goodreads_reviews

def store_review(book_id, user_id, rating, comment):
    db.execute("INSERT INTO reviews (book_id, user_id, rating, comment) VALUES (:book_id, :user_id, :rating, :comment)", {"book_id": book_id, "user_id": user_id, "rating": rating, "comment": comment})
    db.commit()
    return


@app.before_request
def load_logged_in_user():   
    # If no-one is logged in
    user_id = session.get('user_id')
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
    # Initialize variables
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
    # Initialize variables
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
    # Initialize variables
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
    # Initialize variables
    error = None
    reviews = None
    goodreads_reviews = None

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

    # If everything is OK then...
    if error is None:
        reviews = get_book_reviews(book.id)
        goodreads_reviews = get_goodreads_book_reviews(isbn)

    if request.method == 'POST':
        # Obtain the review parameters from the form
        rating = request.form['rating']
        comment = request.form['comment']

        # Check if comment is too short
        if len(comment) == 0:
            error = f'You must enter a comment.'
            print(error)
        # Check if user already has submitted a review
        elif user_already_submitted_review(g.user.id, reviews):
            error = f'You already submitted a review for this book.'
            print(error)

        # If everything is OK then...
        if error is None:
            # Store in DB
            store_review(book.id, g.user.id, rating, comment)
            return redirect(url_for('review'))

    return render_template('book.html',
                            get_average_full_stars=get_average_full_stars,
                            get_average_half_stars=get_average_half_stars,
                            get_average_empty_stars=get_average_empty_stars,
                            get_average_review=get_average_review,
                            get_number_of_reviews=get_number_of_reviews,
                            book=book,
                            reviews=reviews,
                            goodreads_reviews=goodreads_reviews,
                            error=error)

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/api/book/<string:isbn>')
def book_api(isbn):
    # Initialize variables
    error = None
    reviews = None

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

    # If an error occurs
    if error is not None:
        return jsonify({"error": error}), 404

    # If everything is OK then...
    reviews = get_book_reviews(book.id)

    # Build the JSON repy
    reply = jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": get_number_of_reviews(reviews),
        "average_score": get_average_review(reviews)
    })
    
    return reply

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))