import json
import os
import random
import re
import string
import time
from urllib.parse import urlencode

import httpcloak

DIR = os.path.dirname(os.path.abspath(__file__))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
SEC_CH_UA = '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"'

proxies = []
if os.path.exists(os.path.join(DIR, "proxies.txt")):
    with open(os.path.join(DIR, "proxies.txt")) as f:
        proxies = [line.strip() for line in f if line.strip()]


def new_session():
    proxy = None
    if proxies:
        parts = random.choice(proxies).split(":")
        if len(parts) == 4:
            proxy = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        else:
            proxy = "http://" + ":".join(parts)
    return httpcloak.Session(preset="chrome-latest-windows", proxy=proxy, timeout=15, disable_http3=True)


def get_tokens(session):
    r = session.get("https://www.instagram.com/accounts/emailsignup/", headers={
        "sec-ch-ua": SEC_CH_UA,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": UA,
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "upgrade-insecure-requests": "1",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "sec-fetch-site": "none",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-encoding": "gzip, deflate, br, zstd",
        "priority": "u=0, i",
    })
    if r.status_code != 200:
        raise Exception(r.status_code)

    csrf = next((c.value for c in session.get_cookies() if c.name == "csrftoken"), None)
    if not csrf:
        csrf = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', r.text).group(1)
        session.set_cookie("csrftoken", csrf, domain=".instagram.com", path="/")
    lsd = re.search(r'"LSD"\s*,\s*\[\]\s*,\s*\{"token":"([^"]+)"', r.text).group(1)
    rev = re.search(r'"client_revision"\s*:\s*(\d+)', r.text)
    rev = rev.group(1) if rev else "1046821791"
    return csrf, lsd, rev


def check(session, csrf, lsd, rev, username):
    variables = {
        "input": {
            "fetch_username_suggestions": True,
            "field_name": "USERNAME",
            "username": {"sensitive_string_value": username},
        },
        "scale": 1,
    }
    data = {
        "av": "0",
        "__d": "www",
        "__user": "0",
        "qpl_active_flow_ids": "516759801",
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "useCAARegistrationFieldValidationQuery",
        "variables": json.dumps(variables, separators=(",", ":")),
        "doc_id": "26387190147557007",
        "fb_api_analytics_tags": '["qpl_active_flow_ids=516759801"]',
    }
    r = session.post("https://www.instagram.com/api/graphql", data=urlencode(data), headers={
        "sec-ch-ua": SEC_CH_UA,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": UA,
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "x-csrftoken": csrf,
        "x-ig-app-id": "936619743392459",
        "x-fb-friendly-name": "useCAARegistrationFieldValidationQuery",
        "x-ig-max-touch-points": "0",
        "x-asbd-id": "359341",
        "x-fb-lsd": lsd,
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua-full-version-list": '"Chromium";v="152.0.0.0", "Not?A_Brand";v="24.0.0.0", "Google Chrome";v="152.0.0.0"',
        "sec-ch-ua-model": '""',
        "sec-ch-ua-platform-version": '"10.0.0"',
        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "origin": "https://www.instagram.com",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://www.instagram.com/accounts/emailsignup/",
        "accept-encoding": "gzip, deflate, br, zstd",
        "priority": "u=1, i",
    })
    if r.status_code != 200:
        raise Exception(r.status_code)
    result = r.json()["data"]["xfb_caa_registration_field_validation"]
    return result["status"] == "SUCCESS"


def check_username(username):
    error = None
    for _ in range(5):
        try:
            session = new_session()
            csrf, lsd, rev = get_tokens(session)
            junk = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
            if not check(session, csrf, lsd, rev, junk):
                error = "proxy flagged"
                continue
            return check(session, csrf, lsd, rev, username), None
        except Exception as e:
            error = e
    return None, error


def run(usernames):
    for username in usernames:
        available, error = check_username(username)
        if available is None:
            print(f"[ERROR]     {username} ({error})")
        elif available:
            print(f"[AVAILABLE] {username}")
            with open(os.path.join(DIR, "available.txt"), "a") as f:
                f.write(username + "\n")
        else:
            print(f"[TAKEN]     {username}")
        time.sleep(random.uniform(0.5, 1.5))


if __name__ == "__main__":

    print("1) check a username")
    print("2) check usernames.txt")
    choice = input("> ").strip()

    if choice == "1":
        run([input("username: ").strip()])
    elif choice == "2":
        with open(os.path.join(DIR, "usernames.txt")) as f:
            run([line.strip() for line in f if line.strip()])
