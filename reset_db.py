from app import app, db
from sqlalchemy import text

def reset_database():
    print("Resetting database...")
    with app.app_context():
        try:
            # Drop existing connections
            db.session.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = current_database()
                AND pid <> pg_backend_pid();
            """))
            db.session.commit()
            
            # Drop all tables
            db.drop_all()
            print("All tables dropped")
            
            # Create all tables
            db.create_all()
            print("All tables recreated")
            
            # Create admin user
            from models import User
            from werkzeug.security import generate_password_hash
            
            admin = User(
                username='admin',
                email='admin@gmail.com',
                password_hash=generate_password_hash('Password123'),
                is_admin=True,
                role='admin'
            )
            
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
            
            print("Database reset complete")
            
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    reset_database()
