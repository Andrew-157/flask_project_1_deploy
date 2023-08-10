import re
from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from .models import User
from . import db

bp = Blueprint('auth', __name__, url_prefix='/auth')


def username_is_valid(username: str) -> bool:
    # Function to check if user uses only valid
    # symbols for their username
    allowed_symbols = "1234567890 \
                    abcdefghijklmnopqrstuvwxyz\
                    ABCDEFGHIJKLMNOPQRSTUVWXYZ@.+-_"
    for symbol in username:
        if symbol not in allowed_symbols:
            return False
    return True


def email_is_valid(email: str) -> bool:
    # Check validity of email
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.fullmatch(regex, email):
        return False
    return True


@bp.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password1 = request.form['password1']
        remember = True if request.form.get('remember') else False
        errors = False

        # Check that user entered the necessary data
        if not username:
            flash('Username is required.')
            errors = True
        if not email:
            flash('Email is required.')
            errors = True
        if not password:
            flash('Password is required.')
            errors = True

        # Check that the entered data is not too long
        # the existence of email, username and password is checked again
        # so that if somehow None was passed, that we do not
        # call 'len' function on None and get
        if username and len(username) > 50:
            flash('Username is too long.')
            errors = True
        if email and len(email) > 120:
            flash('Email is too long.')
            errors = True
        if password and len(password) > 200:
            flash('Password is too long.')
            errors = True

        # Check that passwords match
        if password != password1:
            flash('Passwords do not match.')
            errors = True

        # Check that the entered data is not too short
        if username and len(username) < 5:
            flash('Username is too short.')
            errors = True
        if password and len(password) < 8:
            flash('Password is too short.')
            errors = True

        # If username was provided, check that it contains only valid symbols
        if username and not username_is_valid(username):
            flash('Username is not valid.Letters, digits and @/./+/-/_ only.')
            errors = True
        # If email was provide, check that it is valid
        if email and not email_is_valid(email):
            flash('Email address is not valid.')
            errors = True

        user_with_email = db.session.query(User).filter_by(email=email).first()
        user_with_username = db.session.query(
            User).filter_by(username=username).first()

        # Check that username and email are unique
        if user_with_email:
            flash('User with this email already exists.')
            errors = True
        if user_with_username:
            flash('User with this username already exists.')
            errors = True

        if errors:
            return render_template('auth/register.html', username=username,
                                   email=email)
            # return redirect(url_for('auth.register'))

        new_user = User(username=username,
                        email=email,
                        password=generate_password_hash(password))

        db.session.add(new_user)
        db.session.commit()

        login_user(user=new_user, remember=remember)

        flash('You successfully registered to Asklee', category='success')

        return redirect(url_for('main.index'))

    return render_template('auth/register.html')


@bp.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        errors = False

        if not email:
            flash('Email is required to login.')
            errors = True
        if not password:
            flash('Password is required to login.')
            errors = True

        user = db.session.query(User).filter_by(email=email).first()

        if not user:
            flash('This email was not found.')
            errors = True
        if user and not check_password_hash(user.password, password):
            flash('Password does not match.')
            errors = True

        if errors:
            return render_template('auth/login.html', email=email)

        login_user(user=user, remember=remember)
        flash('Welcome back to Asklee', 'success')

        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@bp.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You successfully logged out', 'success')
    return redirect(url_for('main.index'))


@bp.route('/change_profile/', methods=['GET', 'POST'])
@login_required
def change_profile():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        errors = False

        if not email:
            flash('Email is required.')
            errors = True
        if not username:
            flash('Username is required.')
            errors = True

        if email and len(email) > 120:
            flash('Email is too long.')
            errors = True
        if username and len(username) > 50:
            flash('Username is too long.')
            errors = True

        if username and len(username) < 5:
            flash('Username is too short.')
            errors = True

        if username and not username_is_valid(username):
            flash('Username is not valid.Letters, digits and @/./+/-/_ only.')
            errors = True

        if email and not email_is_valid(email):
            flash('Email address is not valid.')
            errors = True

        user_with_email = db.session.query(User).filter_by(email=email).first()
        user_with_username = db.session.query(
            User).filter_by(username=username).first()

        if user_with_email and (user_with_email != current_user):
            flash('User with this email already exists.')
            errors = True
        if user_with_username and (user_with_username != current_user):
            flash('User with this username already exists.')
            errors = True

        if errors:
            return render_template('auth/change_profile.html', username=username, email=email)
            # return redirect(url_for('auth.change_profile'))

        current_user.username = username
        current_user.email = email
        db.session.commit()

        flash('You successfully updated your profile', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/change_profile.html',
                           username=current_user.username,
                           email=current_user.email)
