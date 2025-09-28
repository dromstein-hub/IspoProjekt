from flask import Blueprint, render_template, redirect, url_for, flash, request
from . import db
from .models import User
from flask_login import login_user, logout_user, login_required

# Hier den Blueprint definieren
bp = Blueprint("auth", __name__)

@bp.route("/register", methods=["GET","POST"])
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
        return redirect(url_for("index"))

    return render_template("register.html")

@bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Ungültige Anmeldedaten")
            return redirect(url_for("auth.login"))
        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
