import datetime
import os
import re
import sqlite3
import threading
import time
from contextlib import closing

import schedule
from dotenv import load_dotenv
from slack_bolt import App
from includes import utils

from includes import custom_blocks

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
                print(user_id)
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


def is_workspace_admin(user_id):
    try:
        user_info = app.client.users_info(user=user_id)
        is_admin = user_info["user"]["is_admin"]
        is_owner = user_info["user"]["is_owner"]
        is_primary_owner = user_info["user"]["is_primary_owner"]

        # Check if the user is a workspace admin, owner, or primary owner
        return is_admin or is_owner or is_primary_owner
    except Exception as e:
        print(f"Error checking workspace admin status: {e}")
        return False


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


def post_to_general(client, text, blocks=None):
    try:
        if blocks:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text,
                blocks=blocks
            )
            print(result)
        else:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text
            )
            print(result)

    except Exception as e:
        print(f"Error posting message: {e}")


def post_to_channel(client, channel_id, text, blocks=None):
    try:
        if blocks:
            result = client.chat_postMessage(
                channel=channel_id,
                text=text,
                blocks=blocks
            )
            print(result)
        else:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text
            )
            print(result)

    except Exception as e:
        print(f"Error posting message: {e}")


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
    block = custom_blocks.get_app_mention_block()
    say(blocks=block, text="Intro message")


@app.command("/add")
def handle_add_point_command(ack, body, say):
    ack()
    user_id = body["user_id"]
    print(is_workspace_admin(user_id))
    text = body["text"]
    target_user_id, amount = utils.parse_input(text)
    print(target_user_id)
    who = client.users_profile_get(user=target_user_id)
    print(who)
    if target_user_id:
        previous_amount, amount, current_amount = record_debit(target_user_id, int(amount))
        blocks = custom_blocks.add_points_block(previous_amount, amount, current_amount, target_user_id)
        say(text=f"{amount} points have been added to {target_user_id}", blocks=blocks)


@app.command("/delete")
def handle_remove_point_command(ack, body, say):
    ack()
    print(body)
    text = body["text"]
    target_user_id, amount = utils.parse_input(text)
    if target_user_id:
        previous_amount, amount, current_amount = remove_debit(target_user_id, int(amount))
        blocks = custom_blocks.remove_points_block(previous_amount, amount, current_amount, target_user_id)
        say(text=f"{amount} points have been removed from {target_user_id}", blocks=blocks)


def get_permalink(channel, timestamp):
    client = app.client
    response = client.chat_getPermalink(
        channel=channel,
        message_ts=timestamp
    )
    return response["permalink"]


@app.shortcut("add_point")
def handle_add_a_point_shortcut(ack, body):
    ack()

    timestamp = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    trigger_id = body["trigger_id"]
    link = get_permalink(channel_id, timestamp)
    blocks = custom_blocks.points_modal(link, request_type="add_modal_save")
    client.views_open(trigger_id=trigger_id, view=blocks)


@app.shortcut("remove_point")
def handle_remove_point_shortcut(ack, body):
    ack()

    timestamp = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    trigger_id = body["trigger_id"]
    link = get_permalink(channel_id, timestamp)
    blocks = custom_blocks.points_modal(link, request_type="remove_modal_save")
    client.views_open(trigger_id=trigger_id, view=blocks)


@app.view("remove_modal_save")
def handle_remove_submission_events(ack, body, client):
    ack()
    selected_user = body["view"]["state"]["values"]["user"]["multi_users_select-action"]["selected_users"][0]
    userprofile = client.users_info(user=selected_user)
    username = userprofile["user"]["name"]
    points = body["view"]["state"]["values"]["points"]["plain_text_input-action"]["value"]
    timestamp_link = body["view"]["state"]["values"]["timestamp"]["timestamp_input"]["value"]
    previous_amount, amount, current_amount = remove_debit(username, int(points), timestamp_link)
    blocks = custom_blocks.remove_points_block(previous_amount, amount, current_amount, username, link=timestamp_link)
    ts_link = timestamp_link.split('archives/')[1]
    channel_id = ts_link.split('/')[0]
    text = f"{amount} points have been removed from <@{username}>"
    post_to_channel(client, channel_id, text, blocks)


@app.view("add_modal_save")
def handle_add_submission_events(ack, body, say):
    ack()

    selected_user = body["view"]["state"]["values"]["user"]["multi_users_select-action"]["selected_users"][0]
    userprofile = client.users_info(user=selected_user)
    username = userprofile["user"]["name"]
    points = body["view"]["state"]["values"]["points"]["plain_text_input-action"]["value"]
    timestamp_link = body["view"]["state"]["values"]["timestamp"]["timestamp_input"]["value"]
    previous_amount, amount, current_amount = record_debit(username, int(points), timestamp_link)
    blocks = custom_blocks.add_points_block(previous_amount, amount, current_amount, username, link=timestamp_link)
    ts_link = timestamp_link.split('archives/')[1]
    channel_id = ts_link.split('/')[0]
    text = f"{amount} points have been added to <@{username}>"
    post_to_channel(client, channel_id, text, blocks)


@app.shortcut("all_points")
def handle_all_points_shortcut(ack, body):
    ack()

    user_points = get_user_points()
    if user_points:
        print(user_points)
        blocks = custom_blocks.user_points_blocks(user_points)
        post_to_general(client, "Debit Points", blocks)
    else:
        post_to_general(client, "No user points found in the database.")


@app.command("/points")
def handle_points_command(ack, client, body):
    ack()
    print(body)
    text = body["text"]
    if text:
        user_id = text.replace("@", "")
        user_data = get_user_data(user_id)
        user_id = user_data.get("user_id")
        amount = user_data.get("amount")
        link = user_data.get("link")
        response_text = f"<@{user_id}>: {amount} - {link}"
        post_to_general(client, response_text)

    else:
        user_points = get_user_points()
        if user_points:
            print(user_points)
            blocks = custom_blocks.user_points_blocks(user_points)
            post_to_general(client, "Debit Points", blocks)

        else:
            post_to_general(client, "No user points found in the database.")


# SCHEDULING COMMAND

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


def create_reset_mode_table(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS reset_mode (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL
                )""")


@app.command("/set-reset-mode")
def handle_set_reset_mode(ack, body, respond):
    ack()
    mode = body["text"].strip().lower()
    if mode in ["automatic", "manual"]:
        set_reset_mode(mode)
        respond(f"Reset mode set to {mode}.")
    else:
        respond("Invalid mode. Please enter 'automatic' or 'manual'.")


@app.command("/reset")
def handle_reset_command(ack, body):
    ack()
    trigger_id = body["trigger_id"]
    blocks = custom_blocks.reset_db_modal_blocks()
    client = app.client
    client.views_open(trigger_id=trigger_id, view=blocks)


@app.view("reset")
def handle_reset_view(ack, client):
    ack()
    reset_debits_table()
    post_to_general(client, "The database was successfully reset.")


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


def send_weekly_report():
    client = app.client
    user_points = get_user_points()
    if user_points:
        try:
            blocks = custom_blocks.user_points_blocks(user_points)
            post_to_general(client, "Weekly Debit Points Update", blocks)
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


def run_scheduler():
    def send_report_job():
        print("Checking Report Job")
        day_time = get_report_schedule_day()
        if day_time:
            day, time_hour = day_time
            if day == datetime.datetime.today().strftime('%A') and datetime.datetime.now().hour == time_hour:
                send_weekly_report()

    def check_reset_mode():
        reset_mode = get_reset_mode()
        print(reset_mode)
        print(datetime.datetime.now().day == 1)
        if reset_mode == "automatic" and datetime.datetime.now().day == 1:
            reset_debits_table()

    schedule.every().hour.do(send_report_job)
    schedule.every(2).hours.do(check_reset_mode)

    while True:
        schedule.run_pending()
        time.sleep(0.5)


if __name__ == "__main__":
    client = app.client

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    app.start(port=int(os.environ.get("PORT", 3000)))
