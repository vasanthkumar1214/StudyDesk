import pyodbc


SERVER = r"localhost"
DATABASE = "StudyDesk"
CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
)


def get_connection():
    return pyodbc.connect(CONNECTION_STRING)


def init_db():
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.tables
                WHERE name = 'Users'
            )
            BEGIN
                CREATE TABLE Users (
                    UserID INT IDENTITY(1,1) PRIMARY KEY,
                    Name VARCHAR(100) NOT NULL,
                    Age INT NOT NULL,
                    Email VARCHAR(100) NOT NULL,
                    CreatedAt DATETIME DEFAULT GETDATE()
                )
            END
            """
        )
        connection.commit()
        return True, "Database initialized successfully."
    except Exception as error:
        if connection:
            connection.rollback()
        return False, f"Database initialization failed: {error}"
    finally:
        if connection:
            connection.close()


def insert_user(name, age, email):
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO Users (Name, Age, Email) VALUES (?, ?, ?)",
            name,
            int(age),
            email,
        )
        connection.commit()
        return True, "User added successfully."
    except Exception as error:
        if connection:
            connection.rollback()
        return False, f"Add user failed: {error}"
    finally:
        if connection:
            connection.close()


def get_all_users():
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT UserID, Name, Age, Email, CreatedAt
            FROM Users
            ORDER BY UserID
            """
        )
        users = cursor.fetchall()
        connection.commit()
        return True, users
    except Exception as error:
        if connection:
            connection.rollback()
        return False, f"Get users failed: {error}"
    finally:
        if connection:
            connection.close()


def update_email(name, new_email):
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE Users SET Email = ? WHERE Name = ?",
            new_email,
            name,
        )
        connection.commit()
        if cursor.rowcount == 0:
            return False, "No user found with that name."
        return True, "Email updated successfully."
    except Exception as error:
        if connection:
            connection.rollback()
        return False, f"Update email failed: {error}"
    finally:
        if connection:
            connection.close()


def delete_user(name):
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM Users WHERE Name = ?", name)
        connection.commit()
        if cursor.rowcount == 0:
            return False, "No user found with that name."
        return True, "User deleted successfully."
    except Exception as error:
        if connection:
            connection.rollback()
        return False, f"Delete user failed: {error}"
    finally:
        if connection:
            connection.close()
