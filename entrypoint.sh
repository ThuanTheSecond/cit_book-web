#!/bin/sh
echo "Starting entrypoint.sh"
echo "Working directory: $(pwd)"
echo "Listing local media: $(ls -la ./media || echo 'Media directory not found')"
echo "Listing volume: $(ls -la /app/media || echo 'Volume not mounted')"
if [ -d "./media" ]; then
  echo "Copying media files to volume"
  cp -rf ./media/* /app/media/ || echo "Failed to copy media files"
else
  echo "Error: ./media directory does not exist"
fi
echo "Finished entrypoint.sh"
exec "$@"
