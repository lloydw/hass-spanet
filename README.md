

# hass-spanet - supports new SpaNET v2 protocol

<img src="https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.spanet.total" align="right">
Control your SpaNET Spa with Home Assistant

<br/>
<br/>

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lloydw&repository=hass-spanet&category=Integration)

### Current Progress

 - [x] Sensors
 - [x] HVAC Control
 - [x] Pumps
 - [x] Blower (fan — variable speed & ramp)
 - [x] Operation Mode
 - [x] Power Save
 - [x] Sleep Timers
 - [x] HeatPump Support (Enable via Configure screen)
 - [x] Lights — brightness, colour & effects
 - [x] Sanitise / clean cycle
 - [x] Filtration (runtime, interval & status)
 - [x] Keypad lock
 - [x] Auto-sanitise time
 - [x] Pump timeout

### Tested with Home Assistant 2026.7

# configuration

Simply add the plugin and then provide your SpaNET email and password, all Spas on your account will accessible.

# entities

Each spa exposes the following entities (prefixed with your spa's name):

| Entity | Type | Notes |
| --- | --- | --- |
| Climate | `climate` | Target/current temperature, heating state |
| Pumps | `switch` / `select` | Single-speed pumps are switches; variable-speed pumps are selects |
| Blower | `fan` | On/off, variable speed (1–5) and a `ramp` preset |
| Lights | `light` | On/off, brightness, an RGB colour wheel that snaps to the nearest supported spa colour, and the fade / step / party effect modes |
| Light Speed | `number` | Speed of the fade / step / party effects |
| Sanitise | `switch` + `binary_sensor` | Start/stop the one-touch clean cycle; the read-only sensor is kept for existing automations |
| Filtration | `binary_sensor` + `number` | Running status, plus total runtime and hours-between-cycles |
| Keypad Lock | `select` | Off / Partial / Full |
| Auto Sanitise Time | `time` | Daily automatic sanitise time |
| Pump Timeout | `number` | Auto-off timeout for pumps/operation |
| Operation Mode / Power Save / Sleep Timers | `select` / `switch` | |

# dashboards
<img width="334" align="center" alt="Climate" src="https://github.com/lloydw/hass-spanet/assets/297244/f3ab03b6-e5a9-43fd-bdc5-dcf80f7e64e6">

<img width="330" align="center" alt="Sensors" src="https://github.com/lloydw/hass-spanet/assets/297244/6d907414-d23e-4880-bcbc-892d7085614e">
<img width="330" align="center" alt="Graphs" src="https://github.com/lloydw/hass-spanet/assets/297244/98c5cbf1-18e1-4696-8132-4e5604ed8c07">

### Light control

The spa light is a full RGB `light` entity — brightness, a colour wheel that snaps to the nearest supported spa colour, and the fade / step / party effect modes with an adjustable speed.

<img width="330" align="center" alt="Light control" src="images/light-control.png">

# shout out to our contributors!

[@montoyenn-spec](https://github.com/montoyenn-spec) - blower, lights, settings, bug fixes
