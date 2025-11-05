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


@app.shortcut("open_create_checklist")
def handle_create_checklist_shortcut(ack, body, client):
    """Global shortcut handler to open the create checklist modal"""
    ack()

    trigger_id = body["trigger_id"]
    blocks = custom_blocks.create_checklist_modal()
    client.views_open(trigger_id=trigger_id, view=blocks)


@app.shortcut("view_checklists")
def handle_view_checklists_shortcut(ack, body, client):
    """Global shortcut handler to view all checklists"""
    ack()

    workspace_id = utils.get_workspace(body)
    checklists = db.get_all_checklists(workspace_id)
    modal = custom_blocks.view_checklists_modal(checklists)
    client.views_open(trigger_id=body["trigger_id"], view=modal)


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
    command_text = body["text"].strip()

    # Parse checklist name and mentioned users
    parts = command_text.split()
    checklist_name = parts[0] if parts else ""
    mentioned_users = [part for part in parts[1:] if part.startswith('@')]

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
    instance_id = db.create_checklist_instance(checklist["id"], channel_id, "temp")
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

        # Notify mentioned users
        for user in mentioned_users:
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user.strip('@'),
                    text=f"You've been mentioned in checklist '{checklist_name}'. Check it out in this channel!"
                )
            except Exception as e:
                logging.error(f"Error notifying user {user}: {e}")


@app.action("view_checklist_button")
def handle_view_checklist_button(ack, body, client):
    """Handle clicks on the view button for checklist listings"""
    ack()

    action = body.get("actions", [{}])[0]
    checklist_name = action.get("value")
    user_id = body.get("user", {}).get("id")
    workspace_id = utils.get_workspace(body)
    container_type = body.get("container", {}).get("type")
    channel_id = body.get("channel", {}).get("id")

    if not all([checklist_name, user_id, workspace_id]):
        logging.error("Missing mandatory data in view checklist action payload")
        return

    # When launched from the modal, there is no channel in the payload.
    # Open a direct message with the user so we can share the checklist instance there.
    if not channel_id and container_type == "view":
        try:
            dm_response = client.conversations_open(users=user_id)
            channel_id = dm_response.get("channel", {}).get("id")
        except SlackApiError as e:
            logging.error(f"Unable to open DM for checklist preview: {e.response['error'] if e.response else e}")
            return

    if not channel_id:
        logging.error("Unable to determine a destination channel for the checklist view action")
        return

    def notify_user(message: str):
        try:
            if container_type == "view":
                client.chat_postMessage(channel=channel_id, text=message)
            else:
                client.chat_postEphemeral(channel=channel_id, user=user_id, text=message)
        except SlackApiError as e:
            logging.error(f"Failed to notify user about checklist view error: {e.response['error'] if e.response else e}")

    checklist = db.get_checklist_by_name(checklist_name, workspace_id)
    if not checklist:
        notify_user(f"Checklist '{checklist_name}' was not found. It may have been deleted.")
        return

    instance_id = db.create_checklist_instance(checklist["id"], channel_id, "temp")
    if not instance_id:
        notify_user("Unable to create checklist instance. Please try again later.")
        return

    instance_data = db.get_checklist_instance(instance_id)
    if not instance_data:
        notify_user("Unable to load the checklist. Please try again later.")
        return

    response = client.chat_postMessage(
        channel=channel_id,
        blocks=custom_blocks.render_checklist_instance(instance_data),
        text=f"Checklist: {checklist_name}"
    )

    if response.get("ok"):
        message_ts = response.get("ts")
        try:
            with db.Session() as session:
                instance = session.query(db.ChecklistInstance).filter_by(id=instance_id).first()
                if instance and message_ts:
                    instance.message_ts = message_ts
                    session.commit()
        except Exception as e:
            logging.error(f"Error updating checklist instance timestamp: {e}")
    else:
        notify_user("Failed to post the checklist to the channel.")


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
    
    try:
        # Extract action details
        action_id = body["actions"][0]["action_id"]
        selected = len(body["actions"][0]["selected_options"]) > 0
        parts = action_id.split("_")
        
        if len(parts) < 4:
            logging.error(f"Invalid action format: {action_id}")
            return
            
        item_id = parts[2]
        instance_id = parts[3]
        user_id = body["user"]["id"]
        
        # Update the item status
        result = db.update_checklist_item(int(instance_id), int(item_id), selected, user_id)
        if not result:
            logging.error("Failed to update checklist item")
            return
            
        # Get updated instance data
        instance_data = db.get_checklist_instance(int(instance_id))
        if not instance_data:
            logging.error(f"No instance data found for instance_id: {instance_id}")
            return

        # Format timestamps
        def format_timestamp(ts):
            if not ts:
                return None
            try:
                return datetime.datetime.fromisoformat(ts).strftime('%b %d at %I:%M %p')
            except (ValueError, TypeError):
                return None

        created_at = format_timestamp(instance_data.get('created_at'))
        completed_at = format_timestamp(instance_data.get('completed_at'))
        
        # Calculate time taken if both timestamps exist
        time_str = "Time information not available"
        if instance_data.get('created_at') and instance_data.get('completed_at'):
            try:
                start = datetime.datetime.fromisoformat(instance_data['created_at'])
                end = datetime.datetime.fromisoformat(instance_data['completed_at'])
                delta = end - start
                
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                if delta.days > 0:
                    time_str = f"{delta.days} days, {hours} hours"
                elif hours > 0:
                    time_str = f"{hours} hours, {minutes} minutes"
                elif minutes > 0:
                    time_str = f"{minutes} minutes, {seconds} seconds"
                else:
                    time_str = f"{seconds} seconds"
            except (ValueError, TypeError):
                pass

        # Update the checklist message
        client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            blocks=custom_blocks.render_checklist_instance(instance_data),
            text=f"Checklist: {instance_data.get('name', 'Unnamed Checklist')}"
        )

        # Send completion message if all items are complete
        if result.get("all_complete", False):
            completion_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Checklist \"{instance_data.get('name', 'Unnamed Checklist')}\" has been completed!*"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏱️ Time taken: {time_str}"
                        }
                    ]
                }
            ]
            
            if created_at:
                completion_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🕒 Started: {created_at}"
                        }
                    ]
                })
            
            if completed_at:
                completion_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🏁 Completed: {completed_at}"
                        }
                    ]
                })

            client.chat_postMessage(
                channel=body["channel"]["id"],
                blocks=completion_blocks,
                text=f"Checklist completed in {time_str}!"
            )

    except Exception as e:
        logging.error(f"Error in handle_item_toggle: {e}")

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
