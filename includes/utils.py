from typing import Any

import main
import logging

def parse_input(input_string):
    input_strings = str(input_string).strip().split()
    
    # Check if input is empty
    if not input_strings:
        raise ValueError("Please provide a user and an amount (e.g., '@username 5')")
    
    # Check if both user and amount are provided
    if len(input_strings) != 2:
        raise ValueError("Please provide both a user and an amount (e.g., '@username 5')")
    
    user_id = input_strings[0]
    # Check if user ID starts with @
    if not user_id.startswith('@'):
        raise ValueError("User ID must start with '@' (e.g., '@username')")
    user_id = user_id[1:]  # Remove the @ symbol
    
    amount = input_strings[1]
    # Check if amount is a valid integer
    try:
        amount = int(amount)
    except ValueError:
        raise ValueError(f"'{amount}' is not a valid number. Amount must be a number.")
    
    return user_id, amount


def is_workspace_admin(user_id):
    try:
        user_info = main.app.client.users_info(user=user_id)
        is_admin = user_info["user"]["is_admin"]
        is_owner = user_info["user"]["is_owner"]
        is_primary_owner = user_info["user"]["is_primary_owner"]

        return is_admin or is_owner or is_primary_owner
    except Exception as e:
        print(f"Error checking workspace admin status: {e}")
        return False


def get_workspace(body: dict) -> Any | None:
    try:
        team_id = body.get("team_id") or body.get("team", {}).get("id")
        return team_id
    except Exception as e:
        print(f"An error occurred while extracting team ID: {e}")
        return None


def get_user_id(data: dict, data_type: str) -> str:
    user_id = None
    if data_type == "event":
        user_id = data["user"]
    elif data_type == "body":
        try:
            user_id = data["user_id"]
        except KeyError:
            user_id = data["user"]["id"]
    return user_id


def format_time_difference(start_time, end_time):
    """Format the difference between two ISO timestamps"""
    start = datetime.datetime.fromisoformat(start_time)
    end = datetime.datetime.fromisoformat(end_time)
    delta = end - start
    
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if delta.days > 0:
        return f"{delta.days} days, {hours} hours"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes"
    elif minutes > 0:
        return f"{minutes} minutes, {seconds} seconds"
    else:
        return f"{seconds} seconds"