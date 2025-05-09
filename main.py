import datetime
import logging
import os
import threading
import time
import re
from typing import List, Optional

import schedule
from dotenv import load_dotenv
from slack_bolt import App
from slack_sdk.errors import SlackApiError

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


def post_to_general(client, text: str, blocks: Optional[List[dict]] = None):
    try:
        message_payload = {
            "channel": "debits-general",
            "text": text,
        }
        if blocks:
            message_payload["blocks"] = blocks

        client.chat_postMessage(**message_payload)

    except SlackApiError as e:
        logging.error(f"Error posting message to general channel: {e.response['error']}")


def post_to_channel(client, channel_id: str, text: str, blocks: Optional[List[dict]] = None):
    try:
        message_payload = {
            "channel": channel_id,
            "text": text,
        }
        if blocks:
            message_payload["blocks"] = blocks

        client.chat_postMessage(**message_payload)

    except SlackApiError as e:
        logging.error(f"Error posting message to channel {channel_id}: {e.response['error']}")
        try:
            post_to_general(client, text, blocks)
        except SlackApiError as e:
            logging.error(f"Error posting message to general channel as fallback: {e.response['error']}")


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
def handle_add_point_command(ack, body, client, say):
    ack()

    text = body["text"]
    try:
        target_user_id, amount = utils.parse_input(text)
        workspace_id = utils.get_workspace(body)

        previous_amount, amount, current_amount = db.record_debit(target_user_id, workspace_id, int(amount))
        blocks = custom_blocks.add_points_block(previous_amount, amount, current_amount, target_user_id)
        post_to_general(client, f"{amount} points have been added to <@{target_user_id}>", blocks)
    except ValueError as e:
        # Return a helpful error message to the user
        error_message = f"Error: {str(e)}"
        post_to_general(client, error_message)


@app.command("/delete")
def handle_remove_point_command(ack, body, say):
    ack()

    channel_id = utils.get_workspace(body)
    text = body["text"]
    target_user_id, amount = utils.parse_input(text)
    workspace_id = utils.get_workspace(body)
    if target_user_id:
        previous_amount, amount, current_amount = db.remove_debit(target_user_id, workspace_id, int(amount))
        blocks = custom_blocks.remove_points_block(previous_amount, amount, current_amount, target_user_id)
        post_to_general(client, f"{amount} points have been removed from {target_user_id}", blocks)
        # post_to_channel(client, channel_id, f"{amount} points have been added to {target_user_id}", blocks)


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


@app.command("/create-checklist")
def handle_create_checklist_command(ack, body, client):
    """Command handler for /create-checklist"""
    ack()
    
    trigger_id = body["trigger_id"]
    blocks = custom_blocks.create_checklist_modal()
    client.views_open(trigger_id=trigger_id, view=blocks)


@app.view("create_checklist")
def handle_create_checklist_submission(ack, body, client):
    """Handle submission of the create checklist modal"""
    # Extract the values
    checklist_name = body["view"]["state"]["values"]["checklist_name"]["checklist_name_input"]["value"]
    items_text = body["view"]["state"]["values"]["checklist_items"]["checklist_items_input"]["value"]
    items = [item.strip() for item in items_text.split("\n") if item.strip()]
    
    # Get user and workspace info
    user_id = body["user"]["id"]
    workspace_id = utils.get_workspace(body)
    
    # Create the checklist
    success = db.create_checklist(checklist_name, workspace_id, user_id, items)
    
    # Acknowledge the submission
    ack()
    
    # Send a confirmation message to the user
    if success:
        try:
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f"Checklist '{checklist_name}' created successfully! Use `/checklist {checklist_name}` to use it."
            )
        except Exception as e:
            logging.error(f"Error sending confirmation: {e}")
    else:
        try:
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f"Error creating checklist '{checklist_name}'. Please try again."
            )
        except Exception as e:
            logging.error(f"Error sending error message: {e}")


@app.command("/checklist")
def handle_checklist_command(ack, body, client, say):
    """Command handler for /checklist"""
    ack()

    channel_id = body["channel_id"]
    workspace_id = utils.get_workspace(body)
    checklist_name = body["text"].strip()

    if not checklist_name:
        # If no name provided, list all available checklists
        checklists = db.get_all_checklists(workspace_id)
        blocks = custom_blocks.list_checklists_blocks(checklists)
        say(blocks=blocks, text="Available Checklists")
        return

    # Get the checklist by name
    checklist = db.get_checklist_by_name(checklist_name, workspace_id)
    if not checklist:
        say(f"Checklist '{checklist_name}' not found. Use `/checklist` to see available checklists.")
        return

    # Create the checklist instance before posting
    instance_id = db.create_checklist_instance(checklist["id"], channel_id, "temp")  # placeholder ts
    if not instance_id:
        say("Error creating checklist instance. Please try again.")
        return

    instance_data = db.get_checklist_instance(instance_id)
    if not instance_data:
        say("Error retrieving checklist instance data.")
        return

    # Post the checklist message
    response = client.chat_postMessage(
        channel=channel_id,
        blocks=custom_blocks.render_checklist_instance(instance_data),
        text=f"Checklist: {checklist_name}"
    )

    # Update the instance with the real message timestamp
    if response["ok"]:
        message_ts = response["ts"]
        with db.Session() as session:
            inst = session.query(db.ChecklistInstance).filter_by(id=instance_id).first()
            inst.message_ts = message_ts
            session.commit()



@app.command("/delete-checklist")
def handle_delete_checklist_command(ack, body, client):
    """Command handler for /delete-checklist"""
    ack()
    
    workspace_id = utils.get_workspace(body)
    user_id = utils.get_user_id(body, "body")
    
    # Get all available checklists
    checklists = db.get_all_checklists(workspace_id)
    if not checklists:
        client.chat_postEphemeral(
            channel=body["channel_id"],
            user=user_id,
            text="No checklists found to delete."
        )
        return
    
    # Show the delete modal
    blocks = custom_blocks.delete_checklist_modal(checklists)
    client.views_open(trigger_id=body["trigger_id"], view=blocks)


@app.action(re.compile("toggle_item_(.*)"))
def handle_item_toggle(ack, body, client):
    """Handle checkbox actions for checklist items"""
    ack()
    
    # Extract info from the action
    action_id = body["actions"][0]["action_id"]
    selected = len(body["actions"][0]["selected_options"]) > 0
    
    # Extract item_id and instance_id from the action_id
    # Format: toggle_item_{item_id}_{instance_id}
    parts = action_id.split("_")
    if len(parts) >= 3:
        item_id = parts[2]
        instance_id = parts[3] if len(parts) > 3 else None
        
        if not instance_id:
            logging.error(f"No instance_id found in action: {action_id}")
            return
        
        # Get user info
        user_id = body["user"]["id"]
        
        # Update the item status
        result = db.update_checklist_item(int(instance_id), int(item_id), selected, user_id)
        
        if result and "all_complete" in result and result["all_complete"]:
            # If all items are checked, get the updated instance and update the message
            instance_data = db.get_checklist_instance(result["checklist_instance"])
            if instance_data:
                # Update the message with the completed checklist
                try:
                    client.chat_update(
                        channel=body["channel"]["id"],
                        ts=body["message"]["ts"],
                        blocks=custom_blocks.render_checklist_instance(instance_data),
                        text=f"Checklist: {instance_data['name']}"
                    )
                    
                    # Send completion notification with duration
                    client.chat_postMessage(
                        channel=body["channel"]["id"],
                        blocks=custom_blocks.checklist_completion_message(
                            instance_data["name"],
                            instance_data["created_at"],
                            instance_data["completed_at"]
                        ),
                        text=f"Checklist '{instance_data['name']}' completed!"
                    )
                except Exception as e:
                    logging.error(f"Error updating message: {e}")
        else:
            # Update the UI to reflect the change
            instance_data = db.get_checklist_instance(int(instance_id))
            if instance_data:
                try:
                    client.chat_update(
                        channel=body["channel"]["id"],
                        ts=body["message"]["ts"],
                        blocks=custom_blocks.render_checklist_instance(instance_data),
                        text=f"Checklist: {instance_data['name']}"
                    )
                except Exception as e:
                    logging.error(f"Error updating message: {e}")


@app.view("delete_checklist")
def handle_delete_checklist_submission(ack, body, client):
    """Handle submission of the delete checklist modal"""
    # Extract the values
    selected_checklist = body["view"]["state"]["values"]["checklist_select"]["checklist_select_action"]["selected_option"]["value"]
    workspace_id = utils.get_workspace(body)
    user_id = body["user"]["id"]

    # Delete the checklist
    success = db.delete_checklist(selected_checklist, workspace_id)

    # Acknowledge the submission
    ack()

    # Send a confirmation message to the user
    if success:
        try:
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f"Checklist '{selected_checklist}' deleted successfully!"
            )
        except Exception as e:
            logging.error(f"Error sending confirmation: {e}")
    else:
        try:
            client.chat_postEphemeral(
                channel=user_id,
                user=user_id,
                text=f"Error deleting checklist '{selected_checklist}'. Please try again."
            )
        except Exception as e:
            logging.error(f"Error sending error message: {e}")


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
        logging.info("Checking Report Job")
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
            logging.info('No report in database')

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
