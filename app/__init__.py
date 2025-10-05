from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Import models here to avoid circular import
    from . import models
    from .models import User, Recipe

    # Flask-Login user loader
    @login.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .auth import bp as auth_bp
    from .recipes import bp as recipes_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp, url_prefix="/recipes")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Home route
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("recipes.index"))
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
