from typing import List

import discord

from service.exchange.listing import Listing, EXCHANGE_SETS, EXCHANGE_SET_NAMES
from service.views import BaseView

EXCHANGE_MESSAGE = ""


class BaseExchangeView(BaseView):
    def __init__(self, user, d_username):
        super(BaseExchangeView, self).__init__(user['id'])
        self.user = user
        self.d_username = d_username

    def back_to_menu(self):
        return EXCHANGE_MESSAGE, ExchangeMainView(self.user, self.d_username)


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

        await interaction.response.send_modal(view.select_set(selection))


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

    def __init__(self, user, listing: Listing):
        super(AbstractExchangeSelectSetView, self).__init__(user, listing.d_username)
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

    def select_set(self, sid) -> discord.ui.Modal:
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
    def select_set(self, sid) -> discord.ui.Modal:
        self.set_id = int(sid)
        return AddInfoModal(self)

    def add_info(self, info) -> [str, discord.ui.View]:
        self.listing.set_lf(self.set_id, info)
        view = ExchangeListingView(self.user, self.d_username, self.listing)
        return view.message, view


class ForTradeSetView(AbstractExchangeSelectSetView):
    def select_set(self, sid) -> discord.ui.Modal:
        self.set_id = int(sid)
        return AddInfoModal(self)

    def add_info(self, info) -> [str, discord.ui.View]:
        self.listing.set_ft(self.set_id, info)
        view = ExchangeListingView(self.user, self.d_username, self.listing)
        return view.message, view


class ExchangeNewLookingForButton(discord.ui.Button['NewLookFor']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Create New Looking For (LF)", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.new_lf()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeNewForTradeButton(discord.ui.Button['NewForTrade']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.red, label="Create New For Trade (FT)", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeMainView = self.view
        message, new_view = view.new_ft()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeMainView(BaseExchangeView):
    def __init__(self, user, d_username):
        super(ExchangeMainView, self).__init__(user, d_username)
        self.add_item(ExchangeNewLookingForButton())
        self.add_item(ExchangeNewForTradeButton())

    def new_lf(self):
        listing = Listing.new_empty(self.user_id, self.d_username, self.user['topshot_username'])
        view = LookingForSetView(self.user, listing)
        return view.message, view

    def new_ft(self):
        listing = Listing.new_empty(self.user_id, self.d_username, self.user['topshot_username'])
        view = ForTradeSetView(self.user, listing)
        return view.message, view


class ExchangeListingLookingForButton(discord.ui.Button['ListingLF']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Edit Looking For (LF)", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        message, new_view = view.edit_lf()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingForTradeButton(discord.ui.Button['ListingFT']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="Edit For Trade (FT)", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        message, new_view = view.edit_ft()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingInfoButton(discord.ui.Button['ListingInfo']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.gray, label="Add note", row=2)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        await interaction.response.send_modal(view.edit_info())


class ExchangeListingPostButton(discord.ui.Button['ListingPost']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Post", row=3)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        message, new_view = view.post()

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingCompareButton(discord.ui.Button['ListingCompare']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="Compare Collection", row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        message, new_view = view.compare(interaction.user)

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingCheckListingsButton(discord.ui.Button['ListingCheckListings']):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="User's Other Listings", row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: ExchangeListingView = self.view
        message, new_view = view.compare(interaction.user)

        await interaction.response.edit_message(content=message, view=new_view)


class ExchangeListingView(BaseExchangeView):
    def __init__(self, user, d_username, listing):
        super(ExchangeListingView, self).__init__(user, d_username)
        self.listing = listing
        self.__update_message()

        if user['id'] == listing.user_id:
            self.add_item(ExchangeListingLookingForButton())
            self.add_item(ExchangeListingForTradeButton())
            self.add_item(ExchangeListingInfoButton())
            self.add_item(ExchangeListingPostButton())
        else:
            self.add_item(ExchangeListingCompareButton())

    def __update_message(self):
        self.message = f"**LISTING DETAILS**\n\n{self.listing}" \
                       f"Click 'Post' to send message to channels and save this listing."

    def edit_lf(self):
        view = LookingForSetView(self.user, self.listing)
        return view.message, view

    def edit_ft(self):
        view = ForTradeSetView(self.user, self.listing)
        return view.message, view

    def edit_info(self):
        return AddInfoModal(self)

    def add_info(self, info):
        self.listing.set_note(info)
        self.__update_message()
        return self.message, self

    def post(self):
        return self.message, self

    def compare(self, user):
        return self.message, self


class AbstractExchangeListingsView(BaseExchangeView):
    def __init__(self, user, d_username, listings: List[Listing]):
        super(AbstractExchangeListingsView, self).__init__(user, d_username)
        self.listings = listings
        self.offset = 0
