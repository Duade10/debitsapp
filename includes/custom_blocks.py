import datetime

true = True


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
                    "text": "Select User",
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
                    "text": "Points",
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

    for user_id, total, link in user_points:
        section_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Point(s): {total}*\nUser: <@{user_id}>"
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
