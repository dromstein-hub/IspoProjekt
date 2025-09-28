from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from .models import User, Recipe

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "auth.login"  # make sure your auth blueprint has a login route

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

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

    # Home page route
    @app.route("/")
    def index():
        # Fetch latest 10 recipes
        recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(10).all()
        return render_template("index.html", recipes=recipes)

    return app
