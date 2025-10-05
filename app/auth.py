from flask import Blueprint, render_template, redirect, url_for, flash, request
from . import db
from .models import User, Recipe, Favorite
from flask_login import login_user, logout_user, login_required, current_user

# Hier den Blueprint definieren
bp = Blueprint("auth", __name__)

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("Bitte alle Felder ausfüllen")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Benutzername bereits vergeben")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("E-Mail bereits registriert")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("recipes.index"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Ungültige Anmeldedaten")
            return redirect(url_for("auth.login"))
        login_user(user)
        return redirect(url_for("recipes.index"))

    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Du wurdest erfolgreich abgemeldet", "success")
    return redirect(url_for("auth.login"))


@bp.route("/profile")
@login_required
def profile():
    user_recipes = Recipe.query.filter_by(created_by=current_user.id).order_by(Recipe.created_at.desc()).all()

    favorite_recipes = (
        Recipe.query
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )

    return render_template("profile.html", user_recipes=user_recipes, favorite_recipes=favorite_recipes)