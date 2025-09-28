from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from .models import User

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Blueprints importieren
    from .auth import bp as auth_bp
    from .recipes import bp as recipes_bp
    from .api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp, url_prefix="/recipes")
    app.register_blueprint(api_bp, url_prefix="/api")

    # Startseite
    @app.route("/")
    def index():
        from .models import Recipe
        recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(10).all()
        from flask import render_template
        return render_template("index.html", recipes=recipes)

    return app
