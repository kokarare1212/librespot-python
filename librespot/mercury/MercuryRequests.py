from librespot.mercury.JsonMercuryRequest import JsonMercuryRequest
from librespot.mercury.RawMercuryRequest import RawMercuryRequest


class MercuryRequests:
    keymaster_client_id = "65b708073fc0480ea92a077233ca87bd"

    @staticmethod
    def get_root_playlists(username: str):
        pass

    @staticmethod
    def request_token(device_id, scope):
        return JsonMercuryRequest(
            RawMercuryRequest.get(
                "hm://keymaster/token/authenticated?scope={}&client_id={}&device_id={}"
                .format(scope, MercuryRequests.keymaster_client_id,
                        device_id)))
