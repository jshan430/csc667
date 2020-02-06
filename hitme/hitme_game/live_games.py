from .models import GameSession
from django.conf import settings
from redis import StrictRedis
import pickle


KEY_FORMAT = "GAME:{}:GAME"
LOCK_FORMAT = "LOCK:{}:LOCK"


class GameObj(object):
    def __init__(self, url, creator_username):
        self.url = url
        self.creator = creator_username
        self.players = set()


def _get_redis_conn():
    redis_configs = getattr(settings, 'LIVE_GAMES_REDIS_CONFIG', {})
    return StrictRedis(host=redis_configs.get('host', 'localhost'),
                       port=redis_configs.get('port', 6379),
                       db=redis_configs.get('db', 0))


def _redis_add_player(player_consumer, url, creator_username):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)

    with r.lock(lock_key):
        if r.exists(key):
            game_obj = pickle.loads(r.get(key))
        else:
            game_obj = GameObj(url=url, creator_username=creator_username)

        game_obj.players.add(player_consumer.channel_name)
        r.set(key, pickle.dumps(game_obj))

    num_players = len(game_obj.players)

    # Update Database
    GameSession.objects.update_num_players(url, num_players)
    return num_players


def _redis_remove_player(player_consumer, url):
    r = _get_redis_conn()
    key = KEY_FORMAT.format(url)
    lock_key = LOCK_FORMAT.format(url)

    with r.lock(lock_key):
        game_obj = pickle.loads(r.get(key))
        game_obj.players.discard(player_consumer.channel_name)
        num_players = len(game_obj.players)
        if num_players == 0:
            r.delete(key)
        else:
            r.set(key, pickle.dumps(game_obj))

    if num_players == 0:
        GameSession.objects.delete_game_session(url)
    else:
        GameSession.objects.update_num_players(url, num_players)
    return num_players
