// website/static/js/application.js

var PyPoker = {

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

                var staticUrl = window.staticUrl || '/static/';
                let url, width, height;

                if ($(this).hasClass('small')) {
                    url = staticUrl + "cards-small.png";
                    width = 24;
                    height = 40;
                } else if ($(this).hasClass('medium')) {
                    url = staticUrl + "cards-medium.png";
                    width = 45;
                    height = 75;
                } else {
                    url = staticUrl + "cards-large.png";
                    width = 75;
                    height = 125;
                }

                if (rank !== undefined && suit !== undefined) {
                    switch (suit) {
                        case 0: // Spades
                            x -= width;
                            y -= height;
                            break;
                        case 1: // Clubs
                            y -= height;
                            break;
                        case 2: // Diamonds
                            x -= width;
                            break;
                        case 3: // Hearts
                            break;
                        default:
                            console.error("Invalid suit:", suit);
                            return;
                    }

                    if (rank == 14) {
                        rank = 1;
                    } else if (rank < 1 || rank > 13) {
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

            PyPoker.Game.numCards = (message.game_type == "traditional") ? 5 : 2;
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

            $('#game-wrapper').addClass(message.game_type);

            message.players.forEach(function(player) {
                let playerId = player.id;
                let $player = $('#players .player[data-player-id="' + playerId + '"]');
                let $cards = $('.cards', $player);
                $cards.empty(); // Clear any existing cards
        
                for (let i = 0; i < PyPoker.Game.numCards; i++) {
                    $cards.append('<div class="card small" data-key="' + i + '"></div>');
                }
        
                if (playerId === message.dealer_id) {
                    $player.addClass('dealer');
                } else {
                    $player.removeClass('dealer');
                }
        
                if (playerId === PyPoker.Game.getCurrentPlayerId()) {
                    $player.addClass('current');
                } else {
                    $player.removeClass('current');
                }
            });
            $('#current-player').show();
            PyPoker.Logger.log("New game initialized.");
        },

        gameOver: function() {
            $('.player').removeClass('fold winner looser dealer');
            $('.player .cards').empty();
            $('#pots').empty();
            $('#shared-cards').empty();
            $('#players .player .bet-wrapper').empty();
            $('#current-player').hide();
            $('#start-game-wrapper').hide(); // Hide Start Game button when game is over
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

        handlePong: function() {
            console.log("Received pong from server.");
        },

        updatePlayersCards: function(players) {
            for (let playerId in players) {
                let player = players[playerId];
                let $cardsContainer = $('#players .player[data-player-id="' + playerId + '"] .cards');
        
                // Set each card's rank and suit
                player.cards.forEach(function(card, index) {
                    let $card = $cardsContainer.find('.card[data-key=' + index + '"]');
                    PyPoker.Game.setCard($card, card.rank, card.suit);
                });
        
                // Update the score category
                $cardsContainer.find('.category').text(PyPoker.Game.scoreCategories[player.score.category]);
            }
        },

        updateCurrentPlayerCards: function(cards, score) {
            let currentPlayerId = PyPoker.Game.getCurrentPlayerId();
            let $cardsContainer = $('#players .player[data-player-id="' + currentPlayerId + '"] .cards');
            cards.forEach(function(card, index) {
                let $card = $cardsContainer.find('.card[data-key="' + index + '"]');
                PyPoker.Game.setCard($card, card.rank, card.suit);
            });
        
            // Update the score category
            $('#players .player[data-player-id="' + currentPlayerId + '"] .cards .category').text(PyPoker.Game.scoreCategories[score.category]);
        },

        addSharedCards: function(cards) {
            let $sharedCardsContainer = $('#shared-cards');
            $sharedCardsContainer.empty(); // Clear existing shared cards

            cards.forEach(function(card) {
                let $card = $('<div class="card medium"></div>');
                PyPoker.Game.setCard($card, card.rank, card.suit);
                $sharedCardsContainer.append($card);
            });
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
            $('#start-game-wrapper').hide(); // Hide Start Game button after winners are set
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
                    PyPoker.Game.updateCurrentPlayerCards(message.cards, message.score);
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
                    PyPoker.Game.updatePlayersBet();
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
                    PyPoker.Player.handlePing(message);
                    break;
                case 'pong':
                    PyPoker.Player.handlePong(message);
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
            let $activeTimers = $('.timer.active');
            $activeTimers.TimeCircles().destroy();
            $activeTimers.removeClass('active');
        },

        resetControls: function() {
            PyPoker.Player.setCardsChangeMode(false);
            PyPoker.Player.disableBetMode();
        },

        sliderHandler: function(value) {
            if (value == 0) {
                $('#bet-cmd').text("Check"); // Use .text() instead of .attr("value", ...)
            } else {
                $('#bet-cmd').text("$" + parseInt(value)); // Also use .text() for bet amount
            }
            $('#bet-input').val(value);
            return value.toString(); // Return value for the slider tooltip
        },

        enableBetMode: function(message) {
            PyPoker.Player.betMode = true;

            if (!message.min_score || $('#current-player').data('allowed-to-bet')) {
                $('#bet-input').slider({
                    'min': parseInt(message.min_bet),
                    'max': parseInt(message.max_bet),
                    'value': parseInt(message.min_bet),
                    'formatter': PyPoker.Player.sliderHandler
                }).slider('setValue', parseInt(message.min_bet));

                if (message.min_score) {
                    $('#fold-cmd').val('Pass')
                        .removeClass('btn-danger')
                        .addClass('btn-warning');
                } else {
                    $('#fold-cmd').val('Fold')
                        .addClass('btn-danger')
                        .removeClass('btn-warning');
                }

                $('#fold-cmd-wrapper').show();
                $('#bet-input-wrapper').show();
                $('#bet-cmd-wrapper').show();
                $('#no-bet-cmd-wrapper').hide();
            } else {
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
            } else {
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
            console.log("Received pong from server.");
        },

        handlePing: function(message) {
            console.log("Received ping from server:", message);
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
            $('#start-game-wrapper').hide(); // Hide Start Game button when room is destroyed
        },

        onPlayerRemoved: function(message) {
            var playerId = message.player_id;
            $('#players .player[data-player-id="' + playerId + '"]').remove();
            PyPoker.Logger.log("Player removed: " + message.player_id);
        },

        onPlayerAdded: function(message) {
            PyPoker.Logger.log("Player added: " + message.player_name);
        },

        initRoom: function(players) {
            $('#players').empty();

            players.forEach(function(player, index) {
                var $seat = $('<div class="seat"></div>');
                $seat.attr('data-key', index);

                var $playerElement = PyPoker.Room.createPlayer({
                    id: player.player_id,
                    name: player.player_name,
                    money: player.player_money
                });
                $seat.append($playerElement);
                $seat.attr('data-player-id', player.player_id);

                $('#players').append($seat);
            });

            PyPoker.Logger.log("Room initialized with players.");
        },

        onRoomUpdate: function(message) {
            console.log("Received room update:", message);

            if (!message || !Array.isArray(message.players)) {
                console.error("Invalid room-update message structure:", message);
                PyPoker.Logger.log("Error: Invalid room update message.");
                return;
            }

            PyPoker.Room.initRoom(message.players);

            // Show or hide start game button based on can_start
            // Also highlight which players are ready
            if (message.can_start) {
                $('#start-game-wrapper').show();
            } else {
                $('#start-game-wrapper').hide();
            }

            // Optionally, you can show which players are ready
            // For simplicity, we just log them
            console.log("Ready players:", message.ready_players);
        }
    },

    init: function() {
        if (typeof roomId === 'undefined' || !roomId) {
            console.error("roomId is not defined.");
            return;
        }

        if (PyPoker.socket && PyPoker.socket.readyState === WebSocket.OPEN) {
            console.warn("WebSocket is already open.");
            return;
        }

        let wsScheme = window.location.protocol === "https:" ? "wss://" : "ws://";
        let connectionChannel = encodeURIComponent("game_room_" + roomId);

        PyPoker.socket = new WebSocket(
            wsScheme + window.location.host + "/ws/Services/" + connectionChannel + "/"
        );

        console.log("Initializing WebSocket connection...");

        PyPoker.socket.onopen = function() {
            console.log('WebSocket connected');
            PyPoker.Logger.log('Connected :)');

            PyPoker.socket.send(JSON.stringify({
                'message_type': 'join',
                'name': PyPoker.Game.getCurrentPlayerName(),
                'room_id': roomId
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
                    PyPoker.Player.handlePing(data);
                    break;
                case 'pong':
                    PyPoker.Player.handlePong(data);
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
                case 'join-success':
                    PyPoker.Logger.log("Successfully joined the room.");
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

        // Handle "Start Game" button click
        $('#start-game-cmd').click(function() {
            PyPoker.socket.send(JSON.stringify({
                'message_type': 'start-game'
            }));
            PyPoker.Logger.log("You signaled to start the game.");
            // Optionally, disable the button after clicking
            $(this).prop('disabled', true).text('Waiting for others...');
        });

        // Existing button handlers
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
        PyPoker.Logger.log("Player Name: " + PyPoker.Game.getCurrentPlayerName());
    },

    onDisconnect: function(message) {
        PyPoker.Logger.log("Disconnected from poker server.");
    },

    onError: function(message) {
        PyPoker.Logger.log(message.error);
    }
};

window.addEventListener('beforeunload', function() {
    if (PyPoker.socket) {
        PyPoker.socket.close();
    }
});

$(document).ready(function() {
    if ($('#game-wrapper').length)
        PyPoker.init();
});
