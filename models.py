from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    stock_records = db.relationship('Stock', backref='user', lazy=True)
    stock_receipts = db.relationship('StockReceipt', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    pack = db.Column(db.String(50))
    list_price = db.Column(db.Numeric(10, 2))
    pts_price = db.Column(db.Numeric(10, 2))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sales_records = db.relationship('Sale', backref='product_ref', lazy=True)
    stock_receipts = db.relationship('StockReceipt', backref='product_ref', lazy=True)

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    invoice_no = db.Column(db.String(50), nullable=False)
    sale_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    batch_no = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    free_quantity = db.Column(db.Integer, default=0)
    rate = db.Column(db.Numeric(10, 2), nullable=False)
    value = db.Column(db.Numeric(12, 2), nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StockReceipt(db.Model):
    __tablename__ = 'stock_receipts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_no = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    remaining_quantity = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.Date)
    purchase_price = db.Column(db.Numeric(10, 2))
    received_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product = db.relationship("Product", backref="batches")

class Stock(db.Model):
    __tablename__ = 'stock'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # Keeping month/year for Pharma Reports
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    
    opening_stock = db.Column(db.Integer, default=0, nullable=False)
    received_stock = db.Column(db.Integer, default=0, nullable=False)
    sale_return_qty = db.Column(db.Integer, default=0, nullable=False)
    replace_others_in = db.Column(db.Integer, default=0, nullable=False)
    
    # Addition (+)
    total_quantity = db.Column(db.Integer, default=0, nullable=False)
    
    # Subtraction (-)
    sales = db.Column(db.Integer, default=0, nullable=False)
    pr_quantity = db.Column(db.Integer, default=0, nullable=False)
    replace_others_out = db.Column(db.Integer, default=0, nullable=False)
    
    closing_stock = db.Column(db.Integer, default=0, nullable=False)
    last_movement = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product_ref = db.relationship('Product', backref='stock_history', lazy=True)
