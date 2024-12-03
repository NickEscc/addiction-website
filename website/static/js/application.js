// website/static/js/application.js

PyPoker = {

    socket: null,

    Game: {
        gameId: null,

        numCards: null,

        scoreCategories: null,

        getCurrentPlayerId: function() {
            return $('#current-player').attr('data-player-id');
        },

        getCurrentPlayerName: function() {
            return $('#current-player').attr('data-player-name');
        },

        getCurrentPlayerMoney: function() {
            return $('#current-player').attr('data-player-money');
        },

        setCard: function($card, rank, suit) {
            $card.each(function() {
                let x = 0;
                let y = 0;


                let url, width, height;

                if ($(this).hasClass('small')) {
                    url = staticUrl + "images/cards-small.png";
                    width = 24;
                    height = 40;
                }
                else if ($(this).hasClass('medium')) {
                    url = staticUrl + "images/cards-medium.png";
                    width = 45;
                    height = 75;
                }
                else {
                    url = staticUrl + "images/cards-large.png";
                    width = 75;
                    height = 125;
                }

                if (rank !== undefined || suit !== undefined) {
                    switch (suit) {
                        case 0:
                            // Spades
                            x -= width;
                            y -= height;
                            break;
                        case 1:
                            // Clubs
                            y -= height;
                            break;
                        case 2:
                            // Diamonds
                            x -= width;
                            break;
                        case 3:
                            // Hearts
                            break;
                        default:
                            console.error("Invalid suit:", suit);
                            return;
                    }

                    if (rank == 14) {
                        rank = 1;
                    }
                    else if (rank < 1 || rank > 13) {
                        console.error("Invalid rank:", rank);
                        return;
                    }

                    x -= (rank - 1) * 2 * width + width;
                }

                $(this).css('background-position', x + "px " + y + "px");
                $(this).css('background-image', 'url(' + url + ')');
            });
        },

        newGame: function(message) {
            PyPoker.Game.gameId = message.game_id;

            if (message.game_type == "traditional") {
                PyPoker.Game.numCards = 5;
                PyPoker.Game.scoreCategories = {
                    0: "Highest card",
                    1: "Pair",
                    2: "Double pair",
                    3: "Three of a kind",
                    4: "Straight",
                    5: "Full house",
                    6: "Flush",
                    7: "Four of a kind",
                    8: "Straight flush"
                };
            }
            else {
                PyPoker.Game.numCards = 2;
                PyPoker.Game.scoreCategories = {
                    0: "Highest card",
                    1: "Pair",
                    2: "Double pair",
                    3: "Three of a kind",
                    4: "Straight",
                    5: "Flush",
                    6: "Full house",
                    7: "Four of a kind",
                    8: "Straight flush"
                };
            }

            $('#game-wrapper').addClass(message.game_type);

            for (let key in message.players) {
                let playerId = message.players[key].id;
                let $player = $('#players .player[data-player-id=' + playerId + ']');
                let $cards = $('.cards', $player);
                for (let i = 0; i < PyPoker.Game.numCards; i++) {
                    $cards.append('<div class="card small" data-key="' + i + '"></div>');
                }

                if (playerId == message.dealer_id) {
                    $player.addClass('dealer');
                }
                if (playerId == PyPoker.Game.getCurrentPlayerId()) {
                    $player.addClass('current');
                }
            }
            $('#current-player').show();
        },

        gameOver: function(message) {
            $('.player').removeClass('fold winner looser dealer');
            $('.player .cards').empty();
            $('#pots').empty();
            $('#shared-cards').empty();
            $('#players .player .bet-wrapper').empty();
            $('#current-player').hide();
        },

        updatePlayer: function(player) {
            let $player = $('#players .player[data-player-id=' + player.id + ']');
            $('.player-money', $player).text('$' + parseInt(player.money));
            $('.player-name', $player).text(player.name);
        },

        playerFold: function(player) {
            $('#players .player[data-player-id=' + player.id + ']').addClass('fold');
        },

        updatePlayers: function(players) {
            for (let k in players) {
                PyPoker.Game.updatePlayer(players[k]);
            }
        },

        updatePlayersBet: function(bets) {
            // Remove existing bets
            $('#players .player .bet-wrapper').empty();
            if (bets !== undefined) {
                for (let playerId in bets) {
                    let bet = parseInt(bets[playerId]);
                    if (bet > 0) {
                        let $bet = $('<div class="bet"></div>');
                        $bet.text('$' + bet);
                        $('#players .player[data-player-id=' + playerId + '] .bet-wrapper').append($bet);
                    }
                }
            }
        },

        setPlayerCards: function(cards, $cards) {
            for (let cardKey in cards) {
                let $card = $('.card[data-key=' + cardKey + ']', $cards);
                PyPoker.Game.setCard(
                    $card,
                    cards[cardKey][0],
                    cards[cardKey][1]
                );
            }
        },

        handlePong: function(message) {
            // Handle pong response
            console.log("Received pong from server.");
            // Implement logic to update player's last pong time if needed
        },

        updatePlayersCards: function(players) {
            for (let playerId in players) {
                let $cards = $('.player[data-player-id=' + playerId + '] .cards');
                PyPoker.Game.setPlayerCards(players[playerId].cards, $cards);
            }
        },

        updateCurrentPlayerCards: function(cards, score) {
            let $cards = $('.player[data-player-id=' + PyPoker.Game.getCurrentPlayerId() + '] .cards');
            PyPoker.Game.setPlayerCards(cards, $cards);
            $('#current-player .cards .category').text(PyPoker.Game.scoreCategories[score.category]);
        },

        addSharedCards: function(cards) {
            for (let cardKey in cards) {
                let $card = $('<div class="card medium"></div>');
                PyPoker.Game.setCard($card, cards[cardKey][0], cards[cardKey][1]);
                $('#shared-cards').append($card);
            }
        },

        updatePots: function(pots) {
            $('#pots').empty();
            for (let potIndex in pots) {
                $('#pots').append($(
                    '<div class="pot">' +
                    '$' + parseInt(pots[potIndex].money) +
                    '</div>'
                ));
            }
        },

        setWinners: function(pot) {
            $('#players .player').addClass('fold').removeClass('winner looser');
            $('#players .player .cards').empty();
            $('#pots').empty();
            $('#shared-cards').empty();
            $('#players .player .bet-wrapper').empty();
            $('#current-player').hide();
        },

        changeCards: function(player, numCards) {
            let $player = $('#players .player[data-player-id=' + player.id + ']');

            let $cards = $('.card', $player).slice(-numCards);

            $cards.slideUp(1000).slideDown(1000);
        },

        onGameUpdate: function(message) {
            PyPoker.Player.resetControls();
            PyPoker.Player.resetTimers();

            switch (message.event) {
                case 'new-game':
                    PyPoker.Game.newGame(message);
                    break;
                case 'cards-assignment':
                    if (message.target === PyPoker.Game.getCurrentPlayerId()) {
                        PyPoker.Game.updateCurrentPlayerCards(message.cards, message.score);
                    } else {
                        PyPoker.Game.updatePlayersCards(message.players);
                    }
                    break;
                case 'game-over':
                    PyPoker.Game.gameOver();
                    break;
                case 'fold':
                    PyPoker.Game.playerFold(message.player);
                    break;
                case 'bet':
                    PyPoker.Game.updatePlayer(message.player);
                    PyPoker.Game.updatePlayersBet(message.bets);
                    break;
                case 'pots-update':
                    PyPoker.Game.updatePlayers(message.players);
                    PyPoker.Game.updatePots(message.pots);
                    PyPoker.Game.updatePlayersBet();  // Reset the bets
                    break;
                case 'player-action':
                    PyPoker.Player.onPlayerAction(message);
                    break;
                case 'dead-player':
                    PyPoker.Game.playerFold(message.player);
                    break;
                case 'cards-change':
                    PyPoker.Game.changeCards(message.player, message.num_cards);
                    break;
                case 'shared-cards':
                    PyPoker.Game.addSharedCards(message.cards);
                    break;
                case 'winner-designation':
                    PyPoker.Game.updatePlayers(message.players);
                    PyPoker.Game.updatePots(message.pots);
                    PyPoker.Game.setWinners(message.pot);
                    break;
                case 'showdown':
                    PyPoker.Game.updatePlayersCards(message.players);
                    break;
                case 'ping':
                    PyPoker.Player.handlePing(message);  // Handle ping
                    break;
                case 'pong':
                    PyPoker.Player.handlePong(message);  // Handle pong
                    break;
                default:
                    console.warn("Unknown message type:", message.message_type);
            }
        }
    },

    Logger: {
        log: function(text) {
            let $p0 = $('#game-status p[data-key="0"]');
            let $p1 = $('#game-status p[data-key="1"]');
            let $p2 = $('#game-status p[data-key="2"]');
            let $p3 = $('#game-status p[data-key="3"]');
            let $p4 = $('#game-status p[data-key="4"]');

            $p4.text($p3.text());
            $p3.text($p2.text());
            $p2.text($p1.text());
            $p1.text($p0.text());
            $p0.text(text);
        }
    },

    Player: {
        betMode: false,

        cardsChangeMode: false,

        resetTimers: function() {
            // Reset timers
            let $activeTimers = $('.timer.active');
            $activeTimers.TimeCircles().destroy();
            $activeTimers.removeClass('active');
        },

        resetControls: function() {
            // Reset controls
            PyPoker.Player.setCardsChangeMode(false);
            PyPoker.Player.disableBetMode();
        },

        sliderHandler: function(value) {
            if (value == 0) {
                $('#bet-cmd').attr("value", "Check");
            }
            else {
                $('#bet-cmd').attr("value", "$" + parseInt(value));
            }
            $('#bet-input').val(value);
        },

        enableBetMode: function(message) {
            PyPoker.Player.betMode = true;

            if (!message.min_score || $('#current-player').data('allowed-to-bet')) {
                // Set-up slider
                $('#bet-input').slider({
                    'min': parseInt(message.min_bet),
                    'max': parseInt(message.max_bet),
                    'value': parseInt(message.min_bet),
                    'formatter': PyPoker.Player.sliderHandler
                }).slider('setValue', parseInt(message.min_bet));

                // Fold control
                if (message.min_score) {
                    $('#fold-cmd').val('Pass')
                        .removeClass('btn-danger')
                        .addClass('btn-warning');
                }
                else {
                    $('#fold-cmd').val('Fold')
                        .addClass('btn-danger')
                        .removeClass('btn-warning');
                }

                $('#fold-cmd-wrapper').show();
                $('#bet-input-wrapper').show();
                $('#bet-cmd-wrapper').show();
                $('#no-bet-cmd-wrapper').hide();
            }

            else {
                $('#fold-cmd-wrapper').hide();
                $('#bet-input-wrapper').hide();
                $('#bet-cmd-wrapper').hide();
                $('#no-bet-cmd-wrapper').show();
            }

            $('#bet-controls').show();
        },

        disableBetMode: function() {
            $('#bet-controls').hide();
        },

        setCardsChangeMode: function(changeMode) {
            PyPoker.Player.cardsChangeMode = changeMode;

            if (changeMode) {
                $('#cards-change-controls').show();
            }
            else {
                $('#cards-change-controls').hide();
                $('#current-player .card.selected').removeClass('selected');
            }
        },

        onPlayerAction: function(message) {
            let isCurrentPlayer = message.player.id == PyPoker.Game.getCurrentPlayerId();

            switch (message.action) {
                case 'bet':
                    if (isCurrentPlayer) {
                        PyPoker.Player.onBet(message);
                    }
                    break;
                case 'cards-change':
                    if (isCurrentPlayer) {
                        PyPoker.Player.onChangeCards(message);
                    }
                    break;
            }

            let timeout = (Date.parse(message.timeout_date) - Date.now()) / 1000;

            let $timers = $('.player[data-player-id=' + message.player.id + '] .timer');
            $timers.data('timer', timeout);
            $timers.TimeCircles({
                "start": true,
                "animation": "smooth",
                "bg_width": 1,
                "fg_width": 0.05,
                "count_past_zero": false,
                "time": {
                    "Days": { show: false },
                    "Hours": { show: false },
                    "Minutes": { show: false },
                    "Seconds": { show: true }
                }
            });
            $timers.addClass('active');
        },

        onBet: function(message) {
            PyPoker.Player.enableBetMode(message);
            $("html, body").animate({ scrollTop: $(document).height() }, "slow");
        },

        onChangeCards: function(message) {
            PyPoker.Player.setCardsChangeMode(true);
            $("html, body").animate({ scrollTop: $(document).height() }, "slow");
        },

        handlePong: function(message) {
            // Handle pong response
            console.log("Received pong from server.");
            // Implement logic to update player's last pong time if needed
        },

        handlePing: function(message) {
            console.log("Received ping from server:", message);
            // Respond with pong
            PyPoker.socket.send(JSON.stringify({'message_type': 'pong'}));
            console.log("Sent pong to server.");
        }
    },

    Room: {
        roomId: null,

        createPlayer: function(player=undefined) {
            var $playerInfo = $('<div class="player-info"></div>');
            var $player = $('<div class="player"></div>');

            if (player) {
                var isCurrentPlayer = player.id == PyPoker.Game.getCurrentPlayerId();

                var $playerName = $('<p class="player-name"></p>');
                $playerName.text(isCurrentPlayer ? 'You' : player.name);

                var $playerMoney = $('<p class="player-money"></p>');
                $playerMoney.text('$' + parseInt(player.money));

                $playerInfo.append($playerName);
                $playerInfo.append($playerMoney);

                if (isCurrentPlayer) {
                    $player.addClass('current');
                }

                $player.attr('data-player-id', player.id);
            } else {
                // Empty seat
                $playerInfo.text('Empty Seat');
            }

            $player.append($playerInfo);
            $player.append($('<div class="bet-wrapper"></div>'));
            $player.append($('<div class="cards"></div>'));
            $player.append($('<div class="timer"></div>'));

            return $player;
        },

        destroyRoom: function() {
            PyPoker.Game.gameOver();
            PyPoker.Room.roomId = null;
            $('#players').empty();
        },

        onPlayerRemoved: function(message) {
            var playerId = message.player_id;
            $('#players .player[data-player-id="' + playerId + '"]').remove();
            PyPoker.Logger.log("Player removed: " + message.player_id);
        },

        onPlayerAdded: function(message) {
            // Log the addition for debugging
            PyPoker.Logger.log("Player added: " + message.player_name);
            
            // Re-initialize the room to reflect the new player
            PyPoker.Room.initRoom(message);
        },

        initRoom: function(message) {
            // Clear existing players
            $('#players').empty();
            var playerIds = message.player_ids;
            var players = message.players;
        
            // Iterate through player IDs and render them in seats
            playerIds.forEach(function(playerId, index) {
                var $seat = $('<div class="seat"></div>');
                $seat.attr('data-key', index);
        
                if (playerId) {
                    var player = players[playerId];
                    var $playerElement = PyPoker.Room.createPlayer({
                        id: player.player_id || player.id, // Adjusted to match server keys
                        name: player.player_name || player.name,
                        money: player.player_money || player.money
                    });
                    $seat.append($playerElement);
                    $seat.attr('data-player-id', playerId);
                } else {
                    // Empty seat
                    $seat.append(PyPoker.Room.createPlayer());
                    $seat.attr('data-player-id', null);
                }
        
                $('#players').append($seat);
            });
        
            PyPoker.Logger.log("Room initialized with players.");
        },

        onRoomUpdate: function(message) {
            console.log("Received room update:", message);

            // Validate message structure
            if (!message || !message.player_ids || typeof message.players !== 'object') {
                console.error("Invalid message structure:", message);
                PyPoker.Logger.log("Error: Invalid room update message.");
                return;
            }
        
            // Re-initialize the room with the updated data
            PyPoker.Room.initRoom(message);
        },
        
    },

    init: function() {
        // Ensure roomId is available from data attributes or other means
        if (typeof roomId === 'undefined' || !roomId) {
            console.error("roomId is not defined.");
            return;
        }

        // Prevent multiple WebSocket connections
        if (PyPoker.socket && PyPoker.socket.readyState === WebSocket.OPEN) {
            console.warn("WebSocket is already open.");
            return;
        }
            
        let wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";
        let connectionChannel = encodeURIComponent("texas_holdem_" + roomId);


        PyPoker.socket = new WebSocket(
            wsScheme + window.location.host + "/ws/Services/" + connectionChannel + "/"
        );

        console.log("Initializing WebSocket connection...");

        PyPoker.socket.onopen = function() {
            console.log('WebSocket connected');
            PyPoker.Logger.log('Connected :)');

            // Send a 'join' message to inform the server of the active player
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'join',
                'player_id': PyPoker.Game.getCurrentPlayerId(),
                'player_name': PyPoker.Game.getCurrentPlayerName(),
                'player_money': PyPoker.Game.getCurrentPlayerMoney()
            }));
            console.log("Sent 'join' message to server.");
        };

        PyPoker.socket.onclose = function() {
            console.error('WebSocket disconnected');
            PyPoker.Logger.log('Disconnected :(');
            PyPoker.Room.destroyRoom();
            PyPoker.socket = null;
        };

        PyPoker.socket.onmessage = function(message) {
            let data;
            try {
                data = JSON.parse(message.data);
            } catch (e) {
                console.error("Failed to parse message:", message.data);
                return;
            }

            console.log("Received message:", data);

            switch (data.message_type) {
                case 'ping':
                    PyPoker.Player.handlePing(data);  // Handle ping
                    break;
                case 'pong':
                    PyPoker.Player.handlePong(data);  // Handle pong
                    break;
                case 'connect':
                    PyPoker.onConnect(data);
                    break;
                case 'disconnect':
                    PyPoker.onDisconnect(data);
                    break;
                case 'room-update':
                    PyPoker.Room.onRoomUpdate(data);
                    break;
                case 'player-added':
                    PyPoker.Room.onPlayerAdded(data);
                    break;
                case 'game-update':
                    PyPoker.Game.onGameUpdate(data);
                    break;
                case 'player-removed':
                    PyPoker.Room.onPlayerRemoved(data);
                    break;
                case 'error':
                    PyPoker.Logger.log(data.error);
                    break;
                default:
                    console.warn("Unknown message type:", data.message_type);
            }

            PyPoker.Player.setCardsChangeMode(false);
            PyPoker.Player.disableBetMode();
        };

        // Event handlers for game commands
        $('#cards-change-cmd').click(function() {
            let discards = [];
            $('#current-player .card.selected').each(function() {
                discards.push($(this).data('key'));
            });
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'cards-change',
                'cards': discards
            }));
            PyPoker.Player.setCardsChangeMode(false);
        });

        $('#fold-cmd').click(function() {
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'bet',
                'bet': -1
            }));
            PyPoker.Player.disableBetMode();
        });

        $('#no-bet-cmd').click(function() {
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'bet',
                'bet': 0
            }));
            PyPoker.Player.disableBetMode();
        });

        $('#bet-cmd').click(function() {
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'bet',
                'bet': $('#bet-input').val()
            }));
            PyPoker.Player.disableBetMode();
        });

        PyPoker.Player.setCardsChangeMode(false);
        PyPoker.Player.disableBetMode();
    },


    onConnect: function(message) {
        PyPoker.Logger.log("Connection established with poker server.");
        // Since player information is already embedded in HTML, no need to set data attributes here
        PyPoker.Logger.log("Player ID: " + message.player_id);
        PyPoker.Logger.log("Player Name: " + message.player_name);
    },

    onDisconnect: function(message) {
        // Optional: handle disconnect
        PyPoker.Logger.log("Disconnected from poker server.");
    },

    onError: function(message) {
        PyPoker.Logger.log(message.error);
    }
}

window.addEventListener('beforeunload', function() {
    if (PyPoker.socket) {
        PyPoker.socket.close();
    }
});

$(document).ready(function() {
    if ($('#game-wrapper').length) 
        PyPoker.init();
});

// website/static/js/application.js

