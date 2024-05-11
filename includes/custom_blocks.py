import datetime

true = True


def get_app_mention_block():
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hello there! 👋 I'm Debits Bot, here to help you keep track of debit points within your team. With me, you can easily assign and record debit points for various reasons."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Use the `/add` command*. Type `/add` command followed by `@username` and the amount of points. For example: `/add @john.doe 1` "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*2️⃣ Use the `/delete` command*. Type `/delete` command followed by `@username` and the amount of points. For example: `/delete @john.doe 1` to remove points "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*3️⃣ Use the `add_point` or `remove_point` shortcuts*. Click `add_point` or `remove_point` in the context menu and fill the form."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*4️⃣ You can use the `/points` * command to view a leaderboard of users and their accumulated debit points. <`/points` or `/points @john.doe`>"
            }
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "For Scheduling",
                "emoji": true
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Use the `/set-report-day` command*. Type `/set-record` command followed by `the day of the week` and the `hour` of the day you want to get the reports weekly. For example: `/debit friday 18` "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*2️⃣ Use the `/reset` command*. Type `/reset` command to clear the contents of the debit table in the database. Only administrators are permitted to use this command."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*3️⃣ Use the `/set-reset-mode` command*. Type `/set-reset-mode` command to configure whether the bot should automatically clears the database automatically or not. *Automatic* and *Manual* are only options available. Only administrators are permitted to use this command. "
            }
        }
    ]


def points_modal(permalink, request_type, true=True):
    return {
        "type": "modal",
        "callback_id": request_type,
        "title": {
            "type": "plain_text",
            "text": "My App",
            "emoji": true
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit",
            "emoji": true
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": true
        },
        "blocks": [
            {
                "type": "input",
                "block_id": "user",
                "element": {
                    "type": "multi_users_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select users",
                        "emoji": true
                    },
                    "action_id": "multi_users_select-action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Select User (One User)",
                    "emoji": true
                }
            },
            {
                "type": "input",
                "block_id": "points",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "plain_text_input-action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Points (Numbers Only)",
                    "emoji": true
                }
            },
            {
                "type": "divider"
            },
            {
                "dispatch_action": true,
                "type": "input",
                "block_id": "timestamp",
                "element": {
                    "initial_value": permalink,
                    "type": "plain_text_input",
                    "action_id": "timestamp_input"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Timestamp",
                    "emoji": true
                }
            }
        ]
    }


def user_points_blocks(user_points):
    now = datetime.datetime.now()
    date_time_str = now.strftime("%A, %B %d, %Y \n %I:%M %p")
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Here are all the users and points as of *\n {date_time_str}"
            },
            "accessory": {
                "type": "image",
                "image_url": "https://api.slack.com/img/blocks/bkb_template_images/notifications.png",
                "alt_text": "calendar thumbnail"
            }
        },
        {
            "type": "divider"
        }
    ]

    for user_data in user_points:
        user_id = user_data.user
        total = user_data.amount
        section_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*User: <@{user_id}>*\n *Point(s): {total}*"
            }
        }
        blocks.append(section_block)

    return blocks


def add_points_block(pr_amount, amount, cur_amount, user_id, link=None, true=True):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{amount} Points have been added to <@{user_id}>"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Previous Point(s):* {pr_amount} \n*Current Point(s) :* {cur_amount}"
                }
            ]
        }]
    if link:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "emoji": true,
                        "text": "Thread"
                    },
                    "style": "primary",
                    "url": link
                }
            ]
        })
    return blocks


def remove_points_block(pr_amount, amount, cur_amount, user_id, link=None, true=True):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{amount} Points have been removed from <@{user_id}>"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Previous Point(s):* {pr_amount} \n*Current Point(s) :* {cur_amount}"
                }
            ]
        }]
    if link:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "emoji": true,
                        "text": "Thread"
                    },
                    "style": "primary",
                    "url": link
                }
            ]
        })
    return blocks


def reset_db_modal_blocks():
    blocks = {
        "type": "modal",
        "callback_id": "reset",
        "title": {
            "type": "plain_text",
            "text": "My App",
            "emoji": true
        },
        "submit": {
            "type": "plain_text",
            "text": "Proceed",
            "emoji": true
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": true
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Are you sure you want to reset the database?"
                }
            }
        ]
    }
    return blocks
