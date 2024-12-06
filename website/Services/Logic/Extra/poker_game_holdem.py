# # website/Services/Logic/poker_game_holdem.py

# import uuid
# from typing import Optional, List
# import asyncio

# from .deck import DeckFactory
# from .player import Player
# from .poker_game import (
#     PokerGame,
#     GameFactory,
#     GameError,
#     EndGameException,
#     GamePlayers,
#     GameEventDispatcher,
#     GameSubscriber,
# )
# from .score_detector import HoldemPokerScoreDetector


# class HoldemPokerGameFactory(GameFactory):
#     def __init__(
#         self,
#         big_blind: float,
#         small_blind: float,
#         logger,
#         game_subscribers: Optional[List[GameSubscriber]] = None,
#     ):
#         self._big_blind = big_blind
#         self._small_blind = small_blind
#         self._logger = logger
#         self._game_subscribers = game_subscribers or []

#     def create_game(self, players: List[Player]):
#         game_id = str(uuid.uuid4())

#         event_dispatcher = HoldemPokerGameEventDispatcher(
#             game_id=game_id, logger=self._logger
#         )
#         for subscriber in self._game_subscribers:
#             event_dispatcher.subscribe(subscriber)

#         return HoldemPokerGame(
#             self._big_blind,
#             self._small_blind,
#             id=game_id,
#             game_players=GamePlayers(players),
#             event_dispatcher=event_dispatcher,
#             deck_factory=DeckFactory(2),
#             score_detector=HoldemPokerScoreDetector(),
#         )


# class HoldemPokerGameEventDispatcher(GameEventDispatcher):
#     async def new_game_event(
#         self, game_id, players, dealer_id, big_blind, small_blind
#     ):
#         await self.raise_event(
#             "new-game",
#             {
#                 "game_id": game_id,
#                 "game_type": "texas-holdem",
#                 "players": [player.dto() for player in players],
#                 "dealer_id": dealer_id,
#                 "big_blind": big_blind,
#                 "small_blind": small_blind,
#             },
#         )

#     async def game_over_event(self):
#         await self.raise_event("game-over", {})

#     async def shared_cards_event(self, cards):
#         await self.raise_event(
#             "shared-cards",
#             {
#                 "cards": [card.dto() for card in cards],
#             },
#         )


# class HoldemPokerGame(PokerGame):
#     TIMEOUT_TOLERANCE = 2
#     BET_TIMEOUT = 30

#     WAIT_AFTER_FLOP_TURN_RIVER = 1

#     def __init__(self, big_blind, small_blind, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self._big_blind = big_blind
#         self._small_blind = small_blind

#     async def _add_shared_cards(self, new_shared_cards, scores):
#         await self._event_dispatcher.shared_cards_event(new_shared_cards)
#         scores.add_shared_cards(new_shared_cards)
#         await asyncio.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

#     async def _collect_blinds(self, dealer_id):
#         # Remove players with insufficient funds
#         for player in self._game_players.active:
#             if player.money < self._big_blind:
#                 await self._event_dispatcher.dead_player_event(player)
#                 self._game_players.remove(player.id)

#         if self._game_players.count_active() < 2:
#             raise GameError("Not enough players")

#         active_players = list(self._game_players.round(dealer_id))
#         bets = {}

#         sb_player = active_players[-2]
#         sb_player.take_money(self._small_blind)
#         bets[sb_player.id] = self._small_blind

#         await self._event_dispatcher.bet_event(
#             player=sb_player,
#             bet=self._small_blind,
#             bet_type="blind",
#             bets=bets,
#         )

#         bb_player = active_players[-1]
#         bb_player.take_money(self._big_blind)
#         bets[bb_player.id] = self._big_blind

#         await self._event_dispatcher.bet_event(
#             player=bb_player,
#             bet=self._big_blind,
#             bet_type="blind",
#             bets=bets,
#         )

#         return bets

#     async def play_hand(self, dealer_id):
#         self._game_players.reset()
#         deck = self._deck_factory.create_deck()
#         scores = self._create_scores()
#         pots = self._create_pots()

#         await self._event_dispatcher.new_game_event(
#             game_id=self._id,
#             players=self._game_players.active,
#             dealer_id=dealer_id,
#             big_blind=self._big_blind,
#             small_blind=self._small_blind,
#         )

#         try:
#             # Collect blinds
#             blind_bets = await self._collect_blinds(dealer_id)
#             bets = blind_bets

#             # Pre-flop
#             await self._assign_cards(2, dealer_id, deck, scores)
#             await self._bet_handler.bet_round(dealer_id, bets, pots)

#             # Flop
#             await self._add_shared_cards(deck.pop_cards(3), scores)
#             await self._bet_handler.bet_round(dealer_id, {}, pots)

#             # Turn
#             await self._add_shared_cards(deck.pop_cards(1), scores)
#             await self._bet_handler.bet_round(dealer_id, {}, pots)

#             # River
#             await self._add_shared_cards(deck.pop_cards(1), scores)
#             await self._bet_handler.bet_round(dealer_id, {}, pots)

#             # Showdown
#             if self._game_players.count_active() > 1:
#                 await self._showdown(scores)
#             await self._detect_winners(pots, scores)
#         except EndGameException:
#             await self._detect_winners(pots, scores)
#         finally:
#             await self._event_dispatcher.game_over_event()
