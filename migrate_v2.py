import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(db_url)

commands = [
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS list_price NUMERIC(10,2);",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS pts_price NUMERIC(10,2);",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS expiry_date DATE;",
    "ALTER TABLE stock_receipts ADD COLUMN IF NOT EXISTS remaining_quantity INTEGER;",
    "ALTER TABLE stock_receipts ADD COLUMN IF NOT EXISTS expiry_date DATE;",
    "ALTER TABLE stock_receipts ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(10,2);",
    # Initialize remaining_quantity for existing records
    "UPDATE stock_receipts SET remaining_quantity = quantity WHERE remaining_quantity IS NULL;"
]

with engine.connect() as conn:
    for cmd in commands:
        try:
            conn.execute(text(cmd))
            conn.commit()
            print(f"Executed: {cmd}")
        except Exception as e:
            print(f"Error executing {cmd}: {e}")
