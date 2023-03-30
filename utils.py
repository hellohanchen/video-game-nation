def truncate_message(messages, msg, to_add, limit):
    if len(msg) + len(to_add) >= limit:
        messages.append(msg)
        return to_add, ""
    else:
        return msg + to_add, ""
