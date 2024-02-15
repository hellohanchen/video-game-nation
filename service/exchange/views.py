from typing import List

import discord

from constants import INVALID_ID
from service.exchange.listing import Listing, EXCHANGE_SETS, EXCHANGE_SET_NAMES
from service.views import BaseView

EXCHANGE_MESSAGE = "**Video Game Nation Exchange System**\n\n" \
                   "VGNES helps discord users manage NBA Top Shot trade listings. Users can create listings " \
                   "explaining which set they are looking for or trading. Listings are stored in the system and " \
                   "available to search. Users can check others' listing to find an exchange partner.\n" \
                   "Each user can hold *at most 5 listing posts*, creating extra posts will remove old posts " \
                   "automatically.\n" \
                   "Each post can be sent to connected Discord servers *once every 30 minutes.*\n\n" \
                   "*Please do not abuse this system.*\n\n"


class BaseExchangeView(BaseView):
    def __init__(self, service, user, d_username):
        super(BaseExchangeView, self).__init__(user['id'])
        self.service = service
        self.user = user
        self.d_username = d_username

    def back_to_menu(self):
        return EXCHANGE_MESSAGE, ExchangeMainView(self.service, self.user, self.d_username)


class ExchangeMenuButton(discord.ui.Button['Menu']):
    def __init__(self, row=4):
        super(ExchangeMenuButton, self).__init__(style=discord.ButtonStyle.success, label='Menu', row=row)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: BaseExchangeView = self.view
        message, new_view = view.back_to_menu()
        await interaction.response.edit_message(content=message, view=new_view)


class SelectSeriesButton(discord.ui.Button['SelectSeries']):
    def __init__(self, league, series, style, row):
        super(SelectSeriesButton, self).__init__(style=style, label=f"{league} {series}", row=row)
        self.league = league
        self.series = series

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AbstractExchangeSelectSetView = self.view
        view.select_series(self.league, self.series)
        await interaction.response.edit_message(content=view.message, view=view)


class SelectSetMenu(discord.ui.Select):
    def __init__(self, sets):
        super(SelectSetMenu, self).__init__()
        self.append_option(discord.SelectOption(label="<-- BACK TO MENU", value="menu"))
        for sid in sets:
            self.append_option(discord.SelectOption(label=EXCHANGE_SET_NAMES[int(sid)], value=sid))

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AbstractExchangeSelectSetView = self.view
        selection = interaction.data.get('values')[0]
        if selection == "menu":
            message, new_view = view.back_to_menu()
            await interaction.response.edit_message(content=message, view=new_view)
            return

        await view.select_set(selection, interaction)


class SelectTierButton(discord.ui.Button['SelectTier']):
    def __init__(self, tier, style, row):
        super(SelectTierButton, self).__init__(style=style, label=tier, row=row)
        self.tier = tier

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AbstractExchangeSelectSetView = self.view
        view.select_tier(self.tier)
        await interaction.response.edit_message(content=view.message, view=view)


class AbstractExchangeSelectSetView(BaseExchangeView):
    SELECT_SET_MESSAGE = "**SELECT SET**\n\n" \
                         "**Step 1.** Select a set\n" \
                         "**Step 2.** Add details about your trade, examples but not limited to \n" \
                         "a) player names: Luka, Lively\n" \
                         "b) serials: 3-digits\n" \
                         "c) general info: any dupes"

    def __init__(self, service, user, d_username, listing: Listing | None = None):
        super(AbstractExchangeSelectSetView, self).__init__(service, user, d_username)
        self.listing: Listing = listing
        self.league = ""
        self.series = ""
        self.tier = ""
        self.set_id = 0

        self.menu_button = ExchangeMenuButton(4)
        self.add_item(self.menu_button)

        self.dynamic_items: List[discord.ui.Button] = []
        for series in EXCHANGE_SETS['NBA']:
            button = SelectSeriesButton('NBA', series, discord.ButtonStyle.blurple, int(len(self.dynamic_items) / 3))
            self.add_item(button)
            self.dynamic_items.append(button)
        for series in EXCHANGE_SETS['WNBA']:
            button = SelectSeriesButton('WNBA', series, discord.ButtonStyle.gray, int(len(self.dynamic_items) / 3))
            self.add_item(button)
            self.dynamic_items.append(button)

        self.message = "**SELECT SERIES**"

    def select_series(self, league, series):
        self.league = league
        self.series = series
        for button in self.dynamic_items:
            self.remove_item(button)
        self.dynamic_items = []

        if EXCHANGE_SETS[self.league][self.series]['count'] <= 19:
            self.remove_item(self.menu_button)

            sets = {}
            for tier in EXCHANGE_SETS[self.league][self.series]['tiers']:
                sets.update(EXCHANGE_SETS[self.league][self.series]['tiers'][tier])
            self.add_item(SelectSetMenu(sets))
            self.message = self.SELECT_SET_MESSAGE
        else:
            button = SelectTierButton("Common", discord.ButtonStyle.gray, 0)
            self.add_item(button)
            self.dynamic_items.append(button)

            button = SelectTierButton("Fandom", discord.ButtonStyle.green, 0)
            self.add_item(button)
            self.dynamic_items.append(button)

            button = SelectTierButton("Rare", discord.ButtonStyle.blurple, 1)
            self.add_item(button)
            self.dynamic_items.append(button)

            button = SelectTierButton("Legendary", discord.ButtonStyle.red, 1)
            self.add_item(button)
            self.dynamic_items.append(button)
            self.message = "**SELECT TIER**"

    async def select_set(self, sid, interaction):
        pass

    def add_info(self, info) -> [str, discord.ui.View]:
        return "", self

    def select_tier(self, tier):
        self.tier = tier
        for button in self.dynamic_items:
            self.remove_item(button)
        self.dynamic_items = []
        self.remove_item(self.menu_button)

        self.add_item(SelectSetMenu(EXCHANGE_SETS[self.league][self.series]['tiers'][self.tier]))
        self.message = self.SELECT_SET_MESSAGE


class AddInfoModal(discord.ui.Modal, title='Add trade details'):
    info = discord.ui.TextInput(label="Info about your trade (<= 256 characters)", required=False)

    def __init__(self, view):
        super(AddInfoModal, self).__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        info = str(self.info).strip()
        if len(info) > 256:
            info = info[:256]

        message, new_view = self.view.add_info(info)
        await interaction.response.edit_message(content=message, view=new_view)


class LookingForSetView(AbstractExchangeSelectSetView):
    async def select_set(self, sid, interaction):
        self.set_id = int(sid)
        await interaction.response.send_modal(AddInfoModal(self))

    def add_info(self, info) -> [str, discord.ui.View]:
        self.listing.set_lf(self.set_id, info)
        view = ListingDetailView(self.service, self.user, self.d_username, self.listing)
        return view.message, view


class ForTradeSetView(AbstractExchangeSelectSetView):
    async def select_set(self, sid, interaction):
        self.set_id = int(sid)
        await interaction.response.send_modal(AddInfoModal(self))

    def add_info(self, info) -> [str, discord.ui.View]:
        self.listing.set_ft(self.set_id, info)
        view = ListingDetailView(self.service, self.user, self.d_username, self.listing)
        return view.message, view


class SearchLookingForView(AbstractExchangeSelectSetView):
    SELECT_SET_MESSAGE = "**SELECT SET**\n\n" \
                         "Select a set that other users are looking for..."

    async def select_set(self, sid, interaction):
        self.set_id = int(sid)
        listings = []
        if self.set_id in self.service.lf_sets:
            for lid in self.service.lf_sets[self.set_id]:
                li = self.service.lf_sets[self.set_id][lid]
                if li.user_id != self.user_id:
                    listings.append(li)

        new_view = ListingsView(self.service, self.user, self.d_username, listings)
        await interaction.response.edit_message(content=new_view.message, view=new_view)


class SearchForTradeView(AbstractExchangeSelectSetView):
    SELECT_SET_MESSAGE = "**SELECT SET**\n\n" \
                         "Select a set that other users are listing for trade..."

    async def select_set(self, sid, interaction):
        self.set_id = int(sid)
        listings = []
        if self.set_id in self.service.ft_sets:
            for lid in self.service.ft_sets[self.set_id]:
                li = self.service.ft_sets[self.set_id][lid]
                if li.user_id != self.user_id:
                    listings.append(li)

        new_view = ListingsView(self.service, self.user, self.d_username, listings)
        await interaction.response.edit_message(content=new_view.message, view=new_view)


class ExchangeListingsButton(discord.ui.Button['Listings']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="My Listings", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.view_listings(interaction.user.id)

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeNewLookingForButton(discord.ui.Button['NewLookFor']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Create New Looking For (LF)", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.new_lf()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeNewForTradeButton(discord.ui.Button['NewForTrade']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Create New For Trade (FT)", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.new_ft()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeSearchLookingForButton(discord.ui.Button['SearchLookingFor']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Search Looking For (LF)", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.search_lf()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeSearchForTradeButton(discord.ui.Button['SearchForTrade']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Search For Trade (FT)", row=4)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.search_ft()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeMainView(BaseExchangeView):
    def __init__(self, service, user, d_username):
        super(ExchangeMainView, self).__init__(service, user, d_username)
        self.add_item(ExchangeListingsButton())
        self.add_item(ExchangeNewLookingForButton())
        self.add_item(ExchangeNewForTradeButton())
        self.add_item(ExchangeSearchLookingForButton())
        self.add_item(ExchangeSearchForTradeButton())

    def new_lf(self):
        listing = Listing.new_empty(self.user_id, self.d_username, self.user['topshot_username'])
        view = LookingForSetView(self.service, self.user, self.d_username, listing)
        return view.message, view

    def new_ft(self):
        listing = Listing.new_empty(self.user_id, self.d_username, self.user['topshot_username'])
        view = ForTradeSetView(self.service, self.user, self.d_username, listing)
        return view.message, view

    def search_lf(self):
        view = SearchLookingForView(self.service, self.user, self.d_username)
        return view.message, view

    def search_ft(self):
        view = SearchForTradeView(self.service, self.user, self.d_username)
        return view.message, view

    def view_listings(self, uid):
        if uid not in self.service.user_listings:
            return "User doesn't have any listing", self

        listings = self.service.user_listings[uid]
        if len(listings) == 0:
            return "User doesn't have any listing", self

        view = ListingsView(self.service, self.user, self.d_username, listings)
        return view.message, view


class ExchangeListingLookingForButton(discord.ui.Button['ListingLF']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Edit Looking For (LF)", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingDetailView = self.view
        message, new_view = view.edit_lf()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingForTradeButton(discord.ui.Button['ListingFT']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Edit For Trade (FT)", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingDetailView = self.view
        message, new_view = view.edit_ft()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingInfoButton(discord.ui.Button['ListingInfo']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Edit Note", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingDetailView = self.view
        await interaction.response.send_modal(view.edit_info())


class ExchangeListingPostButton(discord.ui.Button['ListingPost']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Post", row=4)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingDetailView = self.view

        await interaction.response.edit_message(content=f"{view.message}\nPosting in progress...\n", view=view)
        followup = interaction.followup

        message, new_view = await view.post()
        await followup.edit_message(interaction.message.id, content=message, view=new_view)


class ExchangeListingCheckListingsButton(discord.ui.Button['ListingCheckListings']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="User's All Listings", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingDetailView = self.view
        message, new_view = view.view_listings()

        await interaction.response.edit_message(content=message, view=new_view)


class ListingDetailView(BaseExchangeView):
    def __init__(self, service, user, d_username, listing):
        super(ListingDetailView, self).__init__(service, user, d_username)
        self.listing = listing
        self.__update_message()

        if user['id'] == listing.user_id:
            self.add_item(ExchangeListingLookingForButton())
            self.add_item(ExchangeListingForTradeButton())
            self.add_item(ExchangeListingInfoButton())
            self.add_item(ExchangeListingPostButton())
            if listing.id != INVALID_ID:
                self.add_item(ExchangeListingCheckListingsButton())
        else:
            self.message += f"\nCompare: " \
                            f"<https://tsgo.app/compare/{self.user['topshot_username']}+{self.listing.ts_username}>"
            self.add_item(ExchangeListingCheckListingsButton())

        self.add_item(ExchangeMenuButton(4))

    def __update_message(self):
        self.message = f"**LISTING DETAILS**\n\n{self.listing}"
        if self.user_id == self.listing.user_id:
            self.message += f"\nClick 'Post' to send message to channels and save this listing."

    def edit_lf(self):
        view = LookingForSetView(self.service, self.user, self.d_username, self.listing.copy())
        return view.message, view

    def edit_ft(self):
        view = ForTradeSetView(self.service, self.user, self.d_username, self.listing.copy())
        return view.message, view

    def edit_info(self):
        return AddInfoModal(self)

    def add_info(self, info):
        self.listing.set_note(info)
        self.__update_message()
        return self.message, self

    async def post(self):
        is_first_post = self.listing.id == INVALID_ID
        posted, msg = await self.service.post(self.listing)
        if posted and is_first_post:
            self.add_item(ExchangeListingCheckListingsButton())

        return self.message + f"\n{msg}", self

    def view_listings(self):
        view = ListingsView(self.service, self.user, self.d_username,
                            self.service.user_listings[self.listing.user_id])
        return view.message, view


class SelectListingMenu(discord.ui.Select):
    def __init__(self, listings: List[Listing], has_prev=False, has_next=False):
        super(SelectListingMenu, self).__init__()
        self.append_option(discord.SelectOption(label="<-- BACK TO MENU", value="menu"))
        if has_prev:
            self.append_option(discord.SelectOption(label="<- PREV PAGE", value="prev"))
        for li in listings:
            self.append_option(discord.SelectOption(label=f"#{li.id}", value=li.id))
        if has_next:
            self.append_option(discord.SelectOption(label="NEXT PAGE ->", value="next"))

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ListingsView = self.view
        selection = interaction.data.get('values')[0]
        if selection == "menu":
            message, new_view = view.back_to_menu()
            await interaction.response.edit_message(content=message, view=new_view)
            return
        if selection == "prev":
            message, new_view = view.prev_page()
            await interaction.response.edit_message(content=message, view=new_view)
            return
        if selection == "next":
            message, new_view = view.next_page()
            await interaction.response.edit_message(content=message, view=new_view)
            return

        lid = int(selection)
        message, new_view = view.select(int(lid))
        await interaction.response.edit_message(content=message, view=new_view)


class ListingsView(BaseExchangeView):
    def __init__(self, service, user, d_username, listings: List[Listing]):
        super(ListingsView, self).__init__(service, user, d_username)
        self.listings = listings

        self.start = 0
        self.end = 0

        self.message = "**SELECT A LISTING TO VIEW DETAIL**\n\n"
        if len(self.listings) == 0:
            self.message += "No available listings"
        else:
            for i in range(self.start, len(listings)):
                li = self.listings[i]
                l_msg = f"**#{li.id}** {li}\n"
                self.end = i + 1
                if len(self.message) + len(l_msg) < 1950:
                    self.message += l_msg
                else:
                    self.end -= 1
                    break

        self.menu = SelectListingMenu(self.listings[self.start:self.end], self.start > 0, self.end < len(self.listings))
        self.add_item(self.menu)

    def prev_page(self):
        self.message = ""
        self.end = self.start
        for i in range(self.end - 1, -1, -1):
            li = self.listings[i]
            l_msg = f"**#{li.id}** {li}\n"
            self.start = i
            if len(self.message) + len(l_msg) < 1950:
                self.message = l_msg + self.message
            else:
                self.start += 1
                break

        self.message = "**SELECT A LISTING TO VIEW DETAIL**\n\n" + self.message

        self.remove_item(self.menu)
        self.menu = SelectListingMenu(self.listings[self.start:self.end], self.start > 0, True)
        self.add_item(self.menu)

        return self.message, self

    def next_page(self):
        self.message = "**SELECT A LISTING TO VIEW DETAIL**\n\n"
        self.start = self.end
        for i in range(self.start, len(self.listings)):
            li = self.listings[i]
            l_msg = f"**#{li.id}** {li}\n"
            self.end = i + 1
            if len(self.message) + len(l_msg) < 1950:
                self.message += l_msg
            else:
                self.end -= 1
                break

        self.remove_item(self.menu)
        self.menu = SelectListingMenu(self.listings[self.start:self.end], True, self.end < len(self.listings))
        self.add_item(self.menu)

        return self.message, self

    def select(self, lid: int):
        for i in range(self.start, self.end):
            if self.listings[i].id == lid:
                view = ListingDetailView(self.service, self.user, self.d_username, self.listings[i])
                return view.message, view
