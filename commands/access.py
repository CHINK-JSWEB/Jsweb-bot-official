PRIVATE_ONLY_NOTICE = "🔒 Please message me privately for this — tap my name and press Send Message."


def is_private(update) -> bool:
    return update.effective_chat.type == "private"