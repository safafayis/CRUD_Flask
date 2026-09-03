from flask import Flask, request, jsonify, render_template

from extensions import db
from config import SQLALCHEMY_DATABASE_URI
from models import CrudNesto


app = Flask(__name__)

# PostgreSQL configuration
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect SQLAlchemy to Flask
db.init_app(app)


# Create the crud_nesto table if it doesn't exist
with app.app_context():
    db.create_all()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")


# ==========================================
# CREATE CUSTOMER
# ==========================================

@app.route("/api/customers", methods=["POST"])
def create_customer():

    data = request.get_json()

    customer_name = data.get("customer_name")
    gender = data.get("gender")
    amount = data.get("amount")

    if not customer_name or not gender or amount is None:
        return jsonify({
            "error": "All fields are required"
        }), 400

    customer = CrudNesto(
        customer_name=customer_name,
        gender=gender,
        amount=amount
    )

    db.session.add(customer)
    db.session.commit()

    return jsonify(customer.to_dict()), 201


# ==========================================
# READ ALL CUSTOMERS
# ==========================================

@app.route("/api/customers", methods=["GET"])
def get_customers():

    customers = CrudNesto.query.all()

    return jsonify([
        customer.to_dict()
        for customer in customers
    ])


# ==========================================
# READ ONE CUSTOMER
# ==========================================

@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )

    if not customer:
        return jsonify({
            "error": "Customer not found"
        }), 404

    return jsonify(customer.to_dict())


# ==========================================
# UPDATE CUSTOMER
# ==========================================

@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )

    if not customer:
        return jsonify({
            "error": "Customer not found"
        }), 404

    data = request.get_json()

    customer.customer_name = data.get(
        "customer_name",
        customer.customer_name
    )

    customer.gender = data.get(
        "gender",
        customer.gender
    )

    if data.get("amount") is not None:
        customer.amount = data["amount"]

    db.session.commit()

    return jsonify(customer.to_dict())


# ==========================================
# DELETE CUSTOMER
# ==========================================

@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )

    if not customer:
        return jsonify({
            "error": "Customer not found"
        }), 404

    db.session.delete(customer)
    db.session.commit()

    return jsonify({
        "message": "Customer deleted successfully"
    })


# ==========================================
# RUN FLASK
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)