import database


def main():
    success, message = database.init_db()
    if success:
        print("SUCCESS: Connected to SQL Server and initialized the Users table.")
    else:
        print(f"FAILED: {message}")


if __name__ == "__main__":
    main()
