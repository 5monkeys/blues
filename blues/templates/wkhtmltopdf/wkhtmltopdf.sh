#!/bin/bash
if ! pgrep Xvfb > /dev/null; then
    # Start new instance of Xvfb
    Xvfb :99 -noreset &
fi
DISPLAY=:99 /usr/bin/env wkhtmltopdf --quiet $*
