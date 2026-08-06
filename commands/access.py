PRIVATE_ONLY_NOTICE = "🔒 Please message me privately for this — tap my name and press Send Message."

ADMIN_ONLY_NOTICE = "🚫✨ Sorry po, boss — admin/owner *lang* po ang pwedeng gumamit ng command na 'to! 👑🔐"


def is_private(update) -> bool:
    return update.effective_chat.type == "private"