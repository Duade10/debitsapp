import datetime
import sqlite3
from contextlib import closing
from main import get_db_connection, get_user_points, set_report_schedule_day


def create_report_schedule_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS report_schedule (day TEXT, time INTEGER)''')
    conn.commit()


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


def send_report_job(report_client, report_channel_id):
    day_time = get_report_schedule_day()
    if day_time:
        day, time_hour = day_time
        if day == datetime.datetime.today().strftime('%A') and datetime.datetime.now().hour == time_hour:
            send_weekly_report(report_client, report_channel_id)
