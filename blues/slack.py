"""
Slack Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    settings:
      slack:
        endpoint: https://hooks.slack.com/...
        #channel: "#deploy"
        #username: deploybot
        #icon_emoji: ":rocket"

"""
from refabric.contrib import blueprints
import urllib2
import json

blueprint = blueprints.get(__name__)

def notify(msg):
    channel = blueprint.get('channel', '#deploy')
    username = blueprint.get('username', 'deploybot')
    icon_emoji = blueprint.get('icon_emoji', ':rocket:')

    endpoint = blueprint.get('endpoint')
    if not endpoint:
        return None

    data = json.dumps({
        "channel": channel,
        "username": username,
        "text": msg,
        "icon_emoji": icon_emoji,
    })
    req = urllib2.Request(endpoint, data, {'Content-Type': 'application/json'})
    urllib2.urlopen(req).close()
