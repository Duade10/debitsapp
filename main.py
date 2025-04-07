import datetime
import os
import threading
import time
import logging

import schedule
from dotenv import load_dotenv
from slack_bolt import App

from includes import custom_blocks, utils, db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

last_reset_dates = {}

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)



def post_to_general(client, text, blocks=None):
    try:
        if blocks:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text,
                blocks=blocks
            )
        else:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text
            )

    except Exception as e:
        logging.error(f"Error posting message: {e}")


def post_to_channel(client, channel_id, text, blocks=None):
    try:
        if blocks:
            result = client.chat_postMessage(
                channel=channel_id,
                text=text,
                blocks=blocks
            )
        else:
            result = client.chat_postMessage(
                channel="debits-general",
                text=text
            )

    except Exception as e:
        logging.error(f"Error posting message: {e}")


# SCHEDULING FUNCTIONS

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

    text = body["text"]
    target_user_id, amount = utils.parse_input(text)
    workspace_id = utils.get_workspace(body)
    if target_user_id:
        previous_amount, amount, current_amount = db.record_debit(target_user_id, workspace_id, int(amount))
        blocks = custom_blocks.add_points_block(previous_amount, amount, current_amount, target_user_id)
        say(text=f"{amount} points have been added to {target_user_id}", blocks=blocks)


@app.command("/delete")
def handle_remove_point_command(ack, body, say):
    ack()

    text = body["text"]
    target_user_id, amount = utils.parse_input(text)
    workspace_id = utils.get_workspace(body)
    if target_user_id:
        previous_amount, amount, current_amount = db.remove_debit(target_user_id, workspace_id, int(amount))
        blocks = custom_blocks.remove_points_block(previous_amount, amount, current_amount, target_user_id)
        say(text=f"{amount} points have been removed from {target_user_id}", blocks=blocks)


@app.command("/points")
def handle_points_command(ack, client, body):
    ack()

    text = body["text"]
    if text:
        workspace_id = utils.get_workspace(body)
        user_id = text.replace("@", "")
        user, amount = db.get_single_user(user_id, workspace_id)
        response_text = f"<@{user}>: {int(amount)}"
        post_to_general(client, response_text)

    else:
        workspace_id = utils.get_workspace(body)
        user_points = db.get_all_points(workspace_id)
        if user_points:
            blocks = custom_blocks.user_points_blocks(user_points)
            post_to_general(client, "Debit Points", blocks)

        else:
            post_to_general(client, "No user points found in the database.")


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
    post_to_general(client, "Add points", blocks)
    # client.views_open(trigger_id=trigger_id, view=blocks)


@app.shortcut("remove_point")
def handle_remove_point_shortcut(ack, body):
    ack()

    timestamp = body["message"]["ts"]
    channel_id = body["channel"]["id"]
    trigger_id = body["trigger_id"]
    link = get_permalink(channel_id, timestamp)
    blocks = custom_blocks.points_modal(link, request_type="remove_modal_save")
    post_to_general(client, "Remove points", blocks)
    # client.views_open(trigger_id=trigger_id, view=blocks)


@app.view("remove_modal_save")
def handle_remove_submission_events(ack, body, client):
    ack()

    workspace_id = utils.get_workspace(body)
    selected_user = body["view"]["state"]["values"]["user"]["multi_users_select-action"]["selected_users"][0]
    userprofile = client.users_info(user=selected_user)
    username = userprofile["user"]["name"]
    points = body["view"]["state"]["values"]["points"]["plain_text_input-action"]["value"]
    timestamp_link = body["view"]["state"]["values"]["timestamp"]["timestamp_input"]["value"]
    previous_amount, amount, current_amount = db.remove_debit(username, workspace_id, int(points), timestamp_link)
    blocks = custom_blocks.remove_points_block(previous_amount, amount, current_amount, username, link=timestamp_link)
    ts_link = timestamp_link.split('archives/')[1]
    channel_id = ts_link.split('/')[0]
    text = f"{amount} points have been removed from <@{username}>"
    post_to_general(client, text, blocks)
    # post_to_channel(client, channel_id, text, blocks)


@app.view("add_modal_save")
def handle_add_submission_events(ack, body, say):
    ack()

    workspace_id = utils.get_workspace(body)
    selected_user = body["view"]["state"]["values"]["user"]["multi_users_select-action"]["selected_users"][0]
    userprofile = client.users_info(user=selected_user)
    username = userprofile["user"]["name"]
    points = body["view"]["state"]["values"]["points"]["plain_text_input-action"]["value"]
    timestamp_link = body["view"]["state"]["values"]["timestamp"]["timestamp_input"]["value"]
    previous_amount, amount, current_amount = db.record_debit(username, workspace_id, int(points), timestamp_link)
    blocks = custom_blocks.add_points_block(previous_amount, amount, current_amount, username, link=timestamp_link)
    ts_link = timestamp_link.split('archives/')[1]
    channel_id = ts_link.split('/')[0]
    text = f"{amount} points have been added to <@{username}>"
    post_to_general(client, text, blocks)
    # post_to_channel(client, channel_id, text, blocks)


@app.shortcut("all_points")
def handle_all_points_shortcut(ack, body):
    ack()

    workspace_id = utils.get_workspace(body)
    user_points = db.get_all_points(workspace_id)
    if user_points:
        blocks = custom_blocks.user_points_blocks(user_points)
        post_to_general(client, "Debit Points", blocks)
    else:
        post_to_general(client, "No user points found in the database.")


# SCHEDULING COMMAND


@app.command("/set-reset-mode")
def handle_set_reset_mode(ack, body, respond):
    ack()
    workspace_id = utils.get_workspace(body)
    mode = body["text"].strip().lower()
    if mode in ["automatic", "manual"]:
        db.set_reset_mode(workspace_id, mode)
        respond(f"Reset mode set to {mode}.")
    else:
        respond("Invalid mode. Please enter 'automatic' or 'manual'.")


@app.command("/reset")
def handle_reset_command(ack, body, respond):
    ack()
    user_id = utils.get_user_id(body, "body")
    if utils.is_workspace_admin(user_id):
        trigger_id = body["trigger_id"]
        blocks = custom_blocks.reset_db_modal_blocks()
        client = app.client
        client.views_open(trigger_id=trigger_id, view=blocks)
    else:
        respond("Command reserved for admin")


@app.view("reset")
def handle_reset_view(ack, body, client):
    ack()
    workspace_id = utils.get_workspace(body)
    db.reset_debits_table(workspace_id)
    post_to_general(client, "The database was successfully reset.")


@app.command("/set-report-day")
def handle_set_report_day(ack, body, respond):
    ack()
    workspace_id = utils.get_workspace(body)
    text = body["text"].strip().lower()

    try:
        day, time_hour = text.split()
        time_hour = int(time_hour)
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        if day in valid_days:
            if 0 <= time_hour < 24:
                db.set_report_daytime(workspace_id, day, time_hour)
                respond(f"Weekly report day set to {day.capitalize()} at {time_hour:02d}:00.")
            else:
                respond("Invalid time. Please enter a valid hour (0-23).")
        else:
            respond("Invalid day. Please enter a valid day of the week.")
    except ValueError:
        respond("Invalid input. Please provide the day and time in the format 'day hour'.")
    except Exception as e:
        respond(f"An error occurred: {e}. Please try again later.")


def send_weekly_report(workspace_id: str):
    client = app.client
    user_points = db.get_all_points(workspace_id)
    if user_points:
        try:
            blocks = custom_blocks.user_points_blocks(user_points)
            post_to_general(client, "Weekly Debit Points Update", blocks)
        except Exception as e:
            logging.error(f"Error sending weekly report: {e}")
    else:
        logging.error("No user points found in the database")


def run_scheduler():
    def send_report_job():
        print("Checking Report Job")
        client = app.client
        reports_daytime = db.get_report_daytime()
        if reports_daytime:
            for report_daytime in reports_daytime:
                day = report_daytime.day
                time_hour = report_daytime.hour
                workspace_id = report_daytime.workspace
                if day == datetime.datetime.today().strftime('%A') and datetime.datetime.now().hour == time_hour:
                    send_weekly_report(workspace_id)
        else:
            print('No report in database')

    def check_reset_mode():
        global last_reset_dates
        client = app.client
        today = datetime.datetime.now()
        reset_modes = db.get_reset_mode()

        if reset_modes:
            for reset_mode in reset_modes:
                workspace_id = reset_mode.workspace
                # Create a key for the current year and month
                current_month_key = f"{workspace_id}_{today.year}_{today.month}"

                # Only reset if mode is automatic, it's the first day of the month, 
                # and we haven't already reset for this month
                if (reset_mode.reset_mode == "automatic" and today.day == 1 and current_month_key not in last_reset_dates):

                    db.reset_debits_table(workspace_id)
                    post_to_general(client, "Database Reset Successful")

                    # Mark that we've reset for this month
                    last_reset_dates[current_month_key] = True
                    logging.info(f"Automatic reset performed for workspace {workspace_id}")
        else:
            logging.info('No mode in database')

    schedule.every().minutes.do(send_report_job)
    schedule.every().day.at("00:01").do(check_reset_mode)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    client = app.client

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    app.start(port=int(os.environ.get("PORT", 3000)))
