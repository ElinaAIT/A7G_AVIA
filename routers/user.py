from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt  # добавили get_jwt
from model import db, Flight, Ticket
from datetime import datetime, timedelta  # для отмены билета

user_bp = Blueprint("user", __name__)

# Получить список всех рейсов (с фильтрами)
@user_bp.route("/flights", methods=["GET"])
@jwt_required()
def get_flights():
    role = get_jwt()["role"]
    if role != "user":
        return jsonify({"error": "Нет доступа"}), 403

    origin = request.args.get("origin")
    destination = request.args.get("destination")
    date = request.args.get("date")
    flight_id = request.args.get("flight_id")
    
    query = Flight.query
    # если запрошен конкретный рейс по id — фильтруем по нему
    if flight_id:
        try:
            fid = int(flight_id)
            query = query.filter(Flight.id == fid)
        except Exception:
            return jsonify({"error": "Неверный flight_id"}), 400
    if origin:
        query = query.filter(Flight.origin.ilike(f"%{origin}%"))
    if destination:
        query = query.filter(Flight.destination.ilike(f"%{destination}%"))
    if date:
        query = query.filter(Flight.date == date)
    
    flights = query.all()
    data = [
        {"id": f.id, "origin": f.origin, "destination": f.destination,
         "date": f.date, "price": f.price, "seats": f.seats}
        for f in flights
    ]
    return jsonify(data)


# Публичный список рейсов (без авторизации) — для поиска с главной страницы
@user_bp.route("/public/flights", methods=["GET"])
def public_get_flights():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    date = request.args.get("date") or request.args.get("dateFrom")
    flight_id = request.args.get("flight_id")

    query = Flight.query
    if flight_id:
        try:
            fid = int(flight_id)
            query = query.filter(Flight.id == fid)
        except Exception:
            return jsonify({"error": "Неверный flight_id"}), 400
    if origin:
        query = query.filter(Flight.origin.ilike(f"%{origin}%"))
    if destination:
        query = query.filter(Flight.destination.ilike(f"%{destination}%"))
    if date:
        query = query.filter(Flight.date == date)

    flights = query.all()
    data = [
        {"id": f.id, "origin": f.origin, "destination": f.destination,
         "date": f.date, "price": f.price, "seats": f.seats}
        for f in flights
    ]
    return jsonify(data)

# Купить билет
@user_bp.route("/tickets", methods=["POST"])
@jwt_required()
def buy_ticket():
    user_id = get_jwt_identity()  # str(id)
    role = get_jwt()["role"]
    if role != "user":
        return jsonify({"error": "Нет доступа"}), 403

    data = request.get_json() or {}
    flight_id = data.get("flight_id")
    qty = int(data.get("quantity", 1) or 1)

    if qty <= 0:
        return jsonify({"error": "Неправильное количество мест"}), 400

    flight = Flight.query.get(flight_id)
    if not flight:
        return jsonify({"error": "Рейс не найден"}), 404
    if flight.seats < qty:
        return jsonify({"error": "Недостаточно мест", "available": flight.seats}), 400

    # create tickets
    tickets_created = []
    for i in range(qty):
        ticket = Ticket(user_id=int(user_id), flight_id=flight_id, status="paid")
        db.session.add(ticket)
        db.session.flush()  # assign id
        tickets_created.append(ticket.id)

    # decrement seats
    flight.seats -= qty
    db.session.commit()

    total_paid = data.get('paid_amount_eur') or (flight.price * qty if flight.price else 0)
    return jsonify({"message": "Билеты куплены", "ticket_ids": tickets_created, "total_paid_eur": total_paid}), 201

# Мои билеты
@user_bp.route("/tickets", methods=["GET"])
@jwt_required()
def my_tickets():
    user_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "user":
        return jsonify({"error": "Нет доступа"}), 403

    tickets = Ticket.query.filter_by(user_id=int(user_id)).all()
    data = [
        {"id": t.id, "flight": t.flight_id, "status": t.status}
        for t in tickets
    ]
    return jsonify(data)

# Отмена билета
@user_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
@jwt_required()
def cancel_ticket(ticket_id):
    user_id = get_jwt_identity()
    role = get_jwt()["role"]
    if role != "user":
        return jsonify({"error": "Нет доступа"}), 403

    ticket = Ticket.query.filter_by(id=ticket_id, user_id=int(user_id)).first()
    if not ticket:
        return jsonify({"error": "Билет не найден"}), 404

    flight = Flight.query.get(ticket.flight_id)
    if not flight:
        return jsonify({"error": "Рейс не найден"}), 404
    # Разрешаем удалять билет только если до вылета более 24 часов.
    # В противном случае отмена запрещена.
    # Поддерживаем оба формата даты: "YYYY-MM-DD" и ISO с временем.
    try:
        flight_date = datetime.strptime(flight.date, "%Y-%m-%d")
    except Exception:
        try:
            flight_date = datetime.fromisoformat(flight.date)
        except Exception:
            return jsonify({"error": "Неверный формат даты рейса"}), 500

    now = datetime.now()
    if (flight_date - now) > timedelta(hours=24):
        # Удаляем запись билета и возвращаем место
        db.session.delete(ticket)
        flight.seats += 1
        db.session.commit()
        return jsonify({"message": "Билет успешно отменён и удалён"}), 200
    else:
        return jsonify({"error": "Билет можно отменить только не позднее чем за 24 часа до вылета"}), 400