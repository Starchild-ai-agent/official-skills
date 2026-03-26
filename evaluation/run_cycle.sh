#!/bin/bash
# Scheduled optimization cycle runner
# Outputs report summary to stdout (for push notification)
cd /data/workspace/projects/official-skills-audit
python -m evaluation.loop --tier small 2>&1
