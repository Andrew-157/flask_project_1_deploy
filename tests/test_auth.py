import pytest
from flask import Response
from flask import session
from flask_login import current_user
from werkzeug.security import generate_password_hash
from .conftest import AuthActions
from app import db
from app.models import User


def test_register(client, app):
    assert client.get('/auth/register/').status_code == 200
    response: Response = client.post(
        '/auth/register/', data={'username': 'random_user',
                                 'email': 'random@gmail.com',
                                 'password': '34somepassword34',
                                 'password1': '34somepassword34'})
    messages = None
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == '/'
    assert messages['success'] == 'You successfully registered to Asklee'
    with app.app_context():
        assert db.session.query(User).\
            filter_by(username='random_user').first() is not None


@pytest.mark.parametrize(('username', 'email', 'password', 'password1', 'message'),
                         (('', 'random@gmail.com', '34somepassword34',
                          '34somepassword34', b'Username is required.'),
                         ('random_user', 'dsfrgthy', '34somepassword34',
                          '34somepassword34', b'Email address is not valid.'),
                         ('random_user', 'random@gmail.com',
                          '123', '123', b'Password is too short.'),
                         ('random_user', 'random@gmail.com', '34somepassword34',
                          '43somepassword43', b'Passwords do not match.'),
                         ('test_user', 'random@gmail.com', '34somepassword34', '34somepassword34',
                          b'User with this username already exists.'))
                         )
def test_register_validate_input(client, username, email, password, password1, message):
    response: Response = client.post('/auth/register/',
                                     data={
                                         "username": username,
                                         "email": email,
                                         "password": password,
                                         "password1": password1
                                     })
    assert response.status_code == 200
    assert message in response.data


def test_login(client, auth: AuthActions):
    assert client.get('/auth/login/').status_code == 200
    response = auth.login()
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert messages['success'] == 'Welcome back to Asklee'
    with client:
        client.get('/')
        test_user = db.session.query(User).filter_by(
            username='test_user').first()
        assert current_user.id == test_user.id


@pytest.mark.parametrize(('email', 'password', 'message'),
                         (
    ('not_valid@gmail.com', '34somepassword34', b'This email was not found.'),
    ('test_user@gmail.com', 'sdfgher', b'Password does not match.')
))
def test_login_validate_input(auth: AuthActions, email, password, message):
    response = auth.login(email, password)
    assert message in response.data


def test_logout(client, auth: AuthActions):
    auth.login()
    response: Response = client.get('/auth/logout/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert messages['success'] == 'You successfully logged out'


def test_logout_for_not_logged_user(client):
    response: Response = client.get('/auth/logout/')
    assert response.status_code == 302
    assert (response.headers['Location'].startswith('/auth/login/'))


def test_change_profile(auth, client):
    auth.login()
    assert client.get('/auth/change_profile/').status_code == 200
    response: Response = client.post('/auth/change_profile/',
                                     data={
                                         'email': 'test_user1@gmail.com',
                                         'username': 'test_user1'
                                     })
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == '/'
    assert messages['success'] == 'You successfully updated your profile'


@pytest.mark.parametrize(('username', 'email', 'message'),
                         (('', 'random@gmail.com', b'Username is required.'),
                         ('test_user', 'dsfrgthy', b'Email address is not valid.'),
                         ('random_name', 'random@gmail.com',
                          b'User with this username already exists.'),
                         ('shor', 'test_user@gmail.com', b'Username is too short.')
                          ))
def test_change_profile_validate_input(app, client, auth: AuthActions, username, email, message):
    user = User(username='random_name',
                email='random_email@gmail.com',
                password=generate_password_hash("34somepassword34"))
    with app.app_context():
        db.session.add(user)
        db.session.commit()
    auth.login()
    response: Response = client.post('/auth/change_profile/',
                                     data={'username': username,
                                           'email': email})
    assert response.status_code == 200
    assert message in response.data


def test_change_profile_for_not_logged_user(app, client):
    response: Response = client.get('/auth/change_profile/')
    assert response.status_code == 302
    assert (response.headers['Location'].startswith('/auth/login/'))
