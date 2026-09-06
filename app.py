from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    session
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from extensions import db
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SECRET_KEY
)

from models import (
    User,
    CrudNesto,
    PasswordResetToken
)

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import secrets
import hashlib
import re


app = Flask(__name__)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
    SQLALCHEMY_TRACK_MODIFICATIONS
)
app.config["SECRET_KEY"] = SECRET_KEY

db.init_app(app)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# VALIDATION FUNCTIONS
# --------------------------------------------------

def validate_customer_name(name):
    if not name:
        return False

    name = name.strip()

    if len(name) < 1 or len(name) > 100:
        return False

    pattern = r"^[A-Za-z]+(?:[ .'-]+[A-Za-z]+)*\.?$"

    return bool(re.fullmatch(pattern, name))


def validate_gender(gender):
    return gender in ["Male", "Female", "Other"]


def validate_amount(amount):
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return False

    if value <= 0:
        return False

    if value > Decimal("99999999.99"):
        return False

    if value.as_tuple().exponent < -2:
        return False

    return True


def validate_password(password):
    if not password:
        return False

    return len(password) >= 8


def hash_reset_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("customers"))

    return redirect(url_for("login"))


# --------------------------------------------------
# REGISTER PAGE
# --------------------------------------------------

@app.route("/register")
def register():

    if "user_id" in session:
        return redirect(url_for("customers"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------

@app.route("/login")
def login():

    if "user_id" in session:
        return redirect(url_for("customers"))

    return render_template("login.html")


# --------------------------------------------------
# REGISTER API
# --------------------------------------------------

@app.route("/api/register", methods=["POST"])
def register_user():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request."
        }), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    # Email validation
    if not email:
        return jsonify({
            "error": "Please enter your email address."
        }), 400

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.fullmatch(email_pattern, email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    # Password validation
    if not validate_password(password):
        return jsonify({
            "error": "Password must contain at least 8 characters."
        }), 400

    # Confirm password
    if password != confirm_password:
        return jsonify({
            "error": "Passwords do not match."
        }), 400

    # Check existing user
    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return jsonify({
            "error": "An account with this email already exists."
        }), 400

    # Create user
    hashed_password = generate_password_hash(password)

    new_user = User(
        email=email,
        password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "message": "Account created successfully."
    }), 201


# --------------------------------------------------
# LOGIN API
# --------------------------------------------------

@app.route("/api/login", methods=["POST"])
def login_user():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request."
        }), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email:
        return jsonify({
            "error": "Please enter your email address."
        }), 400

    if not password:
        return jsonify({
            "error": "Please enter your password."
        }), 400

    user = User.query.filter_by(
        email=email
    ).first()

    if not user:
        return jsonify({
            "error": "Invalid email or password."
        }), 401

    if not check_password_hash(
        user.password,
        password
    ):
        return jsonify({
            "error": "Invalid email or password."
        }), 401

    session.clear()

    session["user_id"] = user.user_id
    session["email"] = user.email

    return jsonify({
        "message": "Login successful."
    })


# --------------------------------------------------
# FORGOT PASSWORD API
# --------------------------------------------------

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request."
        }), 400

    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({
            "error": "Please enter your email address."
        }), 400

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.fullmatch(email_pattern, email):
        return jsonify({
            "error": "Please enter a valid email address."
        }), 400

    user = User.query.filter_by(
        email=email
    ).first()

    # Generic response if account doesn't exist
    if not user:
        return jsonify({
            "message": (
                "If an account exists with this email, "
                "a password reset option will be available."
            )
        })

    # Remove old reset tokens
    PasswordResetToken.query.filter_by(
        user_id=user.user_id
    ).delete()

    # Generate secure token
    token = secrets.token_urlsafe(32)

    token_hash = hash_reset_token(token)

    expires_at = datetime.utcnow() + timedelta(
        minutes=15
    )

    reset_record = PasswordResetToken(
        user_id=user.user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False
    )

    db.session.add(reset_record)
    db.session.commit()

    # Local development reset URL
    reset_url = url_for(
        "reset_password",
        token=token,
        _external=True
    )

    return jsonify({
        "message": (
            "A password reset link has been created."
        ),
        "reset_url": reset_url
    })


# --------------------------------------------------
# RESET PASSWORD PAGE
# --------------------------------------------------

@app.route("/reset-password/<token>")
def reset_password(token):

    return render_template(
        "login.html",
        reset_token=token,
        show_reset=True
    )


# --------------------------------------------------
# RESET PASSWORD API
# --------------------------------------------------

@app.route("/api/reset-password", methods=["POST"])
def reset_password_api():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request."
        }), 400

    token = data.get("token", "")

    password = data.get(
        "password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    if not token:
        return jsonify({
            "error": "Invalid or expired reset link."
        }), 400

    token_hash = hash_reset_token(token)

    reset_record = PasswordResetToken.query.filter_by(
        token_hash=token_hash
    ).first()

    if not reset_record:
        return jsonify({
            "error": "Invalid or expired reset link."
        }), 400

    if reset_record.used:
        return jsonify({
            "error": "This reset link has already been used."
        }), 400

    if reset_record.expires_at < datetime.utcnow():

        db.session.delete(reset_record)
        db.session.commit()

        return jsonify({
            "error": "This reset link has expired."
        }), 400

    if not validate_password(password):
        return jsonify({
            "error": (
                "Password must contain at least 8 characters."
            )
        }), 400

    if password != confirm_password:
        return jsonify({
            "error": "Passwords do not match."
        }), 400

    user = User.query.get(
        reset_record.user_id
    )

    if not user:
        return jsonify({
            "error": "Unable to reset password."
        }), 400

    # Update password
    user.password = generate_password_hash(
        password
    )

    # Mark token as used
    reset_record.used = True

    db.session.commit()

    return jsonify({
        "message": (
            "Password updated successfully. "
            "You can now log in."
        )
    })


# --------------------------------------------------
# LOGOUT API
# --------------------------------------------------

@app.route("/api/logout", methods=["POST"])
def logout_user():

    session.clear()

    return jsonify({
        "message": "Logged out successfully."
    })


# --------------------------------------------------
# CUSTOMER PAGE
# --------------------------------------------------

@app.route("/customers")
def customers():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        email=session.get("email")
    )


# --------------------------------------------------
# GET ALL CUSTOMERS
# --------------------------------------------------

@app.route("/api/customers", methods=["GET"])
def get_customers():

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized."
        }), 401

    customers = CrudNesto.query.all()

    return jsonify([
        customer.to_dict()
        for customer in customers
    ])


# --------------------------------------------------
# GET ONE CUSTOMER
# --------------------------------------------------

@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized."
        }), 401

    customer = CrudNesto.query.get(
        customer_id
    )

    if not customer:
        return jsonify({
            "error": "Customer not found."
        }), 404

    return jsonify(
        customer.to_dict()
    )


# --------------------------------------------------
# CREATE CUSTOMER
# --------------------------------------------------

@app.route("/api/customers", methods=["POST"])
def create_customer():

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized."
        }), 401

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request."
        }), 400

    customer_name = data.get(
        "customer_name",
        ""
    ).strip()

    gender = data.get(
        "gender",
        ""
    ).strip()

    amount = data.get(
        "amount",
        ""
    )

    # Name validation
    if not validate_customer_name(
        customer_name
    ):
        return jsonify({
            "error": (
                "Please enter a valid customer name."
            )
        }), 400

    # Gender validation
    if not validate_gender(gender):
        return jsonify({
            "error": "Please select a valid gender."
        }), 400

    # Amount validation
    if not validate_amount(amount):
        return jsonify({
            "error": (
                "Please enter a valid positive "
                "amount with up to 2 decimal places."
            )
        }), 400

    new_customer = CrudNesto(
        customer_name=customer_name,
        gender=gender,
        amount=Decimal(str(amount))
    )

    db.session.add(new_customer)
    db.session.commit()

    return jsonify({
        "message": "Customer added successfully.",
        "customer": new_customer.to_dict()
    }), 201


# --------------------------------------------------
# UPDATE CUSTOMER
# --------------------------------------------------

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["PUT"]
)
def update_customer(customer_id):

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized."
        }), 401

    customer = CrudNesto.query.get(
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
        "customer_name",
        ""
    ).strip()

    gender = data.get(
        "gender",
        ""
    ).strip()

    amount = data.get(
        "amount",
        ""
    )

    if not validate_customer_name(
        customer_name
    ):
        return jsonify({
            "error": (
                "Please enter a valid customer name."
            )
        }), 400

    if not validate_gender(gender):
        return jsonify({
            "error": "Please select a valid gender."
        }), 400

    if not validate_amount(amount):
        return jsonify({
            "error": (
                "Please enter a valid positive "
                "amount with up to 2 decimal places."
            )
        }), 400

    customer.customer_name = customer_name
    customer.gender = gender
    customer.amount = Decimal(
        str(amount)
    )

    db.session.commit()

    return jsonify({
        "message": "Customer updated successfully.",
        "customer": customer.to_dict()
    })


# --------------------------------------------------
# DELETE CUSTOMER
# --------------------------------------------------

@app.route(
    "/api/customers/<int:customer_id>",
    methods=["DELETE"]
)
def delete_customer(customer_id):

    if "user_id" not in session:
        return jsonify({
            "error": "Unauthorized."
        }), 401

    customer = CrudNesto.query.get(
        customer_id
    )

    if not customer:
        return jsonify({
            "error": "Customer not found."
        }), 404

    db.session.delete(customer)
    db.session.commit()

    return jsonify({
        "message": "Customer deleted successfully."
    })


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True
    )