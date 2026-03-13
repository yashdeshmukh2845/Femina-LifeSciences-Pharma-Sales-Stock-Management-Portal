from app import app
from models import db, User, Product, Sale, Stock, StockReceipt

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Database reset successfully!")

if __name__ == "__main__":
    # The database reset logic has been moved out of the function
    # to ensure models are imported and tables are created directly.
    pass
