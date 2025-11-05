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
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Checklist Commands",
                "emoji": true
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*1️⃣ Use the `/create-checklist` command*. Opens a modal to create a new reusable checklist with multiple tasks."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*2️⃣ Use the `/checklist` command*. Type `/checklist` to see all available checklists or `/checklist [name]` to use a specific checklist in the current channel."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*3️⃣ Use the `/delete-checklist` command*. Opens a modal to delete an existing checklist."
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


def create_checklist_modal():
    """Modal for creating a new checklist"""
    return {
        "type": "modal",
        "callback_id": "create_checklist",
        "title": {
            "type": "plain_text",
            "text": "Create Checklist",
            "emoji": true
        },
        "submit": {
            "type": "plain_text",
            "text": "Create",
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
                "block_id": "checklist_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "checklist_name_input",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter checklist name"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Checklist Name",
                    "emoji": true
                }
            },
            {
                "type": "input",
                "block_id": "checklist_items",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "checklist_items_input",
                    "multiline": true,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter items, one per line"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Checklist Items",
                    "emoji": true
                }
            }
        ]
    }


def view_checklists_modal(checklists):
    """Modal for displaying all available checklists"""
    if not checklists:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No checklists found. Create one with `/create-checklist`.",
                },
            }
        ]
    else:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Use `/checklist [name]` in a channel to post it.",
                },
            },
            {"type": "divider"},
        ]

        for checklist in checklists:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{checklist}`",
                    },
                }
            )

    return {
        "type": "modal",
        "callback_id": "view_checklists",
        "title": {
            "type": "plain_text",
            "text": "Checklists",
            "emoji": true,
        },
        "close": {
            "type": "plain_text",
            "text": "Close",
            "emoji": true,
        },
        "blocks": blocks,
    }


def delete_checklist_modal(checklists):
    """Modal for deleting an existing checklist"""
    options = [
        {
            "text": {
                "type": "plain_text", 
                "text": name
            },
            "value": name
        }
        for name in checklists
    ]
    
    return {
        "type": "modal",
        "callback_id": "delete_checklist",
        "title": {
            "type": "plain_text",
            "text": "Delete Checklist",
            "emoji": true
        },
        "submit": {
            "type": "plain_text",
            "text": "Delete",
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
                    "text": "Select a checklist to delete:"
                }
            },
            {
                "type": "input",
                "block_id": "checklist_select",
                "element": {
                    "type": "static_select",
                    "action_id": "checklist_select_action",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a checklist"
                    },
                    "options": options
                },
                "label": {
                    "type": "plain_text",
                    "text": "Checklist",
                    "emoji": true
                }
            }
        ]
    }


def render_checklist_instance(instance_data):
    """Render a checklist instance with completed items"""
    # Safely get creation time with fallback
    created_at = instance_data.get('created_at')
    if created_at:
        try:
            created_time = datetime.datetime.fromisoformat(created_at).strftime('%b %d, %Y at %I:%M %p')
            created_text = f"Created: {created_time}"
        except (ValueError, TypeError):
            created_text = "Creation time not available"
    else:
        created_text = "Creation time not available"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 {instance_data.get('name', 'Unnamed Checklist')}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": created_text
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    # Render each checklist item
    for item in instance_data.get('items', []):
        is_checked = item.get('is_checked', 0) == 1
        checked_info = ""
        
        if is_checked and item.get('checked_by'):
            checked_time = ""
            if item.get('checked_at'):
                try:
                    checked_time = datetime.datetime.fromisoformat(item['checked_at']).strftime('%b %d at %I:%M %p')
                except (ValueError, TypeError):
                    checked_time = ""
            checked_info = f" ✅ _Completed by <@{item['checked_by']}>"
            if checked_time:
                checked_info += f" on {checked_time}"
            checked_info += "_"

        # Create the checkbox element
        checkbox = {
            "type": "checkboxes",
            "action_id": f"toggle_item_{item.get('id', '')}_{instance_data.get('instance_id', '')}",
            "options": [
                {
                    "text": {
                        "type": "mrkdwn",
                        "text": "Complete"
                    },
                    "value": f"item_{item.get('id', '')}_{instance_data.get('instance_id', '')}"
                }
            ]
        }
        
        if is_checked:
            checkbox["initial_options"] = checkbox["options"]

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{item.get('text', 'Unnamed item')}{checked_info}"
            },
            "accessory": checkbox
        })

    # Add completion message if complete
    if instance_data.get('is_complete', 0) == 1:
        time_str = "Time information not available"
        completed_text = "Completion time not available"
        
        try:
            created_at = instance_data.get('created_at')
            completed_at = instance_data.get('completed_at', datetime.datetime.now().isoformat())
            
            if created_at and completed_at:
                start = datetime.datetime.fromisoformat(created_at)
                end = datetime.datetime.fromisoformat(completed_at)
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
                
                completed_text = f"Completed: {end.strftime('%b %d, %Y at %I:%M %p')}"
        except (ValueError, TypeError, AttributeError):
            pass

        blocks.extend([
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"✅ *All items completed!* Time taken: {time_str}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": completed_text
                    }
                ]
            }
        ])

    return blocks

def checklist_completion_message(checklist_name, time_taken):
    """Message to send when a checklist is completed"""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ *Checklist \"{checklist_name}\" has been completed in {time_taken}!*"
            }
        }
    ]

def list_checklists_blocks(checklists):
    """Display a list of available checklists"""
    if not checklists:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No checklists found. Create one with the `/create-checklist` command."
                }
            }
        ]
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Available Checklists",
                "emoji": true
            }
        },
        {
            "type": "divider"
        }
    ]
    
    for checklist in checklists:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"`/checklist {checklist}`"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View",
                    "emoji": true
                },
                "action_id": "view_checklist_button",
                "value": checklist
            }
        })

    return blocks
