""" SpaNet API

Based on https://github.com/BlaT2512/spanet-api/issues/4
"""
import logging
import json
import jwt
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://app.spanet.net.au/api"
SK_SETTEMP = "setTemperature"
SK_WATERTEMP = "currentTemperature"
SK_HEATER = "heater"
SK_SANITISE = "sanitiser"
SK_SLEEPING = "sleepStatus"

class SpaNetException(Exception):
    """Base SpaNet Exception"""


class SpaNetAuthFailed(SpaNetException):
    """SpaNet authentication failed"""


class SpaNetPoolUnknown(SpaNetException):
    """SpaPool not found"""


class SpaNetApiError(SpaNetException):
    """SpaPool connection failed"""
    def __init__(self, response, body):
        self.response = response
        super().__init__(f"API Error {response.status}: {body}")


class SpaPool:
    def __init__(self, config, client):
        self.config = config
        self.client = client
        self.last_status = None

    @property
    def id(self):
        return self.config["id"]

    @property
    def name(self):
        return self.config["name"]

    async def set_temperature(self, temp: int):
        value = int(temp * 10)
        res = await self.client.put("/Dashboard/" + self.config["id"], {"temperature": value})
        self.last_status[SK_SETTEMP] = value
        logger.debug(f"SET TEMP {value}: {res}\n{self.last_status}")

    def get_status(self, name: str):
        try:
            return self.last_status[name]
        except (KeyError, IndexError) as exc:
            logger.error("Failed to load data for status key %s", name, exc_info=exc)
            logger.error("Status: %s", self.last_status)
            raise

    async def refresh_status(self):
        dashboard_data = await self.client.get("/Dashboard/" + self.config["id"])
        info_data = await self.client.get("/Information/" + self.config["id"])

        status = {}
        status.update(dashboard_data)
        status.update(info_data.get("information", {}).get("informationStatus", {}))
        logger.debug(f"Spa {self.config['id']} Status: {status}")

        self.last_status = status
        return status

class SpaNet:
    def __init__(self, aio_session):
        self.session = aio_session
        self.spa_configs = {}
        self.spa_sockets = {}
        self.session_info = None
        self.client = None
        self.auth_token = {}

    async def authenticate(self, email, password, device_id):
        login_params = {
            "email": email,
            "password": password,
            "userDeviceId": device_id,
            "language": "en_AU"
        }

        client = HttpClient(self.session)
        try:
            login_data = await client.post("/Login/Authenticate", login_params)
            if "access_token" not in login_data:
                raise SpaNetAuthFailed()
        except Exception as e:
            raise SpaNetAuthFailed(e)

        self.token_source = TokenSource(client, login_data, device_id)
        self.client = HttpClient(self.session, self.token_source)
        device_data = await self.client.get("/Devices")

        spa_configs = []
        for config in device_data["devices"]:
            spa_configs.append(
                {
                    "id": str(config["id"]),
                    "name": config["name"],
                    "macAddress": config["macAddress"],
                }
            )
        self.spa_configs = spa_configs

    def get_available_spas(self):
        """Get a list of spas"""
        return self.spa_configs

    async def get_spa(self, spa_id):
        """Get the named spa"""

        spa_config = next(
            (spa for spa in self.spa_configs if str(spa["id"]) == spa_id),
            None,
        )
        if not spa_config:
            raise SpaNetPoolUnknown()

        return SpaPool(spa_config, self.client)

class HttpClient:
    def __init__(self, session, token_source=None):
        self.session = session
        self.token_source = token_source

    async def post(self, path, payload):
        response = await self.session.post(BASE_URL + path, data=json.dumps(payload), headers=await self.build_headers())
        return await self.check_response(response)

    async def put(self, path, payload):
        response = await self.session.put(BASE_URL + path, data=json.dumps(payload), headers=await self.build_headers())
        return await self.check_response(response)

    async def get(self, path):
        response = await self.session.get(BASE_URL + path, headers=await self.build_headers())
        return await self.check_response(response)

    async def build_headers(self):
        headers = {
            "User-Agent": "SpaNET/2 CFNetwork/1465.1 Darwin/23.0.0",
            "Content-Type": "application/json",
        }
        if self.token_source != None:
            headers["Authorization"] = "Bearer " + (await self.token_source.token())
        return headers

    async def check_response(self, response):
        if response.status > 299:
            body = await response.text()
            raise SpaNetApiError(response, body)
        if response.headers.get("Content-Type", "").startswith("application/json"):
            return await response.json()
        return await response.text()

class TokenSource:
    def __init__(self, client, token, device_id):
        self.token_data = {"device_id": device_id}
        self.client = client
        self.update(token)

    def update(self, token):
        decoded = jwt.decode(token["access_token"], options={"verify_signature": False}, algorithms=["HS256"])
        self.token_data.update(token)
        self.token_data["expires_at"] = decoded["exp"]

    async def token(self):
        expire_threshold = int(time.time()) - 60
        if self.token_data["expires_at"] > expire_threshold:
            return self.token_data["access_token"]

        response = await self.client.post("/OAuth/Token", {
            "refreshToken": self.token_data["refresh_token"],
            "userDeviceId": self.token_data["device_id"]
        })

        self.update(response)
        logger.debug(f"Token refreshed {self.token_data}")
        return self.token_data["access_token"]