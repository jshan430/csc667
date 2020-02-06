# hitme_game/consumers.py
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
import json
from .models import GameSession
from . import live_games


class LobbyConsumer(JsonWebsocketConsumer):
    LOBBY_CHANNEL_GROUP = "lobby_channels"

    @classmethod
    def update_game_broadcast(cls, data):
        channel_layer = get_channel_layer()
        data['type'] = 'update_game'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.LOBBY_CHANNEL_GROUP, data
        )

    @classmethod
    def remove_game_broadcast(cls, data):
        channel_layer = get_channel_layer()
        data['type'] = 'remove_game'
        # Send message to room group
        async_to_sync(channel_layer.group_send)(
            cls.LOBBY_CHANNEL_GROUP, data
        )

    def connect(self):
        if self.scope["user"].is_anonymous:
            self.close()

        # Join Lobby Group
        async_to_sync(self.channel_layer.group_add)(
            LobbyConsumer.LOBBY_CHANNEL_GROUP,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            LobbyConsumer.LOBBY_CHANNEL_GROUP,
            self.channel_name
        )

    def update_game(self, event):
        url = event["url"]
        creator = event["creator"]
        num_players = event["num_players"]

        content = {
            'type': 'UPDATE_GAME',
            'url': url,
            'creator': creator,
            'num_players': num_players,
        }
        self.send_json(content)

    def remove_game(self, event):
        url = event["url"]

        content = {
            'type': 'REMOVE_GAME',
            'url': url,
        }
        self.send_json(content)


class GameRoomConsumer(JsonWebsocketConsumer):
    def connect(self):
        if self.scope["user"].is_anonymous:
            self.close()
        game_url = self.scope["url_route"]["kwargs"]["game_url"]
        game = GameSession.objects.get_game(game_url)
        if game is None:
            self.close()
        self.game_url = game_url
        self.game_creator = game.creator.username
        self.accept()
        self.add_player()


    def add_player(self):
        url = self.game_url
        creator_username = self.game_creator

        num_players = live_games._redis_add_player(self, url, creator_username)

        # Send lobby Updates
        LobbyConsumer.update_game_broadcast({
            'url': url,
            'creator': creator_username,
            'num_players': num_players
        })


    def disconnect(self, close_code):
        self.remove_player()


    def remove_player(self):
        url = self.game_url
        creator_username = self.game_creator
        
        num_players = live_games._redis_remove_player(self, url)

        if num_players > 0:
            # Send lobby Updates
            LobbyConsumer.update_game_broadcast({
                'url': url,
                'creator': creator_username,
                'num_players': num_players
            })
        else:
            # Send lobby Updates
            LobbyConsumer.remove_game_broadcast({
                'url': url
            })
        