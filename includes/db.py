import sqlite3
from contextlib import closing


def get_db_connection():
    return sqlite3.connect("debits.db", check_same_thread=False)


def create_report_schedule_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS report_schedule (day TEXT, time INTEGER)''')
    conn.commit()


def create_reset_mode_table(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS reset_mode (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL
                )""")


def create_debits_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS debits
                 (user_id TEXT, amount INTEGER, link TEXT)''')
    conn.commit()


def record_debit(user_id, amount, link=None):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_debits_table(conn)
            c = conn.cursor()
            c.execute("SELECT * FROM debits WHERE user_id=?", (user_id,))
            existing_record = c.fetchone()
            if existing_record:
                previous_amount = existing_record[1]
                new_amount = previous_amount + amount
                if link:
                    c.execute("UPDATE debits SET amount=?, link=? WHERE user_id=?", (new_amount, link, user_id))
                else:
                    c.execute("UPDATE debits SET amount=? WHERE user_id=?", (new_amount, user_id))
                current_amount = new_amount
            else:
                previous_amount = 0
                current_amount = amount
                if link:
                    c.execute("INSERT INTO debits (user_id, amount, link) VALUES (?, ?, ?)", (user_id, amount, link))
                else:
                    c.execute("INSERT INTO debits (user_id, amount) VALUES (?, ?)", (user_id, amount))
            conn.commit()
            return previous_amount, amount, current_amount
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database is locked, retrying later...")
        else:
            raise e


def remove_debit(user_id, amount, link=None):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_debits_table(conn)
            c = conn.cursor()
            c.execute("SELECT * FROM debits WHERE user_id=?", (user_id,))
            existing_record = c.fetchone()
            if existing_record:
                previous_amount = existing_record[1]
                new_amount = previous_amount - amount
                if new_amount > 0:
                    if link:
                        c.execute("UPDATE debits SET amount=?, link=? WHERE user_id=?", (new_amount, link, user_id))
                    else:
                        c.execute("UPDATE debits SET amount=? WHERE user_id=?", (new_amount, user_id))
                    current_amount = new_amount
                else:
                    c.execute("DELETE FROM debits WHERE user_id=?", (user_id,))
                    current_amount = 0
                conn.commit()
                return previous_amount, amount, current_amount
            else:
                return None, None, None
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database is locked, retrying later...")
        else:
            raise e


def reset_debits_table():
    conn = get_db_connection()
    try:
        with closing(conn):
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS debits")
            c.execute("""CREATE TABLE debits (
                          user_id TEXT PRIMARY KEY,
                          amount INTEGER,
                          link TEXT
                      )""")
            conn.commit()
            print("Debits table reset successfully.")
    except sqlite3.Error as e:
        print(f"Error resetting debits table: {e}")


def get_user_data(user_id):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_debits_table(conn)
            c = conn.cursor()
            c.execute("SELECT * FROM debits WHERE user_id=?", (user_id,))
            user_data = c.fetchone()
            if user_data:
                return {
                    "user_id": user_data[0],
                    "amount": user_data[1],
                    "link": user_data[2]
                }
            else:
                return None
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database is locked, retrying later...")
        else:
            raise e


def get_user_points():
    conn = get_db_connection()
    try:
        with closing(conn):
            c = conn.cursor()
            c.execute("""
                SELECT user_id, SUM(amount) AS total_points, MAX(link) AS link
                FROM debits
                GROUP BY user_id
                ORDER BY total_points DESC
            """)
            user_points = c.fetchall()
            return user_points
    except sqlite3.Error as e:
        print(f"Error retrieving user points: {e}")
        return []


def set_reset_mode(mode):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_reset_mode_table(conn)
            c = conn.cursor()
            c.execute("DELETE FROM reset_mode")  # Clear existing mode
            c.execute("INSERT INTO reset_mode (mode) VALUES (?)", (mode,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error setting reset mode: {e}")


def set_report_schedule_day(day, time_hour):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_report_schedule_table(conn)
            c = conn.cursor()
            c.execute("DELETE FROM report_schedule")  # Clear existing day
            c.execute("INSERT INTO report_schedule (day, time) VALUES (?, ?)", (day, time_hour))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error setting report schedule day: {e}")


def get_report_schedule_day():
    conn = get_db_connection()
    try:
        with closing(conn):
            c = conn.cursor()
            c.execute("SELECT day, time FROM report_schedule")
            day_time = c.fetchone()
            if day_time:
                return day_time
            else:
                return None
    except sqlite3.Error as e:
        print(f"Error retrieving report schedule day: {e}")
        return None


def get_reset_mode():
    conn = get_db_connection()
    try:
        with closing(conn):
            c = conn.cursor()
            c.execute("SELECT mode FROM reset_mode")
            mode = c.fetchone()
            if mode:
                return mode[0]
            else:
                return None
    except sqlite3.Error as e:
        print(f"Error retrieving reset mode: {e}")
        return None
