from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from . import db
import os
import time
from .models import Recipe, Comment, Rating, Favorite
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

bp = Blueprint("recipes", __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route("/")
@login_required
def index():
    # Filter
    category = request.args.get("category")
    sort_by = request.args.get("sort", "date")

    query = Recipe.query

    if category:
        query = query.filter_by(category=category)

    # Sortierung
    if sort_by == "rating":
        # Sortiere nach durchschnittlicher Bewertung (komplexer)
        recipes = query.all()
        recipes.sort(key=lambda r: r.average_rating(), reverse=True)
    else:
        recipes = query.order_by(Recipe.created_at.desc()).all()

    # Alle Kategorien für Filter
    categories = db.session.query(Recipe.category).distinct().filter(Recipe.category != None).all()
    categories = [c[0] for c in categories]

    # Favoriten-IDs des aktuellen Users
    favorite_ids = set(f.recipe_id for f in Favorite.query.filter_by(user_id=current_user.id).all())

    return render_template(
        "recipes/index.html",
        recipes=recipes,
        categories=categories,
        current_category=category,
        current_sort=sort_by,
        favorite_ids=favorite_ids
    )


@bp.route("/new", methods=["GET", "POST"])
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

        # Bild-Upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Eindeutiger Dateiname
                filename = f"{current_user.id}_{int(time.time())}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                image_url = f"/static/uploads/{filename}"

        r = Recipe(
            title=title, description=description, ingredients=ingredients,
            steps=steps, category=category,
            duration_min=int(duration) if duration else None,
            difficulty=difficulty, created_by=current_user.id,
            image_url=image_url
        )
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("recipes.view", recipe_id=r.id))

    return render_template("recipes/new.html")

@bp.route("/<int:recipe_id>")
@login_required
def view(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    comments = Comment.query.filter_by(recipe_id=recipe_id).order_by(Comment.created_at.desc()).all()

    # Prüfe ob User bereits bewertet hat
    user_rating = Rating.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    # Prüfe ob favorisiert
    user_favorited = Favorite.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first() is not None

    return render_template("recipes/view.html", recipe=r, comments=comments, user_rating=user_rating, user_favorited=user_favorited)


@bp.route("/<int:recipe_id>/comment", methods=["POST"])
@login_required
def comment(recipe_id):
    text = request.form.get("text")
    if not text:
        flash("Kommentar leer", "warning")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))
    c = Comment(recipe_id=recipe_id, user_id=current_user.id, text=text)
    db.session.add(c)
    db.session.commit()
    flash("Kommentar hinzugefügt", "success")
    return redirect(url_for("recipes.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/rate", methods=["POST"])
@login_required
def rate(recipe_id):
    stars = request.form.get("stars", type=int)

    if not stars or stars < 1 or stars > 5:
        flash("Bitte wähle 1-5 Sterne", "warning")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))

    # Prüfe ob User bereits bewertet hat
    existing_rating = Rating.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()

    if existing_rating:
        # Update existing rating
        existing_rating.stars = stars
        flash("Bewertung aktualisiert", "success")
    else:
        # Create new rating
        rating = Rating(recipe_id=recipe_id, user_id=current_user.id, stars=stars)
        db.session.add(rating)
        flash("Bewertung hinzugefügt", "success")

    db.session.commit()
    return redirect(url_for("recipes.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/edit", methods=["GET", "POST"])
@login_required
def edit(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)

    # Sicherheitscheck: Nur der Autor oder Admin darf bearbeiten
    if r.created_by != current_user.id and not current_user.is_admin:
        flash("Du darfst nur deine eigenen Rezepte bearbeiten", "danger")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))

    if request.method == "POST":
        r.title = request.form.get("title")
        r.description = request.form.get("description")
        r.ingredients = request.form.get("ingredients")
        r.steps = request.form.get("steps")
        r.category = request.form.get("category")
        duration = request.form.get("duration")
        r.duration_min = int(duration) if duration else None
        r.difficulty = request.form.get("difficulty")

        # Bild-Upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # Lösche altes Bild falls vorhanden
                if r.image_url:
                    old_image = r.image_url.replace('/static/', 'app/static/')
                    if os.path.exists(old_image):
                        os.remove(old_image)

                filename = secure_filename(file.filename)
                filename = f"{current_user.id}_{int(time.time())}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                r.image_url = f"/static/uploads/{filename}"

        if not r.title:
            flash("Titel erforderlich", "danger")
            return redirect(url_for("recipes.edit", recipe_id=recipe_id))

        db.session.commit()
        flash("Rezept erfolgreich aktualisiert", "success")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))

    return render_template("recipes/edit.html", recipe=r)


@bp.route("/<int:recipe_id>/delete", methods=["POST"])
@login_required
def delete(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)

    # Sicherheitscheck: Nur der Autor oder Admin darf löschen
    if r.created_by != current_user.id and not current_user.is_admin:
        flash("Du darfst nur deine eigenen Rezepte löschen", "danger")
        return redirect(url_for("recipes.view", recipe_id=recipe_id))

    # Lösche zuerst alle Kommentare und Ratings
    Comment.query.filter_by(recipe_id=recipe_id).delete()
    Rating.query.filter_by(recipe_id=recipe_id).delete()

    db.session.delete(r)
    db.session.commit()
    flash("Rezept erfolgreich gelöscht", "success")
    return redirect(url_for("recipes.index"))


@bp.route("/favorites")
@login_required
def favorites():
    # Rezepte, die der aktuelle User favorisiert hat
    fav_recipes = (
        Recipe.query
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Recipe.created_at.desc())
        .all()
    )
    return render_template("recipes/favorites.html", recipes=fav_recipes)


@bp.route("/<int:recipe_id>/favorite", methods=["POST"])
@login_required
def favorite(recipe_id):
    # Existiert Rezept?
    Recipe.query.get_or_404(recipe_id)
    existing = Favorite.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    if not existing:
        fav = Favorite(recipe_id=recipe_id, user_id=current_user.id)
        db.session.add(fav)
        db.session.commit()
        flash("Zu Favoriten hinzugefügt", "success")
    else:
        flash("Bereits in Favoriten", "info")
    return redirect(request.referrer or url_for("recipes.view", recipe_id=recipe_id))


@bp.route("/<int:recipe_id>/unfavorite", methods=["POST"])
@login_required
def unfavorite(recipe_id):
    existing = Favorite.query.filter_by(recipe_id=recipe_id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Aus Favoriten entfernt", "success")
    else:
        flash("Nicht in Favoriten", "info")
    return redirect(request.referrer or url_for("recipes.view", recipe_id=recipe_id))