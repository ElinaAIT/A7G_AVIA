from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt  # добавили get_jwt
from model import db, Flight, Ticket  # добавили Ticket
from datetime import datetime, timedelta  # для статистики и дат

company_bp = Blueprint("company", __name__)

# Добавить рейс
@company_bp.route("/flights", methods=["POST"])
@jwt_required()
def add_flight():
    user_id = get_jwt_identity()  # str(id)
    role = get_jwt()["role"]
    if role != "manager":
        return jsonify({"error": "Нет доступа"}), 403

    data = request.get_json()
    flight = Flight(
        company_id=1,  # можно связать с таблицей Company
        origin=data["origin"],
        destination=data["destination"],
        date=data["date"],
        price=data["price"],
        seats=data["seats"]
    )
    db.session.add(flight)
    db.session.commit()
    return jsonify({"message": "Рейс добавлен"}), 201

# Список рейсов компании
@company_bp.route("/flights", methods=["GET"])
@jwt_required()
def list_flights():
    user_id = get_jwt_identity()  # str(id)
    role = get_jwt()["role"]
    if role != "manager":
        return jsonify({"error": "Нет доступа"}), 403

    flights = Flight.query.all()
    return jsonify([
        {"id": f.id, "origin": f.origin, "destination": f.destination,
         "date": f.date, "price": f.price, "seats": f.seats}
        for f in flights
    ])

# Статистика компании
@company_bp.route("/stats", methods=["GET"])
@jwt_required()
def company_stats():
    user_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "manager":
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

    # Фильтр рейсов (пока all, потом по company_id)
    query = Flight.query
    if start_date:
        query = query.filter(Flight.date >= str(start_date))

    flights = query.all()
    total_flights = len(flights)

    # Предстоящие/завершённые
    upcoming = len([f for f in flights if datetime.strptime(f.date, "%Y-%m-%d").date() > now.date()])
    completed = total_flights - upcoming

    # Пассажиры (по билетам на рейсах)
    total_passengers = sum([db.session.query(Ticket).filter_by(flight_id=f.id).count() for f in flights])

    # Выручка (сумма price * sold seats, но упрощённо: price * (initial_seats - seats))
    total_revenue = sum([f.price * (100 - f.seats) for f in flights])  # предположим initial=100, подкорректируй

    return jsonify({
        "total_flights": total_flights,
        "upcoming": upcoming,
        "completed": completed,
        "total_passengers": total_passengers,
        "total_revenue": total_revenue,
        "period": period
    })