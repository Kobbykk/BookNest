from app import app, db
from sqlalchemy import text
from models import User

def migrate_roles():
    print("Starting role migration...")
    with app.app_context():
        try:
            # Add role column if it doesn't exist
            db.session.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='users' AND column_name='role'
                    ) THEN
                        ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'customer';
                    END IF;
                END $$;
            """))
            db.session.commit()
            print("Role column added successfully")
            
            # Update existing admin users
            db.session.execute(text("""
                UPDATE users SET role = 'admin' WHERE is_admin = true;
            """))
            db.session.commit()
            print("Admin roles updated successfully")
            
            print("Role migration completed successfully")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    migrate_roles()
