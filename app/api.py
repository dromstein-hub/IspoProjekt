from flask import Blueprint, jsonify, request, current_app
from .models import Recipe, User, Comment, Rating, Favorite
from . import db
import jwt
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint("api", __name__)

@bp.route("/token", methods=["POST"])
def get_token():
    auth = request.authorization
    if not auth:
        return jsonify({"message": "Missing credentials"}), 401
    user = User.query.filter_by(username=auth.username).first()
    if user is None or not user.check_password(auth.password):
        return jsonify({"message": "Invalid credentials"}), 401
    payload = {"user_id": user.id, "exp": datetime.utcnow() + timedelta(hours=24)}
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    return jsonify({"token": token})

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return jsonify({"message":"Token fehlt"}), 401
        try:
            token = auth_header.split()[1]
            data = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
            user = User.query.get(data["user_id"])
            if not user:
                raise Exception("User nicht gefunden")
            request.user = user
        except Exception as e:
            return jsonify({"message": "Ungültiger Token", "error": str(e)}), 401
        return f(*args, **kwargs)
    return decorated

@bp.route("/recipes", methods=["GET"])
def list_recipes():
    page = int(request.args.get("page", 1))
    per = int(request.args.get("per_page", 20))
    q = Recipe.query.order_by(Recipe.created_at.desc())
    recipes = q.paginate(page=page, per_page=per, error_out=False)
    data = [{"id": r.id, "title": r.title, "category": r.category, "duration_min": r.duration_min} for r in recipes.items]
    return jsonify({"recipes": data, "page": page, "total": recipes.total})

@bp.route("/recipes/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    return jsonify({
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "ingredients": r.ingredients,
        "steps": r.steps,
        "category": r.category,
        "duration_min": r.duration_min,
        "difficulty": r.difficulty
    })

@bp.route("/recipes", methods=["POST"])
@token_required
def create_recipe():
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"message":"Title required"}), 400
    r = Recipe(
        title=data.get("title"),
        description=data.get("description"),
        ingredients=data.get("ingredients"),
        steps=data.get("steps"),
        category=data.get("category"),
        duration_min=data.get("duration_min"),
        difficulty=data.get("difficulty"),
        created_by=request.user.id
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"id": r.id}), 201


@bp.route("/recipes/<int:recipe_id>/comments", methods=["GET"])
def get_comments(recipe_id):
    comments = Comment.query.filter_by(recipe_id=recipe_id).order_by(Comment.created_at.desc()).all()
    data = [{
        "id": c.id,
        "text": c.text,
        "user_id": c.user_id,
        "created_at": c.created_at.isoformat()
    } for c in comments]
    return jsonify({"comments": data})


@bp.route("/recipes/<int:recipe_id>/comments", methods=["POST"])
@token_required
def create_comment(recipe_id):
    data = request.get_json() or {}
    if not data.get("text"):
        return jsonify({"message": "Text required"}), 400
    c = Comment(recipe_id=recipe_id, user_id=request.user.id, text=data.get("text"))
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id}), 201


@bp.route("/recipes/<int:recipe_id>/ratings", methods=["POST"])
@token_required
def rate_recipe(recipe_id):
    data = request.get_json() or {}
    stars = data.get("stars")
    if not stars or stars < 1 or stars > 5:
        return jsonify({"message": "Stars must be 1-5"}), 400

    existing = Rating.query.filter_by(recipe_id=recipe_id, user_id=request.user.id).first()
    if existing:
        existing.stars = stars
    else:
        rating = Rating(recipe_id=recipe_id, user_id=request.user.id, stars=stars)
        db.session.add(rating)
    db.session.commit()
    return jsonify({"message": "Rating saved"}), 200


@bp.route("/favorites", methods=["GET"])
@token_required
def list_favorites():
    favs = Favorite.query.filter_by(user_id=request.user.id).all()
    recipe_ids = [f.recipe_id for f in favs]
    recipes = Recipe.query.filter(Recipe.id.in_(recipe_ids)).all() if recipe_ids else []
    data = [{"id": r.id, "title": r.title, "image_url": r.image_url} for r in recipes]
    return jsonify({"favorites": data}), 200


@bp.route("/recipes/<int:recipe_id>/favorite", methods=["POST"])
@token_required
def add_favorite(recipe_id):
    Recipe.query.get_or_404(recipe_id)
    existing = Favorite.query.filter_by(recipe_id=recipe_id, user_id=request.user.id).first()
    if not existing:
        fav = Favorite(recipe_id=recipe_id, user_id=request.user.id)
        db.session.add(fav)
        db.session.commit()
    return jsonify({"message": "Favorited"}), 201


@bp.route("/recipes/<int:recipe_id>/favorite", methods=["DELETE"])
@token_required
def remove_favorite(recipe_id):
    existing = Favorite.query.filter_by(recipe_id=recipe_id, user_id=request.user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    return jsonify({"message": "Unfavorited"}), 200