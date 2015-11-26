"""
Slack Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    settings:
      slack:
        endpoint: https://hooks.slack.com/...
        #channels:
        #  - "#deploy"
        #username: deploybot
        #icon_emoji: ":rocket"

"""
from fabric.utils import warn
from refabric.contrib import blueprints
from collections import OrderedDict
import urllib2
import json

blueprint = blueprints.get(__name__)

def notify(msg, quiet=False):
    channels = blueprint.get('channels', [])
    channel = blueprint.get('channel', None)

    # If channel is specified, add it to channels, and then run it through an
    # OrderedDict, removing any duplicates.
    if channel:
        channels.append(channel)
        channels = list(OrderedDict.fromkeys(channels))

    if not channels:
        warn('Empty slack channel list, skipping notification')
        return False

    username = blueprint.get('username', 'deploybot')
    icon_emoji = blueprint.get('icon_emoji', ':rocket:')

    endpoint = blueprint.get('endpoint')
    if not endpoint:
        warn('No slack API endpoint found, skipping notification')
        return False

    for channel in set(channels):
        send_request(endpoint=endpoint, channel=channel, username=username,
                     msg=msg, icon_emoji=icon_emoji, quiet=quiet)


def send_request(endpoint, channel, username, msg, icon_emoji, quiet=False):
    data = json.dumps({
        "channel": channel,
        "username": username,
        "text": msg,
        "icon_emoji": icon_emoji,
    })

    req = urllib2.Request(endpoint, data, {'Content-Type': 'application/json'})
    try:
        urllib2.urlopen(req).close()
    except urllib2.HTTPError as e:
        if quiet:
            warn(e)
        else:
            raise
