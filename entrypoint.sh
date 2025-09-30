#!/bin/sh
#copy media content from local to volume
if [ -z "$(ls -A /app/media)" ]; then
  cp -r ./media/* /app/media/
fi

exec "$@"
