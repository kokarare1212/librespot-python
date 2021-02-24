class ProtobufMercuryRequest:
    request = None
    parser = None

    def __init__(self, request, parser):
        self.request = request
        self.parser = parser
