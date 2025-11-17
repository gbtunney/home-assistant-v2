# Tuya Device Helper Usage/Notes

This is an attempt at listing devices and datapoints - to get the 'shadow'
datapoints state, ug..

- Single DP value:
- `./gbt-device-helper.py --pretty dp --device eb938e8ca0b930b04fzuzj --code smoke_sensor_state`
- Result: `{"smoke_sensor_state": "normal"}`
- `./gbt-device-helper.py dp --device <id> --code co_value --value-only`
- Filtered get (multiple DPs):
  - `./gbt-device-helper.py --pretty get --device <id> --codes co_state,co_value,smoke_sensor_state`
- Disable shadow fallback:
  - add `--no-shadow` to either command.

## Shadow - get hidden datapoints (i guess?)

> `./gbt-device-helper.py  --pretty shadow --device eb938e8ca0b930b04fzuzj`

```sh
Connecting to https://openapi.tuyaus.com as gbtunney@gmail.com (cc=1, app=smartlife)
connect_result: {'result': {'access_token': '1acdecd5dc5132e7b40142a8d7544f22', 'expire_time': 7200, 'platform_url': 'https://openapi.tuyaus.com', 'refresh_token': 'a19ecac2c1b87cdbdef777b76b4f1567', 'uid': 'az1707862528852NYkQq'}, 'success': True, 't': 1760770251075, 'tid': 'c8edae03abee11f0b05e7612c77168d3'}
{
  "result": {
    "properties": [
      {
        "code": "smoke_sensor_state",
        "custom_name": "",
        "dp_id": 1,
        "time": 1760734358764,
        "type": "enum",
        "value": "normal"
      },
      {
        "code": "smoke_sensor_value",
        "custom_name": "",
        "dp_id": 2,
        "time": 1760734359030,
        "type": "value",
        "value": 0
      },
      {
        "code": "checking_result",
        "custom_name": "",
        "dp_id": 9,
        "time": 1760734356188,
        "type": "enum",
        "value": "check_success"
      },
      {
        "code": "fault",
        "custom_name": "",
        "dp_id": 11,
        "time": 1760734359294,
        "type": "bitmap",
        "value": 0
      },
      {
        "code": "lifecycle",
        "custom_name": "",
        "dp_id": 12,
        "time": 1760734361184,
        "type": "bool",
        "value": true
      },
      {
        "code": "battery_state",
        "custom_name": "",
        "dp_id": 14,
        "time": 1760740604792,
        "type": "enum",
        "value": "high"
      },
      {
        "code": "battery_percentage",
        "custom_name": "",
        "dp_id": 15,
        "time": 1760740605274,
        "type": "value",
        "value": 100
      },
      {
        "code": "muffling",
        "custom_name": "",
        "dp_id": 16,
        "time": 1760734361448,
        "type": "bool",
        "value": false
      },
      {
        "code": "co_state",
        "custom_name": "",
        "dp_id": 18,
        "time": 1760734360116,
        "type": "enum",
        "value": "normal"
      },
      {
        "code": "co_value",
        "custom_name": "",
        "dp_id": 19,
        "time": 1760734360384,
        "type": "value",
        "value": 0
      },
      {
        "code": "fault_nodisturb",
        "custom_name": "",
        "dp_id": 101,
        "time": 1760734360656,
        "type": "enum",
        "value": "0"
      },
      {
        "code": "silence",
        "custom_name": "",
        "dp_id": 102,
        "time": 1760734360918,
        "type": "enum",
        "value": "DND_silence"
      }
    ]
  },
  "success": true,
  "t": 1760770255739,
  "tid": "cbbad3f2abee11f0b8aec6a1562d44cf"
}
```

## Get - device normal datapoints

> `./gbt-device-helper.py  --pretty get --device eb938e8ca0b930b04fzuzj`

```sh
  /config git:(>git-pull) ✗ ./gbt-device-helper.py  --pretty get --device eb938e8ca0b930b04fzuzj
Python: /usr/bin/python3
Connecting to https://openapi.tuyaus.com as gbtunney@gmail.com (cc=1, app=smartlife)
connect_result: {'result': {'access_token': '113d179e75569596496b9831f5ab7e52', 'expire_time': 7200, 'platform_url': 'https://openapi.tuyaus.com', 'refresh_token': '85868716186d1801ecbb3d918e942288', 'uid': 'az1707862528852NYkQq'}, 'success': True, 't': 1760769901259, 'tid': 'f865dd19abed11f0a0ffcef05b58082d'}
{
  "result": [
    {
      "code": "smoke_sensor_status",
      "value": "normal"
    },
    {
      "code": "smoke_sensor_value",
      "value": 0
    },
    {
      "code": "checking_result",
      "value": "check_success"
    },
    {
      "code": "lifecycle",
      "value": true
    },
    {
      "code": "battery_state",
      "value": "high"
    },
    {
      "code": "battery_percentage",
      "value": 100
    },
    {
      "code": "muffling",
      "value": false
    }
  ],
  "success": true,
  "t": 1760769906155,
  "tid": "fb5ca390abed11f0b8aec6a1562d44cf"
}
➜  /config git:(>git-pull) ✗
```

## List w dps and specific dp codes

> `./gbt-device-helper.py  --pretty get --device eb938e8ca0b930b04fzuzj`

```sh
/config git:(>git-pull) ✗ ./gbt-device-helper.py  --pretty get --device eb938e8ca0b930b04fzuzj
Connecting to https://openapi.tuyaus.com as gbtunney@gmail.com (cc=1, app=smartlife)
connect_result: {'result': {'access_token': 'dc3663c68e7c0b7183ad199988fd670d', 'expire_time': 7200, 'platform_url': 'https://openapi.tuyaus.com', 'refresh_token': '5fddf9364893dec9bf8848388cf35acd', 'uid': 'az1707862528852NYkQq'}, 'success': True, 't': 1760770009294, 'tid': '38d0d743abee11f0b05e7612c77168d3'}
Known devices:
- sm_34 | id=ebd72ac0a5b3b9576awumv | category=ywbj
  DP specs/status for ebd72ac0a5b3b9576awumv:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100,
    "co_state": "normal",
    "co_value": 0,
    "smoke_sensor_state": "normal",
    "smoke_sensor_value": 0
  }
}
- sm_36 | id=eb3693396dc591373cjcrr | category=ywbj
  DP specs/status for eb3693396dc591373cjcrr:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100,
    "co_state": "normal",
    "co_value": 0,
    "smoke_sensor_state": "normal",
    "smoke_sensor_value": 0
  }
}
- Contact Sensor (cs_21) | id=eb5b9763a34014ba8fkz6x | category=mcs
  DP specs/status for eb5b9763a34014ba8fkz6x:
  {
  "functions": {},
  "status": {
    "battery_percentage": 0
  }
}
- sm_37 | id=eb938e8ca0b930b04fzuzj | category=ywbj
  DP specs/status for eb938e8ca0b930b04fzuzj:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100,
    "co_state": "normal",
    "co_value": 0,
    "smoke_sensor_state": "normal",
    "smoke_sensor_value": 0
  }
}
- Bedroom String Light | id=04200484dc4f222febbd | category=cz
  DP specs/status for 04200484dc4f222febbd:
  {
  "functions": {},
  "status": {}
}
- sm_38 | id=ebc87a3c53ade86374zquz | category=ywbj
  DP specs/status for ebc87a3c53ade86374zquz:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100,
    "co_state": "normal",
    "co_value": 0,
    "smoke_sensor_state": "normal",
    "smoke_sensor_value": 0
  }
}
- WP 23 | id=eb873c2d427ca17960pnze | category=cz
  DP specs/status for eb873c2d427ca17960pnze:
  {
  "functions": {},
  "status": {}
}
- WP 21 | id=eb9a910f2ddf97a211twg0 | category=cz
  DP specs/status for eb9a910f2ddf97a211twg0:
  {
  "functions": {},
  "status": {}
}
- Bathroom Light Outlet | id=30727350d8f15be729d2 | category=cz
  DP specs/status for 30727350d8f15be729d2:
  {
  "functions": {},
  "status": {}
}
- 10g M Guppies | id=04200320b4e62d129b13 | category=cz
  DP specs/status for 04200320b4e62d129b13:
  {
  "functions": {},
  "status": {}
}
- Display case | id=87887101d8f15be445d3 | category=cz
  DP specs/status for 87887101d8f15be445d3:
  {
  "functions": {},
  "status": {}
}
- Hallway String Lights | id=60785480d8f15be61483 | category=cz
  DP specs/status for 60785480d8f15be61483:
  {
  "functions": {},
  "status": {}
}
- Dorn and Marceline | id=04200484dc4f222fe88d | category=cz
  DP specs/status for 04200484dc4f222fe88d:
  {
  "functions": {},
  "status": {}
}
- 120 gallon | id=03200121dc4f2224312d | category=cz
  DP specs/status for 03200121dc4f2224312d:
  {
  "functions": {},
  "status": {}
}
- 55g | id=04200320b4e62d127be7 | category=cz
  DP specs/status for 04200320b4e62d127be7:
  {
  "functions": {},
  "status": {}
}
- Living Room Light | id=0420048468c63abf8a3f | category=cz
  DP specs/status for 0420048468c63abf8a3f:
  {
  "functions": {},
  "status": {}
}
- sm_35 | id=eb12f2be00fcc6dba0cqxp | category=ywbj
  DP specs/status for eb12f2be00fcc6dba0cqxp:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100,
    "co_state": "normal",
    "co_value": 0,
    "smoke_sensor_state": "normal",
    "smoke_sensor_value": 0
  }
}
- Contact Sensor (cs_20) | id=eba72043e494984306pxki | category=mcs
  DP specs/status for eba72043e494984306pxki:
  {
  "functions": {},
  "status": {
    "battery_percentage": 27
  }
}
- Water Leak Sensor L1 (#11) | id=eb99e7396a53ec50f8eull | category=sj
  DP specs/status for eb99e7396a53ec50f8eull:
  {
  "functions": {},
  "status": {
    "battery_percentage": 100
  }
}
- WP 22 | id=eb7d9ea7398a3883d1mpdt | category=cz
  DP specs/status for eb7d9ea7398a3883d1mpdt:
  {
  "functions": {},
  "status": {}
}
- WP 32 | id=60785480d8f15be5c10d | category=cz
  DP specs/status for 60785480d8f15be5c10d:
  {
  "functions": {},
  "status": {}
}
- Motion Sensor 29 | id=eba0a4d34f0e4848d3up9d | category=pir
  DP specs/status for eba0a4d34f0e4848d3up9d:
  {
  "functions": {},
  "status": {}
}
- Smart Bulb 1 | id=eb6a4f80d30d920edbzsz4 | category=dj
  DP specs/status for eb6a4f80d30d920edbzsz4:
  {
  "functions": {},
  "status": {}
}
- LED Strip: Color | id=ebcf7e30a42f353868dwil | category=dd
  DP specs/status for ebcf7e30a42f353868dwil:
  {
  "functions": {},
  "status": {}
}
- Infrared RF remote control | id=eb96e3d29e31d7848bjfoe | category=wnykq
  DP specs/status for eb96e3d29e31d7848bjfoe:
  {
  "functions": {},
  "status": {}
}
- WP 24 | id=ebc3b4694a4a7f9085gcoz | category=cz
  DP specs/status for ebc3b4694a4a7f9085gcoz:
  {
  "functions": {},
  "status": {}
}
- Water Leak Sensor L3 (#13) | id=eb4c386c2a239394bblvii | category=sj
  DP specs/status for eb4c386c2a239394bblvii:
  {
  "functions": {},
  "status": {
    "battery_percentage": 2
  }
}
- Water Leak Sensor L2 (#12) | id=eb5d14bfd8ced4ce10ci6a | category=sj
  DP specs/status for eb5d14bfd8ced4ce10ci6a:
  {
  "functions": {},
  "status": {
    "battery_percentage": 6
  }
}
- Valve Controller | id=eb3d98cdgaxbbbko | category=sfkzq
  DP specs/status for eb3d98cdgaxbbbko:
  {
  "functions": {},
  "status": {
    "battery_percentage": 83
  }
}
- Test IPT-2CH V2.0 | id=ebf956de12e35cdf38arzm | category=wk
  DP specs/status for ebf956de12e35cdf38arzm:
  {
  "functions": {},
  "status": {}
}
```

```sh
curl --request GET "https://openapi.tuyaus.com/v2.0/cloud/thing/eb938e8ca0b930b04fzuzj/shadow/properties" --header "sign_method: HMAC-SHA256" --header "client_id: a7tgyhgx7nt4jxcryg88" --header "t: 1760769042057" --header "mode: cors" --header "Content-Type: application/json" --header "sign: 3902FB55CA13D339A6A55F16BB6A297AEB18758BC912141BCAF980F03D4EA716" --header "access_token: c058da6e53f72b4f53801cbe9951b485"
```

```json
{
  "result": {
    "properties": [
      {
        "code": "smoke_sensor_state",
        "custom_name": "",
        "dp_id": 1,
        "time": 1760734358764,
        "type": "enum",
        "value": "normal"
      },
      {
        "code": "smoke_sensor_value",
        "custom_name": "",
        "dp_id": 2,
        "time": 1760734359030,
        "type": "value",
        "value": 0
      },
      {
        "code": "checking_result",
        "custom_name": "",
        "dp_id": 9,
        "time": 1760734356188,
        "type": "enum",
        "value": "check_success"
      },
      {
        "code": "fault",
        "custom_name": "",
        "dp_id": 11,
        "time": 1760734359294,
        "type": "bitmap",
        "value": 0
      },
      {
        "code": "lifecycle",
        "custom_name": "",
        "dp_id": 12,
        "time": 1760734361184,
        "type": "bool",
        "value": true
      },
      {
        "code": "battery_state",
        "custom_name": "",
        "dp_id": 14,
        "time": 1760740604792,
        "type": "enum",
        "value": "high"
      },
      {
        "code": "battery_percentage",
        "custom_name": "",
        "dp_id": 15,
        "time": 1760740605274,
        "type": "value",
        "value": 100
      },
      {
        "code": "muffling",
        "custom_name": "",
        "dp_id": 16,
        "time": 1760734361448,
        "type": "bool",
        "value": false
      },
      {
        "code": "co_state",
        "custom_name": "",
        "dp_id": 18,
        "time": 1760734360116,
        "type": "enum",
        "value": "normal"
      },
      {
        "code": "co_value",
        "custom_name": "",
        "dp_id": 19,
        "time": 1760734360384,
        "type": "value",
        "value": 0
      },
      {
        "code": "fault_nodisturb",
        "custom_name": "",
        "dp_id": 101,
        "time": 1760734360656,
        "type": "enum",
        "value": "0"
      },
      {
        "code": "silence",
        "custom_name": "",
        "dp_id": 102,
        "time": 1760734360918,
        "type": "enum",
        "value": "DND_silence"
      }
    ]
  },
  "success": true,
  "t": 1760769042148,
  "tid": "f85f8561abeb11f0860556d5fdf17dc2"
}
```
