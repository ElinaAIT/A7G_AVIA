from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt  # добавили get_jwt
from model import db, User, Company, Flight, Ticket  # добавили Flight, Ticket для stats
from datetime import datetime, timedelta  # для статистики
from werkzeug.security import generate_password_hash
import secrets
import base64, hashlib
from cryptography.fernet import Fernet

admin_bp = Blueprint("admin", __name__)

# Список пользователей
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    user_id = get_jwt_identity()  # str(id)
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    users = User.query.all()
    return jsonify([{"id": u.id, "username": u.username, "role": u.role, "blocked": u.blocked} for u in users])  # добавили "blocked": u.blocked

# Блокировка пользователя
@admin_bp.route("/users/<int:user_id>/block", methods=["PUT"])
@jwt_required()
def block_user(user_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    user.blocked = True  # добавь поле blocked в модель User: blocked = db.Column(db.Boolean, default=False)
    db.session.commit()
    return jsonify({"message": "Пользователь заблокирован"}), 200

# Разблокировка пользователя
@admin_bp.route("/users/<int:user_id>/unblock", methods=["PUT"])
@jwt_required()
def unblock_user(user_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    user.blocked = False
    db.session.commit()
    return jsonify({"message": "Пользователь разблокирован"}), 200

# Добавить компанию
@admin_bp.route("/companies", methods=["POST"])
@jwt_required()
def add_company():
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "Пустой запрос"}), 400
    if not data.get("name"):
        return jsonify({"error": "Название компании обязательно"}), 400
    manager_id = data.get("manager_id")

    # Если менеджер не указан, создаём аккаунт-менеджер автоматически
    created_credentials = None
    if not manager_id:
        # Создаём уникальный username на основе названия
        base = (data.get("name") or "manager").lower().replace(' ', '_')
        username = base
        # Обеспечим уникальность
        while User.query.filter_by(username=username).first():
            username = f"{base}_{secrets.token_hex(2)}"

        password = secrets.token_urlsafe(8)
        hashed = generate_password_hash(password)
        new_user = User(username=username, password=hashed, role="manager")
        db.session.add(new_user)
        db.session.commit()
        manager_id = new_user.id
        created_credentials = {"manager_username": username, "manager_password": password, "manager_id": manager_id}

    # если админ указал пароль для компании — зашифруем и сохраним
    company_password = data.get("company_password")
    company = Company(name=data["name"], manager_id=manager_id)
    # помечаем, что компания создана через админку (вне зависимости от наличия пароля)
    company.is_admin_created = True
    if company_password:
        try:
            # создаём Fernet на основе секретного ключа приложения
            secret = current_app.config.get("JWT_SECRET_KEY", "secret-key")
            digest = hashlib.sha256(secret.encode()).digest()
            key = base64.urlsafe_b64encode(digest)
            f = Fernet(key)
            company.encrypted_password = f.encrypt(company_password.encode()).decode()
        except Exception as e:
            current_app.logger.exception('Ошибка при шифровании пароля компании')
            return jsonify({"error": "Не удалось зашифровать пароль компании"}), 500

    try:
        db.session.add(company)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Ошибка при сохранении компании в БД')
        return jsonify({"error": "Не удалось создать компанию", "detail": str(e)}), 500

    response = {"message": "Компания добавлена", "id": company.id}
    if created_credentials:
        response.update(created_credentials)
    return jsonify(response), 201


# Список компаний, созданных через админку
@admin_bp.route("/companies", methods=["GET"])
@jwt_required()
def list_companies():
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    # Показываем все компании — чтобы админ видел все записи (и старые, и добавленные через админку)
    companies = Company.query.order_by(Company.id.asc()).all()
    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "manager_id": c.manager_id,
            "is_admin_created": getattr(c, 'is_admin_created', False),
            "blocked": getattr(c, 'blocked', False),
            "encrypted_password": bool(getattr(c, 'encrypted_password', None))
        }
        for c in companies
    ])



# Показать пароль компании (раскрывает зашифрованный пароль, только для админа)
@admin_bp.route("/companies/<int:company_id>/reveal", methods=["GET"])
@jwt_required()
def reveal_company_password(company_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Компания не найдена"}), 404
    if not company.is_admin_created or not company.encrypted_password:
        return jsonify({"error": "Пароль для этой компании не доступен"}), 400

    secret = current_app.config.get("JWT_SECRET_KEY", "secret-key")
    digest = hashlib.sha256(secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    f = Fernet(key)
    try:
        password = f.decrypt(company.encrypted_password.encode()).decode()
    except Exception:
        return jsonify({"error": "Не удалось расшифровать пароль"}), 500

    return jsonify({"password": password}), 200

# Удаление/деактивация компании
@admin_bp.route("/companies/<int:company_id>", methods=["DELETE"])
@jwt_required()
def delete_company(company_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Компания не найдена"}), 404

    try:
        db.session.delete(company)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Ошибка при удалении компании')
        return jsonify({"error": "Не удалось удалить компанию", "detail": str(e)}), 500
    return jsonify({"message": "Компания удалена"}), 200


# Блокировка компании (для компаний, созданных через админку)
@admin_bp.route("/companies/<int:company_id>/block", methods=["PUT"])
@jwt_required()
def block_company(company_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Компания не найдена"}), 404
    # allow admin to manage any company (remove is_admin_created restriction)

    company.blocked = True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Ошибка при блокировке компании')
        return jsonify({"error": "Не удалось заблокировать компанию", "detail": str(e)}), 500
    return jsonify({"message": "Компания заблокирована"}), 200


# Разблокировка компании (для компаний, созданных через админку)
@admin_bp.route("/companies/<int:company_id>/unblock", methods=["PUT"])
@jwt_required()
def unblock_company(company_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Компания не найдена"}), 404
    # allow admin to manage any company (remove is_admin_created restriction)

    company.blocked = False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Ошибка при разблокировке компании')
        return jsonify({"error": "Не удалось разблокировать компанию", "detail": str(e)}), 500
    return jsonify({"message": "Компания разблокирована"}), 200

# Назначение менеджера компании (PUT /companies/{id}/manager)
@admin_bp.route("/companies/<int:company_id>/manager", methods=["PUT"])
@jwt_required()
def assign_manager(company_id):
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    data = request.get_json()
    manager_id = data.get("manager_id")

    company = Company.query.get(company_id)
    if not company:
        return jsonify({"error": "Компания не найдена"}), 404

    user = User.query.get(manager_id)
    if not user or user.role != "manager":
        return jsonify({"error": "Менеджер не найден или не назначен роль manager"}), 400

    company.manager_id = manager_id
    db.session.commit()
    return jsonify({"message": "Менеджер назначен"}), 200

# Статистика платформы
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def admin_stats():
    admin_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "admin":
        return jsonify({"error": "Нет доступа"}), 403

    period = request.args.get("period", "all")  # today/week/month/all
    now = datetime.now()

    if period == "today":
        start_date = now.date()
    elif period == "week":
        start_date = now.date() - timedelta(days=7)
    elif period == "month":
        start_date = now.date() - timedelta(days=30)
    else:
        start_date = None  # all

    # Фильтр рейсов
    query = Flight.query
    if start_date:
        query = query.filter(Flight.date >= str(start_date))

    flights = query.all()
    total_flights = len(flights)

    # Предстоящие/завершённые
    upcoming = len([f for f in flights if datetime.strptime(f.date, "%Y-%m-%d").date() > now.date()])
    completed = total_flights - upcoming

    # Пассажиры (все билеты)
    total_passengers = db.session.query(Ticket).count() if not start_date else db.session.query(Ticket).join(Flight).filter(Flight.date >= str(start_date)).count()

    # Выручка (упрощённо)
    total_revenue = sum([f.price * (100 - f.seats) for f in flights])  # предположим initial=100

    return jsonify({
        "total_flights": total_flights,
        "upcoming": upcoming,
        "completed": completed,
        "total_passengers": total_passengers,
        "total_revenue": total_revenue,
        "period": period
    })