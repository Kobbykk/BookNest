from app import app, db
from seed_books import seed_books
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
            
            # Drop schema and recreate with proper owner
            db.session.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.execute(text(f'ALTER SCHEMA public OWNER TO {os.environ["PGUSER"]}'))
            db.session.execute(text('GRANT ALL ON SCHEMA public TO PUBLIC'))
            db.session.commit()
            
            # Recreate all tables
            db.create_all()
            print("Tables recreated")
            
            # Seed sample data
            try:
                seed_books()
                print("Database seeded successfully")
            except Exception as e:
                print(f"Error seeding database: {str(e)}")
                db.session.rollback()
                
            print("Database reset complete")
            
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    import os
    reset_database()
