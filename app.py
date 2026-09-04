import re
from decimal import Decimal, InvalidOperation

from flask import Flask, request, jsonify, render_template
from extensions import db

from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY
)


# ==========================================
# FLASK APPLICATION
# ==========================================

app = Flask(__name__)


# ==========================================
# FLASK CONFIGURATION
# ==========================================

app.config["SQLALCHEMY_DATABASE_URI"] = (
    SQLALCHEMY_DATABASE_URI
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
    SQLALCHEMY_TRACK_MODIFICATIONS
)

app.config["SECRET_KEY"] = SECRET_KEY


# ==========================================
# DATABASE
# ==========================================


db.init_app(app)


# Import model AFTER db is created
from models import CrudNesto


# ==========================================
# CREATE TABLE
# ==========================================

with app.app_context():

    db.create_all()


# ==========================================
# CUSTOMER NAME VALIDATION
# ==========================================

def validate_customer_name(name):

    if not name:

        return "Customer name is required."


    name = name.strip()


    if not name:

        return "Customer name is required."


    if len(name) > 100:

        return (
            "Customer name must be "
            "100 characters or less."
        )


    # Allows:
    #
    # John
    # John Smith
    # A.P.
    # A. P.
    # Safa A.P.
    # Safa A. P.
    # Anne-Marie
    # O'Connor
    #
    # Rejects:
    #
    # 12345
    # John123
    # @John
    # John@Smith

    pattern = (
        r"^[A-Za-z]+(?:[ .'-]+[A-Za-z]+)*\.?$"
    )


    if not re.fullmatch(pattern, name):

        return (
            "Name can contain only letters, "
            "spaces, periods, hyphens and "
            "apostrophes."
        )


    return None


# ==========================================
# GENDER VALIDATION
# ==========================================

def validate_gender(gender):

    allowed_genders = {
        "Male",
        "Female",
        "Other"
    }


    if gender not in allowed_genders:

        return "Please select a valid gender."


    return None


# ==========================================
# AMOUNT VALIDATION
# ==========================================

def validate_amount(amount):

    if amount is None:

        return "Amount is required."


    amount = str(amount).strip()


    if not amount:

        return "Amount is required."


    try:

        decimal_amount = Decimal(amount)

    except InvalidOperation:

        return "Amount must be a valid number."


    if decimal_amount <= 0:

        return "Amount must be greater than 0."


    if decimal_amount.as_tuple().exponent < -2:

        return (
            "Amount can have a maximum "
            "of 2 decimal places."
        )


    if decimal_amount > Decimal("99999999.99"):

        return "Amount is too large."


    return None


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


    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    customer_name = data.get(
        "customer_name"
    )

    gender = data.get(
        "gender"
    )

    amount = data.get(
        "amount"
    )


    # Validate name

    error = validate_customer_name(
        customer_name
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    # Validate gender

    error = validate_gender(
        gender
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    # Validate amount

    error = validate_amount(
        amount
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    try:

        customer = CrudNesto(

            customer_name=
                customer_name.strip(),

            gender=
                gender,

            amount=
                Decimal(str(amount))
        )


        db.session.add(customer)

        db.session.commit()


        return jsonify(
            customer.to_dict()
        ), 201


    except Exception:

        db.session.rollback()


        return jsonify({
            "error": "Unable to save customer."
        }), 500


# ==========================================
# READ ALL CUSTOMERS
# ==========================================

@app.route("/api/customers", methods=["GET"])
def get_customers():

    customers = CrudNesto.query.order_by(
        CrudNesto.customer_id.asc()
    ).all()


    return jsonify([

        customer.to_dict()

        for customer in customers

    ])


# ==========================================
# READ ONE CUSTOMER
# ==========================================

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["GET"]
)
def get_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )


    if not customer:

        return jsonify({
            "error": "Customer not found."
        }), 404


    return jsonify(
        customer.to_dict()
    )


# ==========================================
# UPDATE CUSTOMER
# ==========================================

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["PUT"]
)
def update_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )


    if not customer:

        return jsonify({
            "error": "Customer not found."
        }), 404


    data = request.get_json()


    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    customer_name = data.get(
        "customer_name"
    )

    gender = data.get(
        "gender"
    )

    amount = data.get(
        "amount"
    )


    # Validate name

    error = validate_customer_name(
        customer_name
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    # Validate gender

    error = validate_gender(
        gender
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    # Validate amount

    error = validate_amount(
        amount
    )

    if error:

        return jsonify({
            "error": error
        }), 400


    try:

        customer.customer_name = (
            customer_name.strip()
        )

        customer.gender = gender

        customer.amount = Decimal(
            str(amount)
        )


        db.session.commit()


        return jsonify(
            customer.to_dict()
        )


    except Exception:

        db.session.rollback()


        return jsonify({
            "error": "Unable to update customer."
        }), 500


# ==========================================
# DELETE CUSTOMER
# ==========================================

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["DELETE"]
)
def delete_customer(customer_id):

    customer = db.session.get(
        CrudNesto,
        customer_id
    )


    if not customer:

        return jsonify({
            "error": "Customer not found."
        }), 404


    try:

        db.session.delete(customer)

        db.session.commit()


        return jsonify({
            "message":
                "Customer deleted successfully."
        })


    except Exception:

        db.session.rollback()


        return jsonify({
            "error":
                "Unable to delete customer."
        }), 500


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)