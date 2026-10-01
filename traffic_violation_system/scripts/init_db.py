from app.database.init_db import initialize_application_database


def main() -> None:
    initialize_application_database()
    print("Database initialized.")


if __name__ == "__main__":
    main()
