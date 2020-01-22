#!/usr/bin/env bash

if [ "$USE_LETSENCRYPT" == "yes" ]; then
  certbot renew --post-hook 'supervisorctl restart mailserver:'
fi
