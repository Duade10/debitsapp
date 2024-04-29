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
