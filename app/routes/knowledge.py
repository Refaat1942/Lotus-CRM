from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from app.decorators import feature_required
from app.models import ProductKnowledge

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/")
@login_required
@feature_required("knowledge.index")
def index():
    return render_template("knowledge/index.html")


@knowledge_bp.route("/api/search")
@login_required
@feature_required("knowledge.index")
def search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify([])
    rows = ProductKnowledge.query.filter(
        or_(
            ProductKnowledge.item_code.ilike(f"%{keyword}%"),
            ProductKnowledge.item_name.ilike(f"%{keyword}%"),
        )
    ).limit(100).all()
    return jsonify(
        [
            {
                "item_code": r.item_code,
                "item_name": r.item_name,
                "active_ingredient": r.active_ingredient,
                "medical_use": r.medical_use,
            }
            for r in rows
        ]
    )


@knowledge_bp.route("/api/alternatives")
@login_required
@feature_required("knowledge.index")
def alternatives():
    ingredient = request.args.get("ingredient", "").strip()
    if not ingredient:
        return jsonify([])
    rows = ProductKnowledge.query.filter(
        ProductKnowledge.active_ingredient.ilike(f"%{ingredient}%")
    ).limit(100).all()
    return jsonify(
        [
            {
                "item_code": r.item_code,
                "item_name": r.item_name,
                "active_ingredient": r.active_ingredient,
            }
            for r in rows
        ]
    )
