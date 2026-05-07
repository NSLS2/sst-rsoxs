import redis  ## In-memory (RAM) databases that persists on disk even if Bluesky is restarted
from redis_json_dict import RedisJSONDict
from nbs_bl.beamline import GLOBAL_BEAMLINE as bl
from nbs_bl.redisUtils import open_redis_client_from_settings

redis_config_settings = bl.settings.get("redis").get("config", {})
rsoxsredis = open_redis_client_from_settings(redis_config_settings)
rsoxs_config = RedisJSONDict(rsoxsredis, prefix=redis_config_settings.get("prefix", "rsoxs-"))