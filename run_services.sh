#!/bin/bash

# Start Django development server in the background
echo "Starting Django development server..."
python3 manage.py runserver &
DJANGO_PID=$!

# Start Texas Hold’em Poker Service in the background
echo "Starting Texas Hold’em Poker Service..."
python3 -m website.Services.texasholdem_poker_service &
POKER_PID=$!

# Function to handle script termination
function shutdown {
    echo "Shutting down services..."
    kill $DJANGO_PID
    kill $POKER_PID
    exit
}

# Trap CTRL+C (SIGINT) and execute shutdown
trap shutdown SIGINT

# Wait for both processes to finish
wait $DJANGO_PID
wait $POKER_PID
