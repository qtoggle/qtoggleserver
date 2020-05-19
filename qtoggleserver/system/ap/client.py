
import datetime


class APClient:
    def __init__(
        self,
        mac_address: str,
        ip_address: str,
        hostname: str,
        moment: datetime
    ) -> None:

        self.mac_address: str = mac_address
        self.ip_address: str = ip_address
        self.hostname: str = hostname
        self.moment: datetime = moment

    def __str__(self) -> str:
        return f'APClient {self.mac_address} at {self.ip_address}'
