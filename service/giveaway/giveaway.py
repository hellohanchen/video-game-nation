import datetime
import random
import time
from typing import Dict, Optional

import discord

from constants import NBA_TEAM_IDS
from vgnlog.channel_logger import ADMIN_LOGGER
from provider.topshot.graphql.get_address import get_flow_account_info
from repository.ts_giveaways import message_giveaway, get_ongoing_giveaways, get_submission, get_submission_count, \
    join_giveaway, get_submitted_fav_team, ban_user, get_submissions_with_flow_info, close_giveaway, leave_giveaway
from repository.vgn_users import get_user_new
from service.common.profile.views import ProfileView


THUMBNAIL_URL = "https://i.ibb.co/TWmVsFB/g-01.png"


class Giveaway:
    def __init__(self, i, c, m, n, d, w, dur, f, ws, tb, e, s):
        self.id = i
        self.channel = c
        self.message = m
        self.name = n
        self.description = d
        self.winners = w
        self.duration = dur

        self.fav_teams = [] if f is None else f.split(',')
        self.set_weights = [] if ws is None else [int(w) for w in ws.split(',')]
        self.thumbnail_url: Optional[str] = tb
        self.end_at = e
        self.submissions = s
        self.view = None
        self.embed = discord.Embed(title=f"GIVEAWAY: {n.upper()}", description=self.__build_embed_content())
        self.embed.set_thumbnail(url=THUMBNAIL_URL if self.thumbnail_url is None else self.thumbnail_url)

    def __build_embed_content(self) -> str:
        content = ""
        if self.description is not None and len(self.description) > 0:
            content += f"Description: {self.description}\n\n"
        else:
            content += f"No description\n\n"
        content += f"Winners: {self.winners}\n\n"
        if len(self.fav_teams) > 0:
            content += f"Favorite Teams: **{','.join(self.fav_teams)}**\n\n"
        content += f"Ends at: **<t:{int(self.end_at.timestamp())}:R>**"
        return content

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
                await ADMIN_LOGGER.warn(f"Giveaway:FromDb:FetchMsg:{err}")
                message = None

        return Giveaway(g['id'], c, message, g['name'], g['description'], g['winners'], g['duration'],
                        g['fav_teams'], g['team_set_weights'], g['thumbnail_url'], g['end_at'], 0)

    async def refresh(self):
        if self.message is None:
            await self.send_message()

        if self.message is not None:
            if self.view is None:
                self.view = JoinGiveawayView(self)

            self.refresh_submission()
            self.view.join_button.label = f"Joined: {self.submissions}"
            await self.message.edit(embed=self.embed, view=self.view)

    def refresh_submission(self):
        s, err = get_submission_count(self.id)
        if err is None:
            self.submissions = s

    async def close(self):
        try:
            await self.refresh()

            submitted_users, err = get_submissions_with_flow_info(self.id)
            if err is not None:
                raise err
            random.shuffle(submitted_users)

            winners = []
            if len(self.fav_teams) > 0:
                i = 0

                while i < len(submitted_users) and len(winners) < self.winners:
                    winner = submitted_users[i]
                    i += 1

                    # try to validate winner's favorite team
                    retry = 1
                    fav_team_id = None
                    while retry >= 0 and fav_team_id is None:
                        _, _, fav_team_id, err = await get_flow_account_info(winner['topshot_username'])
                        if err is not None:
                            await ADMIN_LOGGER.warn(f"Giveaway:Close:GetFavTeam:{err}")
                            retry -= 1
                        time.sleep(0.3)

                    if fav_team_id is not None:
                        fav_team = NBA_TEAM_IDS.get(int(fav_team_id))
                        if winner['fav_team'] != fav_team:
                            _, err = ban_user(winner['user_id'])
                            if err is not None:
                                await ADMIN_LOGGER.warn(f"Giveaway:Close:BanUser:{err}")
                            continue

                    winners.append(winner)
            else:
                winners = submitted_users[:min(len(submitted_users), self.winners)]

            # close giveaway in db
            closed, err = close_giveaway(self.id)
            if not closed:
                return False

            # send out winner messages
            mentions = [f"<@{w['user_id']}>({w['topshot_username']})" for w in winners]
            await self.channel.send(f"Congratulations to the winners: {', '.join(mentions)} 🎉\n"
                                    f"Winning the giveaway of **{self.name}**")

            if self.message is not None:
                await self.message.edit(
                    content=f"**GIVEAWAY ENDED**\n"
                            f"Winners: {', '.join(mentions)}\n"
                            f"Reroll command: `.vgn.reroll {self.id}`",
                    view=None)

        except Exception as err:
            await ADMIN_LOGGER.error(f"Giveaway:Close:{err}")
            return False

        return True

    async def join(self, user):
        epoch = datetime.datetime.utcnow()
        if self.end_at <= epoch:
            return False, "Submission is already closed."

        submission, err = get_submission(self.id, user['flow_address'])
        if err is not None:
            await ADMIN_LOGGER.error(f"Giveaway:GetSubmission:{err}")
            return False, f"Join-GetSubmission:{err}"
        if submission is not None:
            return False, f"Flow account *{user['flow_address']}* has already joined this giveaway."

        fav_team = None
        if len(self.fav_teams) > 0:
            _, _, fav_team_id, err = await get_flow_account_info(user['topshot_username'])
            if err is not None:
                await ADMIN_LOGGER.warn(f"Giveaway:Join:GetFlow:{err}")
                return False, f"Join-GetFavTeam:{err}"
            fav_team = NBA_TEAM_IDS.get(int(fav_team_id))
            if fav_team not in self.fav_teams:
                return False, f"Favorite team requirement: {', '.join(self.fav_teams)}"

            submitted_fav_team, _ = get_submitted_fav_team(user['id'])
            if submitted_fav_team is not None and fav_team != submitted_fav_team:
                _, err = ban_user(user['id'])
                if err is not None:
                    await ADMIN_LOGGER.warn(f"Giveaway:Join:BanUser:{err}")
                return False, f"Favorite team rule violation."

        successful, err = join_giveaway(self.id, user, fav_team)
        if successful:
            return True, f"Joined!"
        else:
            await ADMIN_LOGGER.error(f"Giveaway:Join:{err}")
            return False, f"ERROR: Join:{err}"

    async def leave(self, uid):
        epoch = datetime.datetime.utcnow()
        if self.end_at <= epoch:
            return False, "Submission is already closed."

        successful, err = leave_giveaway(self.id, uid)
        if successful:
            return True, f"Your entry is removed."
        else:
            await ADMIN_LOGGER.error(f"Giveaway:Leave:{err}")
            return False, f"ERROR: Leave:{err}"


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
                    await ADMIN_LOGGER.error(f"Refresh {gid}:{err}")
                    continue

        for gid in expired:
            del self.giveaways[gid]


GIVEAWAY_SERVICE = GiveawayService()


class JoinRulesButton(discord.ui.Button['JoinRules']):
    def __init__(self):
        super(JoinRulesButton, self).__init__(style=discord.ButtonStyle.blurple, label="Rules", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        message = f"***GIVEAWAY RULES***\n\n" \
                  f"**Rule 0.** The rewards will be sent to the linked Topshot accounts of winners. Make sure your " \
                  f"Discord is linked to your own Topshot account.\n" \
                  f"**Rule 1.** If you join a **fav-team-gated** giveaway, don't change your fav-team before the " \
                  f"giveaway ends, otherwise you will be removed from all giveaways.\n" \
                  f"**Rule 2.** If you are in **an ongoing fav-team-gated** giveaway, don't change your fav-team " \
                  f"to join another gated giveaway with a different team, otherwise you will be removed from all " \
                  f"giveaways.\n"
        await interaction.response.send_message(content=message, ephemeral=True, delete_after=120.0)


class JoinGiveawayButton(discord.ui.Button['Join']):
    def __init__(self, count):
        super(JoinGiveawayButton, self).__init__(style=discord.ButtonStyle.success, label=f"Joined: {count}", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: JoinGiveawayView = self.view

        user_id = interaction.user.id
        user, err = get_user_new(user_id)
        if err is not None:
            await ADMIN_LOGGER.error(f"Giveaway:Join:GetUser:{err}")
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
        await interaction.response.send_message(content=content, ephemeral=True, delete_after=30.0)
        if joined:
            await view.giveaway.refresh()


class LeaveGiveawayButton(discord.ui.Button['Quit']):
    def __init__(self):
        super(LeaveGiveawayButton, self).__init__(style=discord.ButtonStyle.red, label=f"Leave", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: JoinGiveawayView = self.view
        leaved, content = await view.giveaway.leave(interaction.user.id)
        await interaction.response.send_message(content=content, ephemeral=True, delete_after=30.0)
        if leaved:
            await view.giveaway.refresh()


class JoinGiveawayView(discord.ui.View):
    def __init__(self, giveaway: Giveaway):
        super(JoinGiveawayView, self).__init__()
        giveaway.refresh_submission()
        self.join_button: discord.ui.Button = JoinGiveawayButton(giveaway.submissions)
        self.add_item(self.join_button)
        self.giveaway: Giveaway = giveaway
        self.add_item(JoinRulesButton())
        self.add_item(LeaveGiveawayButton())
