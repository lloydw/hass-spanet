""" SpaNet API

Based on https://github.com/BlaT2512/spanet-api/issues/4
"""
import logging
import json
import jwt
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://app.spanet.net.au/api"

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
        self.pumps = {}

    @property
    def id(self):
        return self.config["id"]

    @property
    def name(self):
        return self.config["name"]

    async def get_dashboard(self):
        return await self.client.get("/Dashboard/" + self.id)

    async def get_information(self):
        return await self.client.get("/Information/" + self.id)

    async def get_pumps(self):
        return await self.client.get("/PumpsAndBlower/Get/" + self.id)

    async def set_pump(self, pump_id:str, state:str):
        modeId = 0
        if state == "on":
            modeId = 1
        elif state == "off":
            modeId = 2
        else:
            logger.warn(f"Unknown modeId for pump state {state}")
            return
        return await self.client.put(f"/PumpsAndBlower/SetPump/" + pump_id, {
            "deviceId": self.id,
            "modeId": modeId,
            "pumpVariableSpeed": 0
        })

    async def set_temperature(self, temp: int):
        return await self.client.put("/Dashboard/" + self.config["id"], {"temperature": temp})

    async def get_operation_mode(self):
        return await self.client.get("/Settings/OperationMode/" + self.id)

    async def set_operation_mode(self, mode: int):
        return await self.client.put("/Settings/OperationMode/" + self.id, { "mode": mode })

    async def get_power_save(self):
        return await self.client.get("/Settings/PowerSave/" + self.id)

    async def set_power_save(self, mode: int):
        return await self.client.put("/Settings/PowerSave/" + self.id, { "mode": mode })

    async def get_sleep_timer(self, index:int):
        return await self.client.get("/SleepTimers/" + self.id)

    async def set_sleep_timer(self, timer_id: int, timer_number: int, enabled: int):
        return await self.client.put("/SleepTimers/" + str(timer_id), { "deviceId": self.id, "timerNumber": timer_number, "enabled": enabled == 1 })

    async def set_heat_pump(self, mode: int):
        return await self.client.put("/Settings/SetHeatPumpMode/" + self.id, { "mode": mode + 1 })

    async def set_element_boost(self, on: int):
        return await self.client.put("/Settings/SetElementBoost/" + self.id, { "svElementBoost": on == 1 })

    async def get_light_details(self):
        return await self.client.get("/Lights/GetLightDetails/" + self.id)

    async def set_light_status(self, light_id: int, on: int):
        return await self.client.put("/Lights/SetLightStatus/" + str(light_id), { "deviceId": self.id, "on": on == 1 })


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
        return await self.check_response(response, True)

    async def build_headers(self):
        headers = {
            "User-Agent": "SpaNET/5 CFNetwork/1498.700.2 Darwin/23.6.0",
            "Content-Type": "application/json",
        }
        if self.token_source != None:
            headers["Authorization"] = "Bearer " + (await self.token_source.token())
        return headers

    async def check_response(self, response, requires_json=False):
        if response.status > 299:
            self.raise_api_error(response)

        is_json = response.headers.get("Content-Type", "").startswith("application/json")

        if not is_json and requires_json:
            self.raise_api_error(response)

        if is_json:
            return await response.json()

        return await response.text()

    async def raise_api_error(self, response):
        body = await response.text()
        raise SpaNetApiError(response, body)

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