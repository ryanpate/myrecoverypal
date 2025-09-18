#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line to add a Python version if needed
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p staticfiles
mkdir -p logs
mkdir -p media/avatars

# If you have a root_files directory for PWA, create it
if [ -d "root_files" ]; then
    echo "root_files directory exists"
else
    mkdir -p root_files
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# List the staticfiles directory to verify
echo "Static files collected:"
ls -la staticfiles/

# Run migrations
python manage.py migrate --noinput

echo "Build completed successfully!"