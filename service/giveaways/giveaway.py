import datetime
from typing import Dict

import discord

from constants import NBA_TEAM_IDS
from provider.topshot.graphql.get_address import get_flow_account_info
from repository.ts_giveaways import message_giveaway, get_ongoing_giveaways, get_submission, get_submission_count, \
    join_giveaway
from repository.vgn_users import get_user_new
from service.common.profile.views import ProfileView


class Giveaway:
    def __init__(self, i, c, m, n, d, w, dur, f, ws, e, s):
        self.id = i
        self.channel = c
        self.message = m
        self.name = n
        self.description = d
        self.winners = w
        self.duration = dur

        self.fav_teams = [] if f is None else f.split(',')
        self.set_weights = [] if ws is None else [int(w) for w in ws.split(',')]
        self.end_at = e
        self.submissions = s
        self.view = None

        content = ""
        if d is not None and len(d) > 0:
            content += f"Description: {d}\n\n"
        else:
            content += f"No description\n\n"
        content += f"Winners:{w}\n\n"
        if len(self.fav_teams) > 0:
            content += f"Favorite Teams: **{f}**\n\n"
        content += f"Ends at: **<t:{int(e.timestamp())}:R>**"

        self.embed = discord.Embed(title=f"GIVEAWAY: {n.upper()}", description=content)

    async def send_message(self):
        if self.message is not None:
            return True, f"Message already exists in {self.channel.name}"

        try:
            view = JoinGiveawayView(self)
            message = await self.channel.send(embed=self.embed, view=view)
            message_giveaway(self.id, message.id)
        except Exception as err:
            return False, f"Failed sending message to {self.channel.name}: {err}"

        self.view = view
        self.message = message
        return True, f"Successfully created giveaway in {self.channel.name}"

    @staticmethod
    async def from_db(g, c):
        message = None
        if g['message_id'] != 0:
            try:
                message = await c.fetch_message(g['message_id'])
            except Exception as err:
                message = None

        return Giveaway(g['id'], c, message, g['name'], g['description'], g['winners'], g['duration'],
                        g['fav_teams'], g['team_set_weights'], g['end_at'], 0)

    async def refresh(self):
        if self.message is None:
            await self.send_message()

        if self.message is not None:
            if self.view is None:
                self.view = JoinGiveawayView(self)

            await self.message.edit(embed=self.embed, view=self.view)

    def refresh_submission(self):
        s, err = get_submission_count(self.id)
        if err is None:
            self.submissions = s

    async def close(self):
        return False

    async def join(self, user):
        epoch = datetime.datetime.utcnow()
        if self.end_at <= epoch:
            return False, "Submission is already closed."

        submission, err = get_submission(self.id, user['id'])
        if err is not None:
            return False, f"Join-GetSubmission:{err}"
        if submission is not None:
            if submission['fav_team'] is not None:
                try:
                    _, _, fav_team_id = await get_flow_account_info(user['topshot_username'])
                except Exception as err:
                    return False, f"Submit-GetFavTeam:{err}"
                fav_team = NBA_TEAM_IDS.get(int(fav_team_id))
                if fav_team is not None and len(fav_team) > 0:
                    if fav_team != submission['fav_team']:
                        # TODO: ban user
                        pass
            return False, "Already joined."

        fav_team = None
        if len(self.fav_teams) > 0:
            try:
                _, _, fav_team_id = await get_flow_account_info(user['topshot_username'])
            except Exception as err:
                return False, f"Join-GetFavTeam:{err}"
            fav_team = NBA_TEAM_IDS.get(int(fav_team_id))
            if fav_team not in self.fav_teams:
                return False, f"Favourite team requirement: {self.fav_teams}"

        successful, err = join_giveaway(self.id, user, fav_team)
        if successful:
            return True, f"Joined!"
        else:
            return False, f"ERROR: Join:{err}"


class GiveawayService:
    def __init__(self):
        self.giveaways: Dict[int, Giveaway] = {}

    async def load_from_guilds(self, guilds):
        giveaways, _ = get_ongoing_giveaways()
        for g in giveaways:
            if g['guild_id'] in guilds:
                guild = guilds[g['guild_id']]
                if g['channel_id'] in guild['channels']:
                    channel = guild['channels'][g['channel_id']]
                    giveaway = await Giveaway.from_db(g, channel)
                    self.add(giveaway)

    def add(self, giveaway: Giveaway):
        if giveaway.id not in self.giveaways:
            self.giveaways[giveaway.id] = giveaway

    async def refresh(self):
        expired = []
        epoch = datetime.datetime.utcnow()
        for gid in self.giveaways:
            giveaway = self.giveaways[gid]
            if giveaway.end_at <= epoch:
                successful = await giveaway.close()
                if successful:
                    expired.append(gid)
            else:
                try:
                    await self.giveaways[gid].refresh()
                except Exception as err:
                    pass

        for gid in expired:
            del self.giveaways[gid]


GIVEAWAY_SERVICE = GiveawayService()


class JoinGiveawayButton(discord.ui.Button['Join']):
    def __init__(self, count):
        super(JoinGiveawayButton, self).__init__(style=discord.ButtonStyle.success, label=f"Joined: {count}", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: JoinGiveawayView = self.view

        user_id = interaction.user.id
        user, err = get_user_new(user_id)
        if err is not None:
            await interaction.response.send_message(
                content=f"ERROR: Join-GetUser:{err}", ephemeral=True, delete_after=30.0)
            return
        if user is None:
            await interaction.response.send_message(
                content=f"Please link TS account first then retry.",
                view=ProfileView(user_id),
                ephemeral=True, delete_after=600.0)
            return

        joined, content = await view.giveaway.join(user)
        if joined:
            view.giveaway.refresh_submission()
            self.label = f"Joined: {view.giveaway.submissions}"

        await interaction.response.send_message(content=content, ephemeral=True, delete_after=30.0)
        await view.giveaway.refresh()


class JoinGiveawayView(discord.ui.View):
    def __init__(self, giveaway: Giveaway):
        super(JoinGiveawayView, self).__init__()
        giveaway.refresh_submission()
        self.add_item(JoinGiveawayButton(giveaway.submissions))
        self.giveaway: Giveaway = giveaway
