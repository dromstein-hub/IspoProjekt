from flask import Blueprint, render_template, request, redirect, url_for, flash
from . import db
from .models import Recipe, Comment
from flask_login import login_required, current_user

bp = Blueprint("recipes", __name__)

@bp.route("/")
def index():
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template("recipes/index.html", recipes=recipes)

@bp.route("/new", methods=["GET","POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        ingredients = request.form.get("ingredients")
        steps = request.form.get("steps")
        category = request.form.get("category")
        duration = request.form.get("duration")
        difficulty = request.form.get("difficulty")

        if not title:
            flash("Titel erforderlich")
            return redirect(url_for("recipes.create"))

        r = Recipe(
            title=title, description=description, ingredients=ingredients,
            steps=steps, category=category,
            duration_min=int(duration) if duration else None,
            difficulty=difficulty, created_by=current_user.id
        )
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("recipes.view", recipe_id=r.id))

    return render_template("recipes/new.html")

@bp.route("/<int:recipe_id>")
def view(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    comments = Comment.query.filter_by(recipe_id=recipe_id).order_by(Comment.created_at.desc()).all()
    return render_template("recipes/view.html", recipe=r, comments=comments)

@bp.route("/<int:recipe_id>/comment", methods=["POST"])
@login_required
def comment(recipe_id):
    text = request.form.get("text")
    if not text:
        flash("Kommentar leer")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))
    c = Comment(recipe_id=recipe_id, user_id=current_user.id, text=text)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for("recipes.view", recipe_id=recipe_id))
