from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from model import db, User

auth_bp = Blueprint("auth", __name__)

# Регистрация
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "user")  # по умолчанию обычный пользователь

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Пользователь уже существует"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Регистрация успешна"}), 201

# Логин
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Неверный логин или пароль"}), 401

    # Заблокированные пользователи не могут войти
    if getattr(user, 'blocked', False):
        return jsonify({"error": "Вы заблокированы"}), 403

    # Фикс: identity как строка (sub), роль в additional_claims
    token = create_access_token(
        identity=str(user.id),  # sub = str(id)
        additional_claims={"role": user.role}
    )
    return jsonify({"access_token": token, "role": user.role}), 200