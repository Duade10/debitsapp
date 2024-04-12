import os
import re
import datetime
import sqlite3
from contextlib import closing
from dotenv import load_dotenv
from slack_bolt import App
import psycopg2

load_dotenv()
# Initialize the Bolt app with your credentials

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)


def get_db_connection():
    return sqlite3.connect("debits.db", check_same_thread=False)


def create_debits_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS debits
                 (user_id TEXT, amount INTEGER)''')
    conn.commit()


def record_debit(user_id, amount):
    conn = get_db_connection()
    try:
        with closing(conn):
            create_debits_table(conn)
            c = conn.cursor()
            # Check if user_id exists in the database
            c.execute("SELECT * FROM debits WHERE user_id=?", (user_id,))
            existing_record = c.fetchone()
            if existing_record:
                # If user_id exists, update the amount

                new_amount = existing_record[1] + amount
                c.execute("UPDATE debits SET amount=? WHERE user_id=?", (new_amount, user_id))
            else:
                # If user_id doesn't exist, insert a new record
                c.execute("INSERT INTO debits (user_id, amount) VALUES (?, ?)", (user_id, amount))
            conn.commit()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("Database is locked, retrying later...")
        else:
            raise e


def get_app_mention_block():
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hello there! 👋 I'm Debits Bot, here to help you keep track of debit points within your "
                        "team. With me, you can easily assign and record debit points for various reasons."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Use the `/debit` command*. Type `/debit` command followed by `@username` and the amount "
                        "of points. For example: `/debit @john.doe 1`"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*2️⃣ You can use the `/points` * command to view a leaderboard of users and their "
                        "accumulated debit points"
            }
        }
    ]


def get_user_points():
    conn = get_db_connection()
    try:
        with closing(conn):
            c = conn.cursor()
            c.execute("""
                SELECT user_id, SUM(amount) AS total
                FROM debits
                GROUP BY user_id
                ORDER BY total DESC
            """)
            user_points = c.fetchall()
            return user_points
    except sqlite3.Error as e:
        print(f"Error retrieving user points: {e}")
        return []


def parse_input(input_string):
    # User ID and Amount Extraction Regex
    regex_pattern = r'^@(\w+)\s(\d+)'

    # Extract User ID and Amount
    match = re.match(regex_pattern, input_string)
    if match:
        user_id = match.group(1)
        amount = int(match.group(2))  # Convert amount to integer
    else:
        user_id = None
        amount = None

    # Return extracted values
    return user_id, amount


# SCHEDULING
def create_report_schedule(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS report_schedule (day TEXT, time INTEGER)''')
    conn.commit()


@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(f"Hey there <@{message['user']}>!")


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@app.event("app_mention")
def handle_app_mention(ack, body, say):
    ack()
    user = body["event"]["user"]
    block = get_app_mention_block()
    say(blocks=block, text="Intro message")


@app.shortcut("debit_shortcut")
def handle_shortcut(ack, shortcut, client):
    ack()
    user_id = shortcut["user"]["id"]
    # Handle the shortcut and tag the user
    # ...


@app.command("/debit")
def handle_debit_command(ack, body, client, say):
    ack()
    user_id = body["user_id"]
    text = body["text"]
    target_user_id, amount = parse_input(text)
    if target_user_id:
        # ...
        record_debit(target_user_id, int(amount))
        say(text=f"{amount} points have been added to {target_user_id}")


@app.command("/points")
def handle_points_command(ack, respond):
    ack()
    user_points = get_user_points()
    if user_points:
        response_text = "User Points:\n"
        for user_id, total in user_points:
            response_text += f"<@{user_id}>: {total}\n"
        respond(response_text)
    else:
        respond("No user points found in the database.")


# def get_db_connection():
#     print('db')
#     try:
#         conn = psycopg2.connect(
#             user="postgres",
#             password="12345",
#             host="127.0.0.1",
#             port="5432",
#             database="debits",
#         )
#         return conn
#     except (Exception, psycopg2.Error) as error:
#         print("Error connecting to PostgreSQL database:", error)
#
#
# def record_debit(user_id, amount, reason):
#     print('debit')
#     conn = get_db_connection()
#     try:
#         with conn:
#             with conn.cursor() as cur:
#                 cur.execute("INSERT INTO debits (user_id, amount, reason) VALUES (%s, %s, %s)",
#                             (user_id, amount, reason))
#     except (Exception, psycopg2.Error) as error:
#         print("Error recording debit:", error)
#     finally:
#         if conn:
#             conn.close()


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
