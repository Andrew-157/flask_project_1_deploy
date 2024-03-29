import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def bad_request(e):
    return render_template('errors/400.html'), 400


def page_not_found(e):
    return render_template('errors/404.html'), 404


def permission_denied_for_page(e):
    return render_template('errors/403.html'), 403


def method_not_allowed_for_page(e):
    return render_template('errors/405.html')


def create_app(config_name: str = 'production'):

    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object(config[config_name])

    # Apply handling of status code with custom templates
    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(403, permission_denied_for_page)
    app.register_error_handler(405, method_not_allowed_for_page)

    # Import of 'models' module is necessary
    # so that Flask-Migrate detects changes there
    from . import models, main, auth

    # Initialize database and migrations
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def login_user(user_id):
        return models.User.query.get(int(user_id))

    # Enable CSRF-protection globally for application
    csrf.init_app(app)

    # Register blueprints
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)

    return app
