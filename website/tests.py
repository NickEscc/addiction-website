from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import uuid

class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    def test_home_view(self):
        """
        Test that the home view renders the correct template.
        """
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
    def test_howtoplay_view(self):
        """
        Test that the HowToPlay view renders the correct template.
        """
        response = self.client.get(reverse('HowToPlay'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/HowToPlay.html')
    def test_login_view(self):
        """
        Test that the login view renders the correct template.
        """
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/login.html')
    def test_join_view(self):
        """
        Test that a POST request to join sets session data and redirects to the game page.
        """
        response = self.client.post(reverse('join'), {'name': 'TestPlayer', 'room-id': 'TestRoom'})
        self.assertRedirects(response, reverse('game'))
        session = self.client.session
        self.assertIn('player-id', session)
        self.assertEqual(session['player-name'], 'TestPlayer')
        self.assertEqual(session['player-money'], 1000)
        self.assertEqual(session['room-id'], 'TestRoom')
    def test_game_view_redirects_if_not_logged_in(self):
        """
        Test that the game view redirects to login if the player is not logged in.
        """
        response = self.client.get(reverse('game'))
        self.assertRedirects(response, reverse('login'))
    def test_game_view_renders_when_logged_in(self):
        """
        Test that the game view renders correctly when the player is logged in.
        """
        session = self.client.session
        session['player-id'] = str(uuid.uuid4())
        session['player-name'] = 'TestPlayer'
        session['player-money'] = 1000
        session['room-id'] = 'TestRoom'
        session.save()

        response = self.client.get(reverse('game'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/game.html')
        self.assertEqual(response.context['player_id'], session['player-id'])
        self.assertEqual(response.context['player_name'], 'TestPlayer')
        self.assertEqual(response.context['player_money'], 1000)
        self.assertEqual(response.context['room_id'], 'TestRoom')
    def test_logout_view(self):
        """
        Test that the logout view clears the session and redirects to the index page.
        """
        session = self.client.session
        session['player-id'] = str(uuid.uuid4())
        session['player-name'] = 'TestPlayer'
        session.save()

        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        session = self.client.session
        self.assertNotIn('player-id', session)
        self.assertNotIn('player-name', session)
    @patch('website.views.Popen')
    def test_start_texas_game(self, mock_popen):
        """
        Test that the start_texas_game view starts the game service and returns the correct JSON response.
        """
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        response = self.client.get(reverse('start_texas_game'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], "Texas Hold'em game started")
        self.assertEqual(data['pid'], 12345)
        mock_popen.assert_called_with(['python', 'website/Services/texasholdem_poker_service.py'])
