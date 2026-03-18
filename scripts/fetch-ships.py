#!/usr/bin/env python3
"""
Fetch AIS ship position data for SITPULSE dashboard via aisstream.io WebSocket.
Connects briefly, collects vessel positions in the West Asia bounding box,
deduplicates by MMSI, enriches with flag state and vessel type, and outputs JSON.
Free API — register at aisstream.io for an API key (GitHub login).
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# MMSI Maritime Identification Digits → (ISO2, country name)
MID_TO_COUNTRY = {
    201: ("AL", "Albania"), 202: ("AD", "Andorra"), 203: ("AT", "Austria"),
    204: ("PT", "Azores"), 205: ("BE", "Belgium"), 206: ("BY", "Belarus"),
    207: ("BG", "Bulgaria"), 209: ("CY", "Cyprus"), 210: ("CY", "Cyprus"),
    211: ("DE", "Germany"), 212: ("CY", "Cyprus"), 213: ("GE", "Georgia"),
    214: ("MD", "Moldova"), 215: ("MT", "Malta"), 216: ("AM", "Armenia"),
    218: ("DE", "Germany"), 219: ("DK", "Denmark"), 220: ("DK", "Denmark"),
    224: ("ES", "Spain"), 225: ("ES", "Spain"), 226: ("FR", "France"),
    227: ("FR", "France"), 228: ("FR", "France"), 229: ("MT", "Malta"),
    230: ("FI", "Finland"), 231: ("FO", "Faroe Islands"),
    232: ("GB", "United Kingdom"), 233: ("GB", "United Kingdom"),
    234: ("GB", "United Kingdom"), 235: ("GB", "United Kingdom"),
    236: ("GI", "Gibraltar"), 237: ("GR", "Greece"), 238: ("HR", "Croatia"),
    239: ("GR", "Greece"), 240: ("GR", "Greece"), 241: ("GR", "Greece"),
    242: ("MA", "Morocco"), 243: ("HU", "Hungary"), 244: ("NL", "Netherlands"),
    245: ("NL", "Netherlands"), 246: ("NL", "Netherlands"), 247: ("IT", "Italy"),
    248: ("MT", "Malta"), 249: ("MT", "Malta"), 250: ("IE", "Ireland"),
    251: ("IS", "Iceland"), 252: ("LI", "Liechtenstein"), 253: ("LU", "Luxembourg"),
    254: ("MC", "Monaco"), 255: ("PT", "Madeira"), 256: ("MT", "Malta"),
    257: ("NO", "Norway"), 258: ("NO", "Norway"), 259: ("NO", "Norway"),
    261: ("PL", "Poland"), 263: ("PT", "Portugal"), 264: ("RO", "Romania"),
    265: ("SE", "Sweden"), 266: ("SE", "Sweden"), 267: ("SK", "Slovakia"),
    268: ("SM", "San Marino"), 269: ("CH", "Switzerland"),
    270: ("CZ", "Czech Republic"), 271: ("TR", "Turkey"), 272: ("UA", "Ukraine"),
    273: ("RU", "Russia"), 274: ("MK", "North Macedonia"),
    275: ("LV", "Latvia"), 276: ("EE", "Estonia"), 277: ("LT", "Lithuania"),
    278: ("SI", "Slovenia"), 279: ("RS", "Serbia"),
    301: ("AI", "Anguilla"), 303: ("US", "United States"),
    304: ("AG", "Antigua and Barbuda"), 305: ("AG", "Antigua and Barbuda"),
    306: ("CW", "Curacao"), 307: ("AW", "Aruba"),
    308: ("BS", "Bahamas"), 309: ("BS", "Bahamas"), 310: ("BM", "Bermuda"),
    311: ("BS", "Bahamas"), 312: ("BZ", "Belize"), 314: ("BB", "Barbados"),
    316: ("CA", "Canada"), 319: ("KY", "Cayman Islands"),
    321: ("CR", "Costa Rica"), 323: ("CU", "Cuba"), 325: ("DM", "Dominica"),
    327: ("DO", "Dominican Republic"), 329: ("GP", "Guadeloupe"),
    330: ("GD", "Grenada"), 331: ("GL", "Greenland"), 332: ("GT", "Guatemala"),
    334: ("HN", "Honduras"), 336: ("HT", "Haiti"), 338: ("US", "United States"),
    339: ("JM", "Jamaica"), 341: ("KN", "Saint Kitts and Nevis"),
    343: ("LC", "Saint Lucia"), 345: ("MX", "Mexico"), 347: ("MQ", "Martinique"),
    348: ("MS", "Montserrat"), 350: ("NI", "Nicaragua"), 351: ("PA", "Panama"),
    352: ("PA", "Panama"), 353: ("PA", "Panama"), 354: ("PA", "Panama"),
    355: ("PA", "Panama"), 356: ("PA", "Panama"), 357: ("PA", "Panama"),
    358: ("PR", "Puerto Rico"), 361: ("VC", "Saint Vincent"),
    362: ("TT", "Trinidad and Tobago"), 364: ("TC", "Turks and Caicos"),
    366: ("US", "United States"), 367: ("US", "United States"),
    368: ("US", "United States"), 369: ("US", "United States"),
    370: ("PA", "Panama"), 371: ("PA", "Panama"), 372: ("PA", "Panama"),
    373: ("PA", "Panama"), 374: ("PA", "Panama"), 375: ("VC", "Saint Vincent"),
    376: ("VC", "Saint Vincent"), 377: ("VC", "Saint Vincent"),
    378: ("VG", "British Virgin Islands"), 379: ("VI", "US Virgin Islands"),
    401: ("AF", "Afghanistan"), 403: ("SA", "Saudi Arabia"),
    405: ("BD", "Bangladesh"), 408: ("BH", "Bahrain"), 410: ("BT", "Bhutan"),
    412: ("CN", "China"), 413: ("CN", "China"), 414: ("CN", "China"),
    416: ("TW", "Taiwan"), 417: ("LK", "Sri Lanka"), 419: ("IN", "India"),
    422: ("IR", "Iran"), 423: ("AZ", "Azerbaijan"), 425: ("IQ", "Iraq"),
    428: ("IL", "Israel"), 431: ("JP", "Japan"), 432: ("JP", "Japan"),
    434: ("TM", "Turkmenistan"), 436: ("KZ", "Kazakhstan"),
    437: ("UZ", "Uzbekistan"), 438: ("JO", "Jordan"),
    440: ("KR", "South Korea"), 441: ("KR", "South Korea"),
    443: ("PS", "Palestine"), 445: ("KP", "North Korea"),
    447: ("KW", "Kuwait"), 450: ("LB", "Lebanon"), 451: ("KG", "Kyrgyzstan"),
    453: ("MO", "Macao"), 455: ("MV", "Maldives"), 457: ("MN", "Mongolia"),
    459: ("NP", "Nepal"), 461: ("OM", "Oman"), 463: ("PK", "Pakistan"),
    466: ("QA", "Qatar"), 468: ("SY", "Syria"),
    470: ("AE", "UAE"), 471: ("AE", "UAE"), 472: ("TJ", "Tajikistan"),
    473: ("YE", "Yemen"), 475: ("AF", "Afghanistan"),
    477: ("HK", "Hong Kong"), 478: ("BA", "Bosnia and Herzegovina"),
    501: ("FR", "Adelie Land"), 503: ("AU", "Australia"),
    506: ("MM", "Myanmar"), 508: ("BN", "Brunei"), 510: ("FM", "Micronesia"),
    511: ("PW", "Palau"), 512: ("NZ", "New Zealand"), 514: ("KH", "Cambodia"),
    515: ("KH", "Cambodia"), 516: ("CX", "Christmas Island"),
    518: ("CK", "Cook Islands"), 520: ("FJ", "Fiji"), 523: ("CC", "Cocos Islands"),
    525: ("ID", "Indonesia"), 529: ("KI", "Kiribati"), 531: ("LA", "Laos"),
    533: ("MY", "Malaysia"), 536: ("MP", "N. Mariana Islands"),
    538: ("MH", "Marshall Islands"), 540: ("NC", "New Caledonia"),
    542: ("NU", "Niue"), 544: ("NR", "Nauru"), 546: ("PF", "French Polynesia"),
    548: ("PH", "Philippines"), 553: ("PG", "Papua New Guinea"),
    555: ("PN", "Pitcairn"), 557: ("SB", "Solomon Islands"),
    559: ("AS", "American Samoa"), 561: ("WS", "Samoa"),
    563: ("SG", "Singapore"), 564: ("SG", "Singapore"), 565: ("SG", "Singapore"),
    566: ("SG", "Singapore"), 567: ("TH", "Thailand"), 570: ("TO", "Tonga"),
    572: ("TV", "Tuvalu"), 574: ("VN", "Vietnam"), 576: ("VU", "Vanuatu"),
    577: ("VU", "Vanuatu"), 578: ("WF", "Wallis and Futuna"),
    601: ("ZA", "South Africa"), 603: ("AO", "Angola"), 605: ("DZ", "Algeria"),
    607: ("FR", "Saint Paul"), 608: ("IO", "Ascension Island"),
    609: ("BI", "Burundi"), 610: ("BJ", "Benin"), 611: ("BW", "Botswana"),
    612: ("CF", "Central African Republic"), 613: ("CM", "Cameroon"),
    615: ("CG", "Congo"), 616: ("KM", "Comoros"), 617: ("CV", "Cape Verde"),
    618: ("FR", "Crozet"), 619: ("CI", "Ivory Coast"), 620: ("KM", "Comoros"),
    621: ("DJ", "Djibouti"), 622: ("EG", "Egypt"), 624: ("ET", "Ethiopia"),
    625: ("ER", "Eritrea"), 626: ("GA", "Gabon"), 627: ("GH", "Ghana"),
    629: ("GM", "Gambia"), 630: ("GW", "Guinea-Bissau"), 631: ("GQ", "Equatorial Guinea"),
    632: ("GN", "Guinea"), 633: ("BF", "Burkina Faso"), 634: ("KE", "Kenya"),
    635: ("FR", "Kerguelen"), 636: ("LR", "Liberia"), 637: ("LR", "Liberia"),
    638: ("SS", "South Sudan"), 642: ("LY", "Libya"), 644: ("LS", "Lesotho"),
    645: ("MU", "Mauritius"), 647: ("MG", "Madagascar"), 649: ("ML", "Mali"),
    650: ("MZ", "Mozambique"), 654: ("MR", "Mauritania"), 655: ("MW", "Malawi"),
    656: ("NE", "Niger"), 657: ("NG", "Nigeria"), 659: ("NA", "Namibia"),
    660: ("RE", "Reunion"), 661: ("RW", "Rwanda"),
    662: ("SD", "Sudan"), 663: ("SN", "Senegal"), 664: ("SC", "Seychelles"),
    665: ("SH", "Saint Helena"), 666: ("SO", "Somalia"), 667: ("SL", "Sierra Leone"),
    668: ("ST", "Sao Tome"), 669: ("SZ", "Eswatini"), 670: ("TD", "Chad"),
    671: ("TG", "Togo"), 672: ("TN", "Tunisia"), 674: ("TZ", "Tanzania"),
    675: ("UG", "Uganda"), 676: ("CD", "DR Congo"), 677: ("TZ", "Tanzania"),
    678: ("ZM", "Zambia"), 679: ("ZW", "Zimbabwe"),
}

# AIS vessel type codes → category
def classify_vessel_type(code):
    """Map AIS vessel type code to human-readable category."""
    if code is None:
        return "Unknown"
    code = int(code)
    if 70 <= code <= 79:
        return "Cargo"
    elif 80 <= code <= 89:
        return "Tanker"
    elif 60 <= code <= 69:
        return "Passenger"
    elif code == 30:
        return "Fishing"
    elif code in (31, 32):
        return "Towing"
    elif code == 33:
        return "Dredger"
    elif code == 34:
        return "Diving"
    elif code == 35:
        return "Military"
    elif code == 36:
        return "Sailing"
    elif code == 37:
        return "Pleasure Craft"
    elif 40 <= code <= 49:
        return "High Speed Craft"
    elif code == 50:
        return "Pilot"
    elif code == 51:
        return "SAR"
    elif code == 52:
        return "Tug"
    elif code == 53:
        return "Port Tender"
    elif code == 55:
        return "Law Enforcement"
    elif code == 58:
        return "Medical"
    else:
        return "Other"


def iso_to_flag_emoji(iso2):
    """Convert ISO 3166-1 alpha-2 code to flag emoji."""
    if not iso2 or len(iso2) != 2:
        return ""
    return chr(0x1F1E6 + ord(iso2[0]) - ord('A')) + chr(0x1F1E6 + ord(iso2[1]) - ord('A'))


def get_flag_from_mmsi(mmsi):
    """Extract flag state from MMSI Maritime Identification Digits."""
    if not mmsi or len(str(mmsi)) < 3:
        return None, None, ""
    mid = int(str(mmsi)[:3])
    info = MID_TO_COUNTRY.get(mid)
    if info:
        iso2, country = info
        return iso2, country, iso_to_flag_emoji(iso2)
    return None, None, ""


async def collect_ships(api_key, duration=45):
    """Connect to aisstream.io WebSocket and collect ship positions."""
    try:
        import websockets
    except ImportError:
        print("Installing websockets...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        import websockets

    vessels = {}
    url = "wss://stream.aisstream.io/v0/stream"

    # West Asia bounding box (expanded for maritime traffic)
    subscribe_msg = {
        "APIKey": api_key,
        "BoundingBoxes": [
            [[10, 30], [44, 65]],   # Persian Gulf, Arabian Sea, Red Sea
            [[10, 30], [30, 45]],   # Red Sea extension
        ],
        "FiltersShipMMSI": [],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }

    print(f"Connecting to aisstream.io (collecting for {duration}s)...")
    try:
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(subscribe_msg))
            end_time = asyncio.get_event_loop().time() + duration

            while asyncio.get_event_loop().time() < end_time:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    msg = json.loads(raw)
                    msg_type = msg.get("MessageType", "")
                    meta = msg.get("MetaData", {})
                    mmsi = meta.get("MMSI")

                    if not mmsi:
                        continue

                    mmsi_str = str(mmsi)

                    if mmsi_str not in vessels:
                        vessels[mmsi_str] = {
                            "mmsi": mmsi,
                            "name": "",
                            "lat": None,
                            "lng": None,
                            "sog": None,
                            "cog": None,
                            "heading": None,
                            "destination": "",
                            "vessel_type": "Unknown",
                            "vessel_type_code": None,
                            "draught": None,
                            "imo": None,
                            "callsign": "",
                            "timestamp": None,
                        }

                    v = vessels[mmsi_str]

                    # Update name from metadata
                    ship_name = meta.get("ShipName", "").strip()
                    if ship_name and ship_name != "0":
                        v["name"] = ship_name

                    # Update timestamp
                    ts = meta.get("time_utc")
                    if ts:
                        v["timestamp"] = ts

                    if msg_type == "PositionReport":
                        pos = msg.get("Message", {}).get("PositionReport", {})
                        if pos:
                            lat = pos.get("Latitude")
                            lng = pos.get("Longitude")
                            if lat is not None and lng is not None and lat != 91 and lng != 181:
                                v["lat"] = round(lat, 5)
                                v["lng"] = round(lng, 5)
                            sog = pos.get("Sog")
                            if sog is not None and sog < 102.3:
                                v["sog"] = round(sog, 1)
                            cog = pos.get("Cog")
                            if cog is not None and cog < 360:
                                v["cog"] = round(cog, 1)
                            hdg = pos.get("TrueHeading")
                            if hdg is not None and hdg < 360:
                                v["heading"] = hdg

                    elif msg_type == "ShipStaticData":
                        static = msg.get("Message", {}).get("ShipStaticData", {})
                        if static:
                            dest = static.get("Destination", "").strip()
                            if dest and dest != "0":
                                v["destination"] = dest
                            imo = static.get("ImoNumber")
                            if imo and imo > 0:
                                v["imo"] = imo
                            cs = static.get("CallSign", "").strip()
                            if cs and cs != "0":
                                v["callsign"] = cs
                            vtype = static.get("Type")
                            if vtype is not None:
                                v["vessel_type_code"] = vtype
                                v["vessel_type"] = classify_vessel_type(vtype)
                            draught = static.get("MaximumStaticDraught")
                            if draught and draught > 0:
                                v["draught"] = round(draught, 1)

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"  Message error: {e}")
                    continue

    except Exception as e:
        print(f"WebSocket error: {e}")

    return vessels


def main():
    api_key = os.environ.get("AISSTREAM_KEY", "")
    if not api_key:
        print("Error: AISSTREAM_KEY environment variable not set")
        print("Register free at https://aisstream.io and set AISSTREAM_KEY")
        sys.exit(1)

    vessels = asyncio.run(collect_ships(api_key, duration=45))
    print(f"Collected {len(vessels)} unique vessels")

    # Enrich with flag state and filter valid positions
    ship_list = []
    for mmsi_str, v in vessels.items():
        if v["lat"] is None or v["lng"] is None:
            continue

        iso2, country, flag = get_flag_from_mmsi(v["mmsi"])
        v["flag_iso"] = iso2 or ""
        v["flag_country"] = country or ""
        v["flag_emoji"] = flag

        ship_list.append(v)

    # Sort by name
    ship_list.sort(key=lambda s: s.get("name") or str(s.get("mmsi", "")))

    print(f"Valid positioned vessels: {len(ship_list)}")

    output = {
        "source": "aisstream.io",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(ship_list),
        "vessels": ship_list,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/ships.json", "w") as f:
        json.dump(output, f, ensure_ascii=False)
    print(f"Wrote {len(ship_list)} vessels to data/ships.json")


if __name__ == "__main__":
    main()
