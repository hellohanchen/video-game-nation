import discord


class BaseView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
