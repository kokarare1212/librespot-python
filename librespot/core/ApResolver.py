import random
import requests


class ApResolver:
    base_url = "http://apresolve.spotify.com/"

    @staticmethod
    def request(service_type: str):
        response = requests.get("{}?type={}".format(ApResolver.base_url,
                                                    service_type))
        return response.json()

    @staticmethod
    def get_random_of(service_type: str):
        pool = ApResolver.request(service_type)
        urls = pool.get(service_type)
        if urls is None or len(urls) == 0:
            raise RuntimeError()
        return random.choice(urls)

    @staticmethod
    def get_random_dealer() -> str:
        return ApResolver.get_random_of("dealer")

    @staticmethod
    def get_random_spclient() -> str:
        return ApResolver.get_random_of("spclient")

    @staticmethod
    def get_random_accesspoint() -> str:
        return ApResolver.get_random_of("accesspoint")
