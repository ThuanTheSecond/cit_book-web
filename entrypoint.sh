#!/bin/sh
if [ -z "$(ls -A /app/media)" ]; then
  echo "copy media"
  cp -r ./media/* /app/media/
fi

exec "$@"
