import time
import unittest
from typing import Generator
from unittest import mock

from ..Services.Logic.Extra.channel import Channel
from ..Services.Logic.Extra.player_server import PlayerServer
from ..Services.Logic.Extra.game_server import GameServer, ConnectedPlayer
#python -m unittest website.test.test_game_server


class GameServerTest(unittest.TestCase):

    class NoOpChannel(Channel):
        def recv_message(self, timeout_epoch=None):
            return None

        def send_message(self, message):
            pass

    class GameServerStub(GameServer):
        def new_players(self) -> Generator[ConnectedPlayer, None, None]:
            for i in range(500):
                yield ConnectedPlayer(
                    PlayerServer(
                        GameServerTest.NoOpChannel(),
                        id="player-{}".format(i),
                        name="Player {}".format(i),
                        money=1000.0,
                        logger=mock.Mock()
                    )
                )

    def test_500_players_connection(self):
        time_start = time.time()
        server = GameServerTest.GameServerStub(mock.Mock())
        server.start()
        time_diff = time.time() - time_start
        self.assertLess(time_diff, 0.3, "It took {} seconds to connect 500 players. Too slow!".format(time_diff))


if __name__ == '__main__':
    unittest.main()