import os
import re
import time
import threading
import schedule
from dotenv import load_dotenv
from slack_bolt import App
import datetime
import sqlite3
from contextlib import closing

load_dotenv()

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
            c.execute("SELECT * FROM debits WHERE user_id=?", (user_id,))
            existing_record = c.fetchone()
            if existing_record:

                new_amount = existing_record[1] + amount
                c.execute("UPDATE debits SET amount=? WHERE user_id=?", (new_amount, user_id))
            else:
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
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "For Scheduling",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Use the `/set-report-day` command*. Type `/set-record` command followed by `the day of "
                        "the week` and the `hour` of the day you want to get the reports weekly. For example: `/debit"
                        " friday 18`"
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
        amount = int(match.group(2))
    else:
        user_id = None
        amount = None

    return user_id, amount


# SCHEDULING FUNCTIONS

def create_report_schedule_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS report_schedule (day TEXT, time INTEGER)''')
    conn.commit()


@app.message("hello")
def message_hello(message, say):
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


@app.command("/add")
def handle_add_point_command(ack, body, say):
    ack()
    print(body)
    print(body["timestamp"])
    user_id = body["user_id"]
    text = body["text"]
    target_user_id, amount = parse_input(text)
    if target_user_id:
        # ...
        record_debit(target_user_id, int(amount))
        say(text=f"{amount} points have been added to {target_user_id}")


def get_permalink(channel, timestamp):
    client = app.client
    response = client.chat_getPermalink(
        channel=channel,
        message_ts=timestamp
    )
    return response["permalink"]


@app.shortcut("add_a_point")
def handle_add_a_point_shortcut(ack, body, say):
    ack()
    print(body)
    print(body["message"]["ts"])
    timestamp = body["message"]["ts"]
    channel_id = body["channel"]["id"]

    print(get_permalink(channel_id, timestamp))


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


# SCHEDULING COMMAND
@app.command("/set-report-day")
def handle_set_report_day(ack, body, respond):
    ack()
    text = body["text"].strip().lower()
    try:
        day, time_hour = text.split()
        time_hour = int(time_hour)
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if day in valid_days:
            if 0 <= time_hour < 24:
                set_report_schedule_day(day.capitalize(), time_hour)
                respond(f"Weekly report day set to {day.capitalize()} at {time_hour:02d}:00.")
            else:
                respond("Invalid time. Please enter a valid hour (0-23).")
        else:
            respond("Invalid day. Please enter a valid day of the week.")
    except ValueError:
        respond("Invalid input. Please provide the day and time in the format 'day hour'.")


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


def send_weekly_report(client, channel_id):
    user_points = get_user_points()
    if user_points:
        response_text = "Weekly User Points Report:\n"
        for user_id, total in user_points:
            response_text += f"<@{user_id}>: {total}\n"
        try:
            client.chat_postMessage(channel=channel_id, text=response_text)
        except Exception as e:
            print(f"Error sending weekly report: {e}")
    else:
        print("No user points found in the database")


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


def run_scheduler(scheduler_client, scheduler_channel_id):
    def send_report_job(report_client, report_channel_id):
        day_time = get_report_schedule_day()
        if day_time:
            day, time_hour = day_time
            if day == datetime.datetime.today().strftime('%A') and datetime.datetime.now().hour == time_hour:
                send_weekly_report(report_client, report_channel_id)

    schedule.every().hour.do(send_report_job, scheduler_client, scheduler_channel_id)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    client = app.client

    channel_name = "general"
    response = client.conversations_list()
    for channel in response["channels"]:
        if channel["name"] == channel_name:
            channel_id = channel["id"]
            break

    scheduler_thread = threading.Thread(target=run_scheduler, args=(client, channel_id))
    scheduler_thread.start()
    app.start(port=int(os.environ.get("PORT", 3000)))
