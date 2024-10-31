from app import db
from flask_migrate import Migrate

def upgrade():
    # Add payment-related columns to order table
    with db.engine.connect() as conn:
        conn.execute("""
            ALTER TABLE "order" 
            ADD COLUMN IF NOT EXISTS payment_intent_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS payment_date TIMESTAMP,
            ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100),
            ADD COLUMN IF NOT EXISTS carrier VARCHAR(100),
            ADD COLUMN IF NOT EXISTS shipping_date TIMESTAMP;
        """)

def downgrade():
    # Remove payment-related columns from order table
    with db.engine.connect() as conn:
        conn.execute("""
            ALTER TABLE "order" 
            DROP COLUMN IF EXISTS payment_intent_id,
            DROP COLUMN IF EXISTS payment_status,
            DROP COLUMN IF EXISTS payment_date,
            DROP COLUMN IF EXISTS tracking_number,
            DROP COLUMN IF EXISTS carrier,
            DROP COLUMN IF EXISTS shipping_date;
        """) 