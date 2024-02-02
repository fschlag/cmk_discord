#!/usr/bin/env python3
# Discord Notification

# https://github.com/fschlag/cmk_discord
# Version: 0.0.1
# Release date: 2024-02-02

import os
import sys
import datetime
import requests
from http import HTTPStatus

DISCORD_COLORS = {
    "Green": 5763719,
    "Orange": 15105570,
    "Red": 15548997,
    "DarkGrey": 9936031,
    "Yellow": 16776960,
}

ALERT_COLORS = {
    "CRITICAL": DISCORD_COLORS["Red"],
    "DOWN": DISCORD_COLORS["Red"],
    "WARNING": DISCORD_COLORS["Yellow"],
    "OK": DISCORD_COLORS["Green"],
    "UP": DISCORD_COLORS["Green"],
    "UNKNOWN": DISCORD_COLORS["Orange"],
    "UNREACHABLE": DISCORD_COLORS["DarkGrey"],
}


def emoji_for_notification_type(notification_type: str):
    if notification_type.startswith("PROBLEM"):
        return ":rotating_light: "
    if notification_type.startswith("RECOVERY"):
        return ":white_check_mark: "
    if notification_type.startswith("ACKNOWLEDGEMENT"):
        return ":ballot_box_with_check: "
    if notification_type.startswith("FLAPPINGSTART"):
        return ":interrobang: "
    if notification_type.startswith("FLAPPINGSTOP"):
        return ":white_check_mark: "
    if notification_type.startswith("DOWNTIMESTART"):
        return ":alarm_clock: "
    if notification_type.startswith("DOWNTIMEEND"):
        return ":white_check_mark: "
    if notification_type.startswith("DOWNTIMECANCELLED"):
        return ":ballot_box_with_check: "
    return ""


def build_service_embeds(ctx, site_url, timestamp):
    description = "**%s -> %s**\n\n%s" % (
        ctx.get("LASTSERVICESTATE"),
        ctx.get("SERVICESTATE"),
        ctx.get("SERVICEOUTPUT"),
    )
    if len(ctx.get("NOTIFICATIONCOMMENT")) > 0:
        description = "\n\n".join([description, ctx.get("NOTIFICATIONCOMMENT")])
    embed = {
        "title": "%s%s: %s"
                 % (
                     emoji_for_notification_type(ctx.get("NOTIFICATIONTYPE")),
                     ctx.get("NOTIFICATIONTYPE"),
                     ctx.get("SERVICEDESC"),
                 ),
        "description": description,
        "color": ALERT_COLORS[ctx.get("SERVICESTATE")],
        "fields": [
            {"name": "Host", "value": ctx.get("HOSTNAME"), "inline": True},
            {"name": "Service", "value": ctx.get("SERVICEDESC"), "inline": True},
        ],
        "footer": {
            "text": ctx.get("SERVICECHECKCOMMAND"),
        },
        "timestamp": timestamp,
    }

    if site_url:
        embed["url"] = "".join([site_url, ctx.get("SERVICEURL")])
    return [embed]


def build_host_embeds(ctx, site_url, timestamp):
    description = "**%s -> %s**\n\n%s" % (
        ctx.get("LASTHOSTSTATE"),
        ctx.get("HOSTSTATE"),
        ctx.get("HOSTOUTPUT"),
    )
    if len(ctx.get("NOTIFICATIONCOMMENT")) > 0:
        description = "\n\n".join([description, ctx.get("NOTIFICATIONCOMMENT")])
    embed = {
        "title": "%s%s: Host: %s"
                 % (
                     emoji_for_notification_type(ctx.get("NOTIFICATIONTYPE")),
                     ctx.get("NOTIFICATIONTYPE"),
                     ctx.get("HOSTNAME"),
                 ),
        "description": description,
        "color": ALERT_COLORS[ctx.get("HOSTSTATE")],
        "footer": {"text": ctx.get("HOSTCHECKCOMMAND")},
        "timestamp": timestamp,
    }
    if site_url:
        embed["url"] = "".join([site_url, ctx.get("HOSTURL")])
    return [embed]


def build_embeds(ctx, site_url):
    timestamp = str(datetime.datetime.fromisoformat(ctx["SHORTDATETIME"]).astimezone())
    return (
        build_service_embeds(ctx, site_url, timestamp)
        if ctx.get("WHAT") == "SERVICE"
        else build_host_embeds(ctx, site_url, timestamp)
    )


def build_webhook_content(ctx, site_url):
    return {
        "username": "Checkmk - " + ctx.get("OMD_SITE"),
        "avatar_url": "https://checkmk.com/android-chrome-192x192.png",
        "embeds": build_embeds(ctx, site_url),
    }


def build_context():
    return {
        var[7:]: value
        for (var, value) in os.environ.items()
        if var.startswith("NOTIFY_")
    }


def post_webhook(url, json):
    response = requests.post(url=url, json=json)
    if response.status_code != HTTPStatus.NO_CONTENT.value:
        sys.stderr.write(
            "Unexpected response when calling webhook url %s: %i. Response body: %s"
            % (url, response.status_code, response.text)
        )
        sys.exit(1)


def main():
    ctx = build_context()
    webhook_url = ctx.get("PARAMETER_1")
    site_url = ctx.get("PARAMETER_2")

    if not webhook_url:
        sys.stderr.write("Empty webhook url given as parameter 1")
        sys.exit(2)
    if not webhook_url.startswith("https://discord.com"):
        sys.stderr.write(
            "Invalid Discord webhook url given as first parameter (not starting with https://discord.com )"
        )
        sys.exit(2)
    if site_url and not site_url.startswith("http"):
        sys.stderr.write(
            "Invalid site url given as second parameter (not starting with http): %s"
            % site_url
        )
        sys.exit(2)

    webhook_content = build_webhook_content(ctx, site_url)

    post_webhook(webhook_url, webhook_content)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("Unhandled exception: %s\n" % e)
        sys.exit(2)
