# StudyDesk

StudyDesk is a simple Python project with a threaded socket chat server, a Tkinter chat client, and Microsoft SQL Server CRUD operations using Windows Authentication.

## Files

- `server.py` - Multi-client chat server on port `8080`. Client nicknames are authenticated against the SQL Server `Users` table.
- `client_gui.py` - Tkinter GUI client with Chat and Database tabs.
- `database.py` - SQL Server database helper functions using `pyodbc`.
- `db_setup.sql` - SQL Server setup script for SSMS.
- `requirements.txt` - Python dependency list.

## Requirements

- Python 3
- Microsoft SQL Server
- SQL Server Management Studio
- ODBC Driver 17 for SQL Server

## Setup and Run

1. Open SQL Server Management Studio.

2. Open `db_setup.sql` and run the script. It creates the `Studydesk` database and the `Users` table.

3. Install the Python dependency:

   ```bash
   pip install pyodbc
   ```

   You can also install from the requirements file:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the chat server:

   ```bash
   python server.py
   ```

   Keep this terminal open. The server listens on port `8080`.

5. Start the GUI client:

   ```bash
   python client_gui.py
   ```

6. Add at least one user in the Database tab. The chat nickname must exactly match a name stored in the `Users` table.

7. In the Chat tab, enter the server IP address and your nickname, then click **Connect**.

   - If the client is running on the same computer as the server, use `127.0.0.1`.
   - If the client is running on another machine, use the server machine's IP address.

8. Run `client_gui.py` on each machine that should join the chat.

## Database Tab

Use the Database tab to manage users:

- **Add User** inserts a user with Name, Age, and Email.
- **Search** loads all users, or filters by the Name field when it is filled in.
- **Update Email** updates the email address for the user matching the Name field.
- **Delete** deletes the user matching the Name field.

## Notes

- The database connection uses Windows Authentication with `Trusted_Connection=yes`.
- The SQL Server name in `database.py` is set to `VASANTH\SQLEXPRESS`, and the database name is set to `Studydesk`.
- If clients on other machines cannot connect, allow port `8080` through the server machine's firewall.
