from typing import Any

import main


def parse_input(input_string):
    input_strings = str(input_string).split()

    if len(input_strings) != 2:
        raise ValueError("Input string must contain exactly two elements: user ID and amount")

    user_id = input_strings[0]
    if not user_id.startswith('@'):
        raise ValueError("User ID must start with '@'")
    user_id = user_id[1:]

    amount = input_strings[1]
    try:
        amount = int(amount)
    except ValueError:
        raise ValueError("Amount must be a valid numerical value")

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
