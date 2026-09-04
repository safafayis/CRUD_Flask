from extensions import db


class CrudNesto(db.Model):
    __tablename__ = "crud_nesto"

    customer_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    gender = db.Column(
        db.String(20),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "gender": self.gender,
            "amount": float(self.amount)
        }