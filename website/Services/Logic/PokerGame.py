# website/Services/logic/PokerGame.py

import uuid
import time
import random
import collections
import asyncio
import logging
from typing import Optional, List, Dict, Set, Generator, Any


class GameError(Exception):
    pass

class EndGameException(Exception):
    pass


class Card:
    RANKS = {
        2: "2",
        3: "3",
        4: "4",
        5: "5",
        6: "6",
        7: "7",
        8: "8",
        9: "9",
        10: "10",
        11: "J",
        12: "Q",
        13: "K",
        14: "A",
    }
    SUITS = {
        0: "Spades",
        1: "Clubs",
        2: "Diamonds",
        3: "Hearts",
    }

    def __init__(self, rank: int, suit: int):
        if rank not in Card.RANKS:
            raise ValueError("Invalid card rank")
        if suit not in Card.SUITS:
            raise ValueError("Invalid card suit")
        self._value = (rank << 2) + suit

    @property
    def rank(self) -> int:
        return self._value >> 2

    @property
    def suit(self) -> int:
        return self._value & 3

    def __lt__(self, other):
        return int(self) < int(other)

    def __eq__(self, other):
        return int(self) == int(other)

    def __int__(self):
        return self._value

    def dto(self):
        return {
            "rank": self.rank,
            "suit": self.suit,
            "rank_name": Card.RANKS[self.rank],
            "suit_name": Card.SUITS[self.suit],
        }


class Deck:
    def __init__(self, lowest_rank: int):
        self._cards: List[Card] = [Card(rank, suit) for rank in range(lowest_rank, 15) for suit in range(0, 4)]
        self._discard: List[Card] = []
        random.shuffle(self._cards)

    def pop_cards(self, num_cards=1) -> List[Card]:
        new_cards = []
        if len(self._cards) < num_cards:
            new_cards = self._cards
            self._cards = self._discard
            self._discard = []
            random.shuffle(self._cards)
        return new_cards + [self._cards.pop() for _ in range(num_cards - len(new_cards))]

    def push_cards(self, discard: List[Card]):
        self._discard += discard


class DeckFactory:
    def __init__(self, lowest_rank: int):
        self._lowest_rank = lowest_rank

    def create_deck(self):
        return Deck(self._lowest_rank)


class Player:
    def __init__(self, id: str, name: str, money: float):
        self._id: str = id
        self._name: str = name
        self._money: float = money

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def money(self) -> float:
        return self._money

    def dto(self):
        return {
            "id": self.id,
            "name": self.name,
            "money": self.money
        }

    def take_money(self, money: float):
        if money > self._money:
            raise ValueError("Player does not have enough money")
        if money < 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money -= money

    def add_money(self, money: float):
        if money <= 0.0:
            raise ValueError("Money has to be a positive amount")
        self._money += money

    def __str__(self):
        return f"player {self._id}"


class MessageFormatError(Exception):
    def __init__(self, attribute=None, desc=None, expected=None, found=None):
        message = "Invalid message received."
        if attribute:
            message += " Invalid message attribute {}.".format(attribute)
            if expected is not None and found is not None:
                message += " '{}' expected, found '{}'.".format(expected, found)
        if desc:
            message += " " + desc
        Exception.__init__(self, message)

    @staticmethod
    def validate_message_type(message, expected):
        if "message_type" not in message:
            raise MessageFormatError(attribute="message_type", desc="Attribute is missing")
        elif message["message_type"] == "error":
            if "error" in message:
                raise MessageFormatError(desc="Error received from the remote host: '{}'".format(message['error']))
            else:
                raise MessageFormatError(desc="Unknown error received from the remote host")
        if message["message_type"] != expected:
            raise MessageFormatError(attribute="message_type", expected=expected, found=message["message_type"])

class Cards:
    def __init__(self, cards: List[Card], lowest_rank=2):
        self._sorted = sorted(cards, key=int, reverse=True)
        self._lowest_rank: int = lowest_rank

    def _group_by_ranks(self) -> Dict[int, List[Card]]:
        ranks = collections.defaultdict(list)
        for card in self._sorted:
            ranks[card.rank].append(card)
        return ranks

    def _x_sorted_list(self, x) -> List[List[Card]]:
        return sorted(
            (cards for cards in self._group_by_ranks().values() if len(cards) == x),
            key=lambda cards: cards[0].rank,
            reverse=True
        )

    def _get_straight(self, sorted_cards):
        if len(sorted_cards) < 5:
            return None

        straight = [sorted_cards[0]]

        for i in range(1, len(sorted_cards)):
            if sorted_cards[i].rank == sorted_cards[i - 1].rank - 1:
                straight.append(sorted_cards[i])
                if len(straight) == 5:
                    return straight
            elif sorted_cards[i].rank != sorted_cards[i - 1].rank:
                straight = [sorted_cards[i]]

        # Ace can wrap around (A can be low)
        if len(straight) == 4 and sorted_cards[0].rank == 14 and straight[-1].rank == self._lowest_rank:
            straight.append(sorted_cards[0])
            return straight
        return None

    def quads(self):
        quads_list = self._x_sorted_list(4)
        try:
            return self._merge_with_cards(quads_list[0])[0:5]
        except IndexError:
            return None

    def full_house(self):
        trips_list = self._x_sorted_list(3)
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(trips_list[0] + pair_list[0])[0:5]
        except IndexError:
            return None

    def trips(self):
        trips_list = self._x_sorted_list(3)
        try:
            return self._merge_with_cards(trips_list[0])[0:5]
        except IndexError:
            return None

    def two_pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0] + pair_list[1])[0:5]
        except IndexError:
            return None

    def pair(self):
        pair_list = self._x_sorted_list(2)
        try:
            return self._merge_with_cards(pair_list[0])[0:5]
        except IndexError:
            return None

    def straight(self):
        return self._get_straight(self._sorted)

    def flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            if len(suits[card.suit]) == 5:
                return suits[card.suit]
        return None

    def straight_flush(self):
        suits = collections.defaultdict(list)
        for card in self._sorted:
            suits[card.suit].append(card)
            if len(suits[card.suit]) >= 5:
                straight = self._get_straight(suits[card.suit])
                if straight:
                    return straight
        return None

    def no_pair(self):
        return self._sorted[0:5]

    def _merge_with_cards(self, score_cards: List[Card]):
        return score_cards + [card for card in self._sorted if card not in score_cards]


class Score:
    def __init__(self, category: int, cards: List[Card]):
        self._category: int = category
        self._cards: List[Card] = cards
        assert(len(cards) <= 5)

    @property
    def category(self) -> int:
        return self._category

    @property
    def cards(self) -> List[Card]:
        return self._cards

    def dto(self):
        return {
            "category": self.category,
            "cards": [card.dto() for card in self.cards]
        }


class TraditionalPokerScore(Score):
    NO_PAIR = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FULL_HOUSE = 5
    FLUSH = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8

    @property
    def strength(self) -> int:
        strength = self.category
        for offset in range(5):
            strength <<= 4
            try:
                strength += self.cards[offset].rank
            except IndexError:
                pass
        for offset in range(5):
            strength <<= 2
            try:
                strength += self.cards[offset].suit
            except IndexError:
                pass
        return strength

    def cmp(self, other):
        # Straight flush special handling
        if self.category == TraditionalPokerScore.STRAIGHT_FLUSH:
            if self._straight_is_max(self.cards) and self._straight_is_min(other.cards):
                return -1
            elif self._straight_is_min(self.cards) and self._straight_is_max(other.cards):
                return 1

        if self.strength < other.strength:
            return -1
        elif self.strength > other.strength:
            return 1
        else:
            return 0

    @staticmethod
    def _straight_is_min(straight_sequence) -> bool:
        return straight_sequence[4].rank == 14

    @staticmethod
    def _straight_is_max(straight_sequence) -> bool:
        return straight_sequence[0].rank == 14


class HoldemPokerScore(Score):
    NO_PAIR = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8

    @property
    def strength(self):
        strength = self.category
        for offset in range(5):
            strength <<= 4
            try:
                strength += self.cards[offset].rank
            except IndexError:
                pass
        return strength

    def cmp(self, other):
        if self.strength < other.strength:
            return -1
        elif self.strength > other.strength:
            return 1
        else:
            return 0


class ScoreDetector:
    def get_score(self, cards: List[Card]):
        raise NotImplementedError


class TraditionalPokerScoreDetector(ScoreDetector):
    def __init__(self, lowest_rank):
        self._lowest_rank = lowest_rank

    def get_score(self, cards):
        cards_obj = Cards(cards, self._lowest_rank)
        score_functions = [
            (TraditionalPokerScore.STRAIGHT_FLUSH,  cards_obj.straight_flush),
            (TraditionalPokerScore.QUADS,           cards_obj.quads),
            (TraditionalPokerScore.FULL_HOUSE,      cards_obj.full_house),
            (TraditionalPokerScore.FLUSH,           cards_obj.flush),
            (TraditionalPokerScore.STRAIGHT,        cards_obj.straight),
            (TraditionalPokerScore.TRIPS,           cards_obj.trips),
            (TraditionalPokerScore.TWO_PAIR,        cards_obj.two_pair),
            (TraditionalPokerScore.PAIR,            cards_obj.pair),
            (TraditionalPokerScore.NO_PAIR,         cards_obj.no_pair),
        ]

        for score_category, score_function in score_functions:
            score = score_function()
            if score:
                return TraditionalPokerScore(score_category, score)

        raise RuntimeError("Unable to detect the score")


class HoldemPokerScoreDetector(ScoreDetector):
    def get_score(self, cards):
        cards_obj = Cards(cards, 2)
        score_functions = [
            (HoldemPokerScore.STRAIGHT_FLUSH,   cards_obj.straight_flush),
            (HoldemPokerScore.QUADS,            cards_obj.quads),
            (HoldemPokerScore.FULL_HOUSE,       cards_obj.full_house),
            (HoldemPokerScore.FLUSH,            cards_obj.flush),
            (HoldemPokerScore.STRAIGHT,         cards_obj.straight),
            (HoldemPokerScore.TRIPS,            cards_obj.trips),
            (HoldemPokerScore.TWO_PAIR,         cards_obj.two_pair),
            (HoldemPokerScore.PAIR,             cards_obj.pair),
            (HoldemPokerScore.NO_PAIR,          cards_obj.no_pair),
        ]

        for score_category, score_function in score_functions:
            s = score_function()
            if s:
                return HoldemPokerScore(score_category, s)

        raise RuntimeError("Unable to detect the score")


class GamePlayers:
    def __init__(self, players: List[Player]):
        self._players: Dict[str, Player] = {player.id: player for player in players}
        self._player_ids: List[str] = [player.id for player in players]
        self._folder_ids: Set[str] = set()
        self._dead_player_ids: Set[str] = set()

    def fold(self, player_id: str):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        self._folder_ids.add(player_id)

    def remove(self, player_id: str):
        self.fold(player_id)
        self._dead_player_ids.add(player_id)

    def reset(self):
        self._folder_ids = set(self._dead_player_ids)

    def round(self, start_player_id: str, reverse=False) -> Generator[Player, None, None]:
        start_item = self._player_ids.index(start_player_id)
        step_multiplier = -1 if reverse else 1
        for i in range(len(self._player_ids)):
            next_item = (start_item + (i * step_multiplier)) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield self._players[player_id]

    def get(self, player_id: str) -> Player:
        try:
            return self._players[player_id]
        except KeyError:
            raise ValueError("Unknown player id")

    def get_next(self, dealer_id: str) -> Optional[Player]:
        if dealer_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if dealer_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_item = self._player_ids.index(dealer_id)
        for i in range(len(self._player_ids) - 1):
            next_index = (start_item + i + 1) % len(self._player_ids)
            next_id = self._player_ids[next_index]
            if next_id not in self._folder_ids:
                return self._players[next_id]
        return None

    def is_active(self, player_id: str) -> bool:
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        return player_id not in self._folder_ids

    def count_active(self) -> int:
        return len(self._player_ids) - len(self._folder_ids)

    def count_active_with_money(self) -> int:
        return len([player for player in self.active if player.money > 0])

    @property
    def all(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._dead_player_ids]

    @property
    def folders(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._folder_ids]

    @property
    def dead(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._dead_player_ids]

    @property
    def active(self) -> List[Player]:
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._folder_ids]


class GameScores:
    def __init__(self, score_detector: ScoreDetector):
        self._score_detector: ScoreDetector = score_detector
        self._players_cards: Dict[str, List[Card]] = {}
        self._shared_cards: List[Card] = []

    @property
    def shared_cards(self):
        return self._shared_cards

    def player_cards(self, player_id: str):
        return self._players_cards[player_id]

    def player_score(self, player_id: str):
        return self._score_detector.get_score(self._players_cards[player_id] + self._shared_cards)

    def assign_cards(self, player_id: str, cards: List[Card]):
        self._players_cards[player_id] = cards

    def add_shared_cards(self, cards):
        self._shared_cards += cards


class GamePots:
    class GamePot:
        def __init__(self):
            self._money = 0.0
            self._players: List[Player] = []

        def add_money(self, money: float):
            self._money += money

        def add_player(self, player: Player):
            self._players.append(player)

        @property
        def money(self) -> float:
            return self._money

        @property
        def players(self) -> List[Player]:
            return self._players

    def __init__(self, game_players: GamePlayers):
        self._game_players = game_players
        self._pots = []
        self._bets = {player.id: 0.0 for player in game_players.all}

    def __len__(self):
        return len(self._pots)

    def __getitem__(self, item):
        return self._pots[item]

    def __iter__(self):
        return iter(self._pots)

    def add_bets(self, bets: Dict[str, float]):
        for player in self._game_players.all:
            self._bets[player.id] += bets.get(player.id, 0.0)

        bets = dict(self._bets)
        players = sorted(self._game_players.all, key=lambda player: bets[player.id])
        self._pots = []
        spare_money = 0.0

        for i, player in enumerate(players):
            if not self._game_players.is_active(player.id):
                spare_money += bets[player.id]
                bets[player.id] = 0.0
            elif bets[player.id] > 0.0:
                pot_bet = bets[player.id]
                current_pot = GamePots.GamePot()
                current_pot.add_money(spare_money)
                spare_money = 0.0
                for j in range(i, len(players)):
                    if self._game_players.is_active(players[j].id):
                        current_pot.add_player(players[j])
                    current_pot.add_money(pot_bet)
                    bets[players[j].id] -= pot_bet
                self._pots.append(current_pot)

        if spare_money:
            raise ValueError("Invalid bets")


class GameEventDispatcher:
    def __init__(self, game_id: str, logger):
        self._subscribers: List['GameSubscriber'] = []
        self._game_id: str = game_id
        self._logger = logger

    def subscribe(self, subscriber: 'GameSubscriber'):
        self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: 'GameSubscriber'):
        self._subscribers.remove(subscriber)

    async def raise_event(self, event, event_data):
        event_data["message_type"] = "game-update"
        event_data["event"] = event
        event_data["game_id"] = self._game_id
        self._logger.debug(f"GAME: {self._game_id} EVENT: {event}\n{event_data}")
        await asyncio.gather(*(subscriber.game_event(event, event_data) for subscriber in self._subscribers))

    async def cards_assignment_event(self, player: Player, cards: List[Card], score: Score):
        await self.raise_event(
            "cards-assignment",
            {
                "target": player.id,
                "cards": [card.dto() for card in cards],
                "score": score.dto()
            }
        )

    async def pots_update_event(self, players: List[Player], pots: GamePots):
        await self.raise_event(
            "pots-update",
            {
                "pots": [
                    {
                        "money": pot.money,
                        "player_ids": [player.id for player in pot.players],
                    }
                    for pot in pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    async def winner_designation_event(self, players: List[Player], pot: GamePots.GamePot, winners: List[Player], money_split: float, upcoming_pots: GamePots):
        await self.raise_event(
            "winner-designation",
            {
                "pot": {
                    "money": pot.money,
                    "player_ids": [player.id for player in pot.players],
                    "winner_ids": [winner.id for winner in winners],
                    "money_split": money_split
                },
                "pots": [
                    {
                        "money": upcoming_pot.money,
                        "player_ids": [player.id for player in upcoming_pot.players]
                    }
                    for upcoming_pot in upcoming_pots
                ],
                "players": {player.id: player.dto() for player in players}
            }
        )

    async def bet_action_event(self, player: Player, min_bet: float, max_bet: float, bets: Dict[str, float], timeout: int, timeout_epoch: float):
        await self.raise_event(
            "player-action",
            {
                "action": "bet",
                "player": player.dto(),
                "min_bet": min_bet,
                "max_bet": max_bet,
                "allowed_to_bet": True,  
                "bets": bets,
                "timeout": timeout,
                "timeout_date": time.strftime("%Y-%m-%d %H:%M:%S+0000", time.gmtime(timeout_epoch))
            }
        )

    async def bet_event(self, player: Player, bet: float, bet_type: str, bets: Dict[str, float]):
        await self.raise_event(
            "bet",
            {
                "player": player.dto(),
                "bet": bet,
                "bet_type": bet_type,
                "bets": bets
            }
        )

    async def dead_player_event(self, player: Player):
        await self.raise_event(
            "dead-player",
            {
                "player": player.dto()
            }
        )

    async def fold_event(self, player: Player):
        await self.raise_event(
            "fold",
            {
                "player": player.dto()
            }
        )

    async def showdown_event(self, players: List[Player], scores: GameScores):
        await self.raise_event(
            "showdown",
            {
                "players": {
                    player.id: {
                        "cards": [card.dto() for card in scores.player_cards(player.id)],
                        "score": scores.player_score(player.id).dto(),
                    }
                    for player in players
                }
            }
        )


class GameSubscriber:
    async def game_event(self, event, event_data):
        raise NotImplementedError


class GameWinnersDetector:
    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def get_winners(self, players: List[Player], scores: GameScores) -> List[Player]:
        winners = []
        for player in players:
            if not self._game_players.is_active(player.id):
                continue
            if not winners:
                winners.append(player)
            else:
                score_diff = scores.player_score(player.id).cmp(scores.player_score(winners[0].id))
                if score_diff == 0:
                    winners.append(player)
                elif score_diff > 0:
                    winners = [player]
        return winners


class GameBetRounder:
    def __init__(self, game_players: GamePlayers):
        self._game_players: GamePlayers = game_players

    def _get_max_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
        try:
            highest_stake = max(
                player.money + bets[player.id]
                for player in self._game_players.round(dealer.id)
                if player is not dealer
            )
        except ValueError:
            return 0.0
        return min(highest_stake - bets[dealer.id], dealer.money)

    def _get_min_bet(self, dealer: Player, bets: Dict[str, float]) -> float:
        return min(max(bets.values()) - bets[dealer.id], dealer.money)

    # async def bet_round(self, dealer_id: str, bets: Dict[str, float], get_bet_function, on_bet_function=None) -> Optional[Player]:
    #     players_round = list(self._game_players.round(dealer_id))
    #     if len(players_round) == 0:
    #         raise GameError("No active players in this game")
    #
    #     dealer = players_round[0]
    #     for k, player in enumerate(players_round):
    #         if player.id not in bets:
    #             bets[player.id] = 0
    #         if bets[player.id] < 0 or (k > 0 and bets[player.id] < bets[players_round[k - 1].id]):
    #             raise ValueError("Invalid bets dictionary")
    #
    #     best_player = None
    #     while dealer is not None and dealer != best_player:
    #         next_player = self._game_players.get_next(dealer.id)
    #         max_bet = self._get_max_bet(dealer, bets)
    #         min_bet = self._get_min_bet(dealer, bets)
    #
    #         if max_bet == 0.0:
    #             bet = 0.0
    #         else:
    #             bet = await get_bet_function(player=dealer, min_bet=min_bet, max_bet=max_bet, bets=bets)
    #
    #         if bet is None:
    #             self._game_players.remove(dealer.id)
    #         elif bet == -1:
    #             self._game_players.fold(dealer.id)
    #         else:
    #             if bet < min_bet or bet > max_bet:
    #                 raise ValueError("Invalid bet")
    #             dealer.take_money(bet)
    #             bets[dealer.id] += bet
    #             if best_player is None or bet > min_bet:
    #                 best_player = dealer
    #
    #         if on_bet_function:
    #             await on_bet_function(dealer, bet, min_bet, max_bet, bets)
    #
    #         dealer = next_player
    #     return best_player

    async def bet_round(self, dealer_id: str, bets: Dict[str, float], get_bet_function, on_bet_function=None) -> Optional[Player]:
        players_round = list(self._game_players.round(dealer_id))
        if len(players_round) == 0:
            raise GameError("No active players in this game")

        dealer = players_round[0]
        for k, player in enumerate(players_round):
            if player.id not in bets:
                bets[player.id] = 0
            if bets[player.id] < 0 or (k > 0 and bets[player.id] < bets[players_round[k - 1].id]):
                raise ValueError("Invalid bets dictionary")

        for player_id, bet_amount in bets.items():
            player = self._game_players._players[player_id]
            if not player:
                continue
            max_bet = self._get_max_bet(player, bets)
            min_bet = self._get_min_bet(player, bets)

            if max_bet == 0.0:
                bet = 0.0
            else:
                bet = await get_bet_function(player=player, min_bet=min_bet, max_bet=max_bet, bets=bets)

            if bet is None:
                self._game_players.remove(player.id)
            elif bet == -1:
                self._game_players.fold(player.id)
            else:
                if bet < min_bet or bet > max_bet:
                    raise ValueError("Invalid bet")
                player.take_money(bet)
                # bets[player.id] += bet
            if on_bet_function:
                await on_bet_function(player, bet, min_bet, max_bet, bets)
        return


class GameBetHandler:
    def __init__(self, game_players: GamePlayers, bet_rounder: GameBetRounder, event_dispatcher: GameEventDispatcher, bet_timeout: int, timeout_tolerance: int, wait_after_round: int):
        self._game_players: GamePlayers = game_players
        self._bet_rounder: GameBetRounder = bet_rounder
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._bet_timeout: int = bet_timeout
        self._timeout_tolerance: int = timeout_tolerance
        self._wait_after_round: int = wait_after_round

    def any_bet(self, bets: Dict[str, float]) -> bool:
        return any(bets[k] > 0 for k in bets)

    async def bet_round(self, dealer_id: str, bets: Dict[str, float], pots: GamePots):
        best_player = await self._bet_rounder.bet_round(dealer_id, bets, self.get_bet, self.on_bet)
        await asyncio.sleep(self._wait_after_round)
        if self.any_bet(bets):
            pots.add_bets(bets)
            await self._event_dispatcher.pots_update_event(self._game_players.active, pots)

        return best_player

    async def get_bet(self, player, min_bet: float, max_bet: float, bets: Dict[str, float]) -> Optional[int]:
        timeout_epoch = time.time() + self._bet_timeout
        await self._event_dispatcher.bet_action_event(
            player=player,
            min_bet=min_bet,
            max_bet=max_bet,
            bets=bets,
            timeout=self._bet_timeout,
            timeout_epoch=timeout_epoch
        )
        return await self.receive_bet(player, min_bet, max_bet, bets, timeout_epoch)

    async def receive_bet(self, player, min_bet, max_bet, bets, timeout_epoch) -> Optional[int]:
        try:
            message = {
                "message_type": "bet",
                "bet": bets[player.id],
            }
            # message = await player.recv_message(temp_message, timeout_epoch=timeout_epoch)
            MessageFormatError.validate_message_type(message, "bet")

            if "bet" not in message:
                raise MessageFormatError(attribute="bet", desc="Attribute is missing")

            try:
                bet = round(float(message["bet"]))
            except ValueError:
                raise MessageFormatError(attribute="bet", desc=f"'{message['bet']}' is not a number")
            else:
                if bet != -1 and (bet < min_bet or bet > max_bet):
                    raise MessageFormatError(attribute="bet", desc=f"Bet out of range. min: {min_bet} max: {max_bet}, actual: {bet}")
                return bet
        except (MessageFormatError, asyncio.TimeoutError) as e:
            await player.send_message({"message_type": "error", "error": str(e)})
            return None

    async def on_bet(self, player: Player, bet: float, min_bet: float, max_bet: float, bets: Dict[str, float]):
        def get_bet_type(bet):
            if bet is None:
                return "dead"
            if bet == -1:
                return "fold"
            if bet == 0:
                return "check"
            elif bet == player.money:
                return "all-in"
            elif bet == min_bet:
                return "call"
            else:
                return "raise"

        if bet is None:
            await self._event_dispatcher.dead_player_event(player)
        elif bet == -1:
            await self._event_dispatcher.fold_event(player)
        else:
            await self._event_dispatcher.bet_event(player, bet, get_bet_type(bet), bets)


class GameFactory:
    def create_game(self, players: List[Player]):
        raise NotImplementedError


class PokerGame:
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 30
    WAIT_AFTER_CARDS_ASSIGNMENT = 1
    WAIT_AFTER_BET_ROUND = 1
    WAIT_AFTER_SHOWDOWN = 2
    WAIT_AFTER_WINNER_DESIGNATION = 5

    def __init__(self, id: str, game_players: GamePlayers, event_dispatcher: GameEventDispatcher, deck_factory: DeckFactory, score_detector: ScoreDetector):
        self._id: str = id
        self._game_players: GamePlayers = game_players
        self._event_dispatcher: GameEventDispatcher = event_dispatcher
        self._deck_factory: DeckFactory = deck_factory
        self._score_detector: ScoreDetector = score_detector
        self._bet_handler: GameBetHandler = self._create_bet_handler()
        self._winners_detector: GameWinnersDetector = self._create_winners_detector()

    @property
    def event_dispatcher(self) -> GameEventDispatcher:
        return self._event_dispatcher

    async def play_hand(self, dealer_id: str):
        raise NotImplementedError

    def _create_bet_handler(self) -> GameBetHandler:
        return GameBetHandler(
            game_players=self._game_players,
            bet_rounder=GameBetRounder(self._game_players),
            event_dispatcher=self._event_dispatcher,
            bet_timeout=self.BET_TIMEOUT,
            timeout_tolerance=self.TIMEOUT_TOLERANCE,
            wait_after_round=self.WAIT_AFTER_BET_ROUND
        )

    def _create_winners_detector(self) -> GameWinnersDetector:
        return GameWinnersDetector(self._game_players)

    def _create_pots(self) -> GamePots:
        return GamePots(self._game_players)

    def _create_scores(self) -> GameScores:
        return GameScores(self._score_detector)

    async def _assign_cards(self, number_of_cards: int, dealer_id: str, deck: Deck, scores: GameScores):
        for player in self._game_players.round(dealer_id):
            p_cards = deck.pop_cards(number_of_cards)
            scores.assign_cards(player.id, p_cards)
            await self._send_player_score(player, scores)
        await asyncio.sleep(self.WAIT_AFTER_CARDS_ASSIGNMENT)

    async def _send_player_score(self, player: Player, scores: GameScores):
        await self._event_dispatcher.cards_assignment_event(
            player=player,
            cards=scores.player_cards(player.id),
            score=scores.player_score(player.id)
        )

    def _game_over_detection(self):
        if self._game_players.count_active() < 2:
            raise EndGameException

    async def _detect_winners(self, pots: GamePots, scores: GameScores):
        for i, pot in enumerate(reversed(pots)):
            winners = self._winners_detector.get_winners(pot.players, scores)
            try:
                money_split = round(pot.money / len(winners))
            except ZeroDivisionError:
                raise GameError("No players left")
            else:
                for winner in winners:
                    winner.add_money(money_split)

                await self._event_dispatcher.winner_designation_event(
                    players=self._game_players.active,
                    pot=pot,
                    winners=winners,
                    money_split=money_split,
                    upcoming_pots=pots[(i + 1):]
                )
                await asyncio.sleep(self.WAIT_AFTER_WINNER_DESIGNATION)

    async def _showdown(self, scores: GameScores):
        await self._event_dispatcher.showdown_event(self._game_players.active, scores)
        await asyncio.sleep(self.WAIT_AFTER_SHOWDOWN)


class HoldemPokerGameEventDispatcher(GameEventDispatcher):
    async def new_game_event(self, game_id, players, dealer_id, big_blind, small_blind):
        await self.raise_event(
            "new-game",
            {
                "game_id": game_id,
                "game_type": "texas-holdem",
                "players": [player.dto() for player in players],
                "dealer_id": dealer_id,
                "big_blind": big_blind,
                "small_blind": small_blind,
            },
        )

    async def game_over_event(self):
        await self.raise_event("game-over", {})

    async def shared_cards_event(self, cards):
        await self.raise_event(
            "shared-cards",
            {
                "cards": [card.dto() for card in cards],
            },
        )


class HoldemPokerGame(PokerGame):
    TIMEOUT_TOLERANCE = 2
    BET_TIMEOUT = 30
    WAIT_AFTER_FLOP_TURN_RIVER = 1

    def __init__(self, big_blind, small_blind, logger: Optional[logging.Logger] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._big_blind = big_blind
        self._small_blind = small_blind
        self.scores = None
        self.pots = None
        self.deck = None
        self.current_stage = "pre-flop"
        self._logger = logger or logging.getLogger(__name__)

    async def _add_shared_cards(self, new_shared_cards, scores):
        await self._event_dispatcher.shared_cards_event(new_shared_cards)
        scores.add_shared_cards(new_shared_cards)
        await asyncio.sleep(self.WAIT_AFTER_FLOP_TURN_RIVER)

    async def _collect_blinds(self, dealer_id):
        for player in self._game_players.active:
            if player.money < self._big_blind:
                await self._event_dispatcher.dead_player_event(player)
                self._game_players.remove(player.id)

        if self._game_players.count_active() < 2:
            raise GameError("Not enough players")

        active_players = list(self._game_players.round(dealer_id))
        bets = {}

        sb_player = active_players[-2]
        sb_player.take_money(self._small_blind)
        bets[sb_player.id] = self._small_blind
        await self._event_dispatcher.bet_event(
            player=sb_player,
            bet=self._small_blind,
            bet_type="blind",
            bets=bets,
        )

        bb_player = active_players[-1]
        bb_player.take_money(self._big_blind)
        bets[bb_player.id] = self._big_blind
        await self._event_dispatcher.bet_event(
            player=bb_player,
            bet=self._big_blind,
            bet_type="blind",
            bets=bets,
        )

        return bets

    async def play_hand_preflop(self, dealer_id):
        self._logger.info(f"Starting hand in game {self._id} with dealer {dealer_id}")

        self._game_players.reset()
        self.deck = self._deck_factory.create_deck()
        self.scores = self._create_scores()
        self.pots = self._create_pots()

        await self._event_dispatcher.new_game_event(
            game_id=self._id,
            players=self._game_players.active,
            dealer_id=dealer_id,
            big_blind=self._big_blind,
            small_blind=self._small_blind,
        )
        self._logger.info("New game event sent.")

        try:
            # Collect blinds
            blind_bets = await self._collect_blinds(dealer_id)
            self._logger.info(f"Blinds collected: {blind_bets}")
            bets = blind_bets

            # Pre-flop
            await self._assign_cards(2, dealer_id, self.deck, self.scores)
            self._logger.info("Pre-flop cards assigned.")

            await self._bet_handler.bet_round(dealer_id, bets, self.pots)
            self._logger.info("Pre-flop betting round completed.")

            await self._add_shared_cards(self.deck.pop_cards(3), self.scores)
            self._logger.info("Flop cards added.")
            self.current_stage = "flop"

        except EndGameException:
            self._logger.info("Game ended due to insufficient players.")
        except Exception as e:
            self._logger.exception(f"Error during play_hand: {e}")
        finally:
            self._logger.info(f"Game {self._id} pre-flop betting round completed.")

    async def handle_bet_event(self, player_id, bets):
        player = self._game_players._players[player_id]

        if not player:
            raise Exception

        min_bet = self._bet_handler._bet_rounder._get_min_bet(player, bets)
        max_bet = self._bet_handler._bet_rounder._get_max_bet(player, bets)

        timeout_epoch = time.time() + self._bet_handler._bet_timeout
        await self._event_dispatcher.bet_action_event(
            player=player,
            min_bet=min_bet,
            max_bet=max_bet,
            bets=bets,
            timeout=self._bet_handler._bet_timeout,
            timeout_epoch=timeout_epoch
        )

    async def play_hand_flop(self, dealer_id, bets):
        self._logger.info(f"Starting flop in game {self._id} with dealer {dealer_id}")
        try:
            await self._bet_handler.bet_round(dealer_id, bets, self.pots)
            self._logger.info("Flop betting round completed.")
            await self._add_shared_cards(self.deck.pop_cards(1), self.scores)
            self._logger.info("Turn card added.")
            self.current_stage = "turn"
        except EndGameException:
            self._logger.info("Game ended due to insufficient players.")
        except Exception as e:
            self._logger.exception(f"Error during play_hand: {e}")
        finally:
            self._logger.info(f"Game {self._id} flop betting round completed.")


    async def play_hand_turn(self, dealer_id, bets):
        self._logger.info(f"Starting turn in game {self._id} with dealer {dealer_id}")
        try:
            await self._bet_handler.bet_round(dealer_id, bets, self.pots)
            self._logger.info("Turn betting round completed.")
            await self._add_shared_cards(self.deck.pop_cards(1), self.scores)
            self._logger.info("River card added.")
            self.current_stage = "river"
        except EndGameException:
            self._logger.info("Game ended due to insufficient players.")
        except Exception as e:
            self._logger.exception(f"Error during play_hand: {e}")
        finally:
            self._logger.info(f"Game {self._id} turn betting round completed.")


    async def play_hand_river(self, dealer_id, bets):
            self._logger.info(f"Starting flop in game {self._id} with dealer {dealer_id}")
            try:
                await self._bet_handler.bet_round(dealer_id, bets, self.pots)
                self._logger.info("River betting round completed.")
                self.current_stage = "pre-flop"

                # Showdown
                if self._game_players.count_active() > 1:
                    await self._showdown(self.scores)
                    self._logger.info("Showdown completed.")

                await self._detect_winners(self.pots, self.scores)
                self._logger.info("Winners detected.")

            except EndGameException:
                self._logger.info("Game ended due to insufficient players.")
                await self._detect_winners(self.pots, self.scores)
            except Exception as e:
                self._logger.exception(f"Error during play_hand: {e}")
            finally:
                await self._event_dispatcher.game_over_event()
                self._logger.info(f"Game {self._id} hand completed.")


    async def play_hand(self, dealer_id):
        self._logger.info(f"Starting hand in game {self._id} with dealer {dealer_id}")

        self._game_players.reset()
        deck = self._deck_factory.create_deck()
        scores = self._create_scores()
        pots = self._create_pots()

        await self._event_dispatcher.new_game_event(
            game_id=self._id,
            players=self._game_players.active,
            dealer_id=dealer_id,
            big_blind=self._big_blind,
            small_blind=self._small_blind,
        )
        self._logger.info("New game event sent.")

        try:
            # Collect blinds
            blind_bets = await self._collect_blinds(dealer_id)
            self._logger.info(f"Blinds collected: {blind_bets}")

            bets = blind_bets

            # Pre-flop
            await self._assign_cards(2, dealer_id, deck, scores)
            self._logger.info("Pre-flop cards assigned.")

            await self._bet_handler.bet_round(dealer_id, bets, pots)
            self._logger.info("Pre-flop betting round completed.")


            # Flop
            await self._add_shared_cards(deck.pop_cards(3), scores)
            self._logger.info("Flop cards added.")

            await self._bet_handler.bet_round(dealer_id, {}, pots)
            self._logger.info("Flop betting round completed.")

            # Turn
            await self._add_shared_cards(deck.pop_cards(1), scores)
            self._logger.info("Turn card added.")
            await self._bet_handler.bet_round(dealer_id, {}, pots)
            self._logger.info("Turn betting round completed.")

            # River
            await self._add_shared_cards(deck.pop_cards(1), scores)
            self._logger.info("River card added.")
            await self._bet_handler.bet_round(dealer_id, {}, pots)
            self._logger.info("River betting round completed.")

            # Showdown
            if self._game_players.count_active() > 1:
                await self._showdown(scores)
                self._logger.info("Showdown completed.")

            await self._detect_winners(pots, scores)
            self._logger.info("Winners detected.")

        except EndGameException:
            self._logger.info("Game ended due to insufficient players.")

            await self._detect_winners(pots, scores)
        except Exception as e:
            self._logger.exception(f"Error during play_hand: {e}")
        finally:
            await self._event_dispatcher.game_over_event()
            self._logger.info(f"Game {self._id} hand completed.")



class HoldemPokerGameFactory(GameFactory):
    def __init__(self, big_blind: float, small_blind: float, logger, game_subscribers: Optional[List['GameSubscriber']] = None):
        self._big_blind = big_blind
        self._small_blind = small_blind
        self._logger = logger
        self._game_subscribers = game_subscribers or []

    def create_game(self, players: List[Player]):
        game_id = str(uuid.uuid4())
        event_dispatcher = HoldemPokerGameEventDispatcher(
            game_id=game_id, logger=self._logger
        )
        for subscriber in self._game_subscribers:
            event_dispatcher.subscribe(subscriber)

        self._logger.debug(f"Creating HoldemPokerGame with game_id {game_id}")
        # Ensure no trailing comma after score_detector argument
        return HoldemPokerGame(
            self._big_blind,
            self._small_blind,
            id=game_id,
            game_players=GamePlayers(players),
            event_dispatcher=event_dispatcher,
            deck_factory=DeckFactory(2),
            score_detector=HoldemPokerScoreDetector()
        )