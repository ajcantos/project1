import os

from flask import Flask, session, render_template, request
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


def check_user_credentials(email, password):
    access = 'denied'
    if email == 'a.j.cantos@gmail.com':
        if password == '111111':
            access = 'granted'
    return access

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'GET':
        access = 'initial'
        return render_template('signin.html', access=access, name=None)
    else:
        email = request.form.get('email')
        password = request.form.get('password')
        access = check_user_credentials(email, password)
        return render_template('signin.html', access=access, name=email)

@app.route('/signup')
def signup():
    return render_template('signup.html')
