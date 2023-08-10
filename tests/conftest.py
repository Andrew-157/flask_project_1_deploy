from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

import pytest
from app import create_app, db
from app.models import User


load_dotenv()


@pytest.fixture
def app():

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": 'sqlite:///:memory:',
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        test_user = User(username='test_user',
                         email='test_user@gmail.com',
                         password=generate_password_hash('34somepassword34'))
        db.session.add(test_user)
        db.session.commit()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# @pytest.fixture
# def runner(app):
#     return app.test_cli_runner()


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self,
              email="test_user@gmail.com",
              password="34somepassword34"):
        return self._client.post(
            '/auth/login/',
            data={'email': email,
                  'password': password}
        )

    # def logout(self):
    #     return self._client.get(
    #         '/auth/logout/'
    #     )


@pytest.fixture
def auth(client):
    return AuthActions(client)
