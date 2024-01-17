from service.fastbreak.fastbreak import FastBreak


class FastBreakService:
    def __init__(self):
        self.formatted_schedule = ""
        self.fb: FastBreak | None = None
        self.players = {}
        self.player_ids = []
