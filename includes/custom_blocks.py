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
