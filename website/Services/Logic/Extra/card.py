# # website/Services/Logic/card.py

# class Card:
#     RANKS = {
#         2: "2",
#         3: "3",
#         4: "4",
#         5: "5",
#         6: "6",
#         7: "7",
#         8: "8",
#         9: "9",
#         10: "10",
#         11: "J",
#         12: "Q",
#         13: "K",
#         14: "A",
#     }
#     SUITS = {
#         0: "Spades",
#         1: "Clubs",
#         2: "Diamonds",
#         3: "Hearts",
#     }

#     def __init__(self, rank: int, suit: int):
#         if rank not in Card.RANKS:
#             raise ValueError("Invalid card rank")
#         if suit not in Card.SUITS:
#             raise ValueError("Invalid card suit")
#         self._value = (rank << 2) + suit

#     @property
#     def rank(self) -> int:
#         return self._value >> 2

#     @property
#     def suit(self) -> int:
#         return self._value & 3

#     def __lt__(self, other):
#         return int(self) < int(other)

#     def __eq__(self, other):
#         return int(self) == int(other)

#     def __int__(self):
#         return self._value

#     def dto(self):
#         return {
#             "rank": self.rank,
#             "suit": self.suit,
#             "rank_name": Card.RANKS[self.rank],
#             "suit_name": Card.SUITS[self.suit],
#         }
