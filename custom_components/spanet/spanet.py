""" SpaNet API

Based on https://github.com/BlaT2512/spanet-api/blob/main/spanet.md
"""
import socket
import asyncio
import logging

logger = logging.getLogger(__name__)

SK_SETTEMP = "R6:9"
SK_WATERTEMP = "R5:16"
SK_HEATER = "R5:13"
SK_CLEANING = "R5:12"
SK_SANITIZE = "R5:17"
SK_SLEEPING = "R5:11"
SK_PUMP1 = "R5:19"
SK_PUMP2 = "R5:20"


class SpaNetException(Exception):
    """Base SpaNet Exception"""


class SpaNetAuthFailed(SpaNetException):
    """SpaNet authentication failed"""


class SpaNetPoolUnknown(SpaNetException):
    """SpaPool not found"""


class SpaNetConnectFailed(SpaNetException):
    """SpaPool connection failed"""


class SpaNetConnectionLost(SpaNetException):
    """SpaPool connection failed"""


class SpaPool:
    def __init__(self, config, loop, sock):
        self.config = config
        self.loop = loop
        self.socket = sock
        self.lock = asyncio.Lock()
        self.last_status = None

    @property
    def id(self):
        return self.config["mac_addr"].replace(":", "")

    @property
    def name(self):
        return self.config["name"]

    async def set_temperature(self, temp: int):
        await self.send("W40", str(int(temp * 10)))

    def get_status(self, status_key: str):
        key, index = status_key.split(":")
        try:
            return self.last_status[key][int(index)]
        except (KeyError, IndexError) as exc:
            logger.error("Failed to load data for status key %s", status_key, exc_info=exc)
            logger.error("Status: %s", self.last_status)
            raise

    async def refresh_status(self):
        status = {}

        data = await self.send("RF", expect=13)
        logger.debug("REFRESH GOT %s", data)

        for row in data.split("\r\n"):
            row_data = row.split(",")
            if len(row_data) > 2:
                status[row_data[1]] = row_data

        self.last_status = status
        return status

    async def send(self, command, value=None, expect=1):
        if value:
            data = f"{command}:{value}\n"
        else:
            data = f"{command}\n"
        try:
            async with self.lock:
                logger.debug("SEND: %s", data)
                await self.loop.sock_sendall(self.socket, data.encode("utf-8"))

                response = ""
                while response.count("\n") < expect:
                    response += (await self.loop.sock_recv(self.socket, 1024)).decode("utf8")
                    logger.debug("RECV %d: %s", len(response), response)
                    logger.debug("WAIT %s %s", response.count("\n"), expect)

            return response
        except Exception as exc:
            logger.error("SpaNet Exception", exc_info=exc)
            raise SpaNetConnectionLost() from exc


class SpaNet:
    def __init__(self, aio_session):
        self.session = aio_session
        self.spa_configs = {}
        self.spa_sockets = {}
        self.session_info = None

    async def authenticate(self, username, encrypted_password):
        login_params = {
            "login": username,
            "api_key": "4a483b9a-8f02-4e46-8bfa-0cf5732dbbd5",
            "password": encrypted_password,
        }

        login_response = await self.session.post("https://api.spanet.net.au/api/MemberLogin", data=login_params)
        if login_response.status != 200 or (await login_response.json())["success"] is not True:
            raise SpaNetAuthFailed()

        session_info = (await login_response.json())["data"]

        socket_params = {
            "id_member": session_info["id_member"],
            "id_session": session_info["id_session"],
        }

        socket_response = await self.session.get("https://api.spanet.net.au/api/membersockets", params=socket_params)

        if socket_response.status != 200 or (await socket_response.json())["success"] is not True:
            raise SpaNetAuthFailed("Failed to get available sockets")

        self.spa_configs = (await socket_response.json())["sockets"]

    def get_available_spas(self):
        """Get a list of spas"""
        result = []
        for config in self.spa_configs:
            result.append(
                {
                    "id": config["mac_addr"].replace(":", ""),
                    "name": config["name"],
                    "mac_addr": config["mac_addr"],
                }
            )
        return result

    async def get_spa(self, spa_id):
        """Get the named spa"""

        logger.info("Opening connection to " + spa_id)

        spa_config = next(
            (spa for spa in self.spa_configs if spa["mac_addr"].replace(":", "") == spa_id),
            None,
        )
        if not spa_config:
            raise SpaNetPoolUnknown()

        loop = asyncio.get_event_loop()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        await loop.sock_connect(sock, (spa_config["spaurl"][:-5], int(spa_config["spaurl"][-4:])))
        await loop.sock_sendall(
            sock,
            bytes(
                "<connect--" + str(spa_config["id_sockets"]) + "--" + str(spa_config["id_member"]) + ">",
                "utf-8",
            ),
        )

        data = await loop.sock_recv(sock, 22)
        if data.decode("utf8") != "Successfully connected":
            raise SpaNetConnectFailed(f"Connect to spa {spa_id} failed, result: {data.decode('utf8')}")

        return SpaPool(spa_config, loop, sock)
