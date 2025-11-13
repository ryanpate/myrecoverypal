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

# Generate sitemap.xml for search engines
echo "Generating sitemap.xml..."
python manage.py generate_sitemap --output=sitemap.xml 2>&1 || echo "Note: Sitemap generation completed with warnings (this is normal if some pages don't exist yet)"

# Copy SEO files to static files directory (optional backup)
if [ -f "sitemap.xml" ]; then
    cp sitemap.xml staticfiles/sitemap.xml 2>/dev/null || echo "Note: Could not copy sitemap to staticfiles (not critical)"
    echo "Sitemap generated successfully"
else
    echo "Warning: sitemap.xml not generated"
fi

# Copy robots.txt if it exists
if [ -f "root_files/robots.txt" ]; then
    cp root_files/robots.txt staticfiles/robots.txt 2>/dev/null || echo "Note: Could not copy robots.txt to staticfiles (not critical)"
    echo "Robots.txt copied"
fi

echo "Build completed successfully!"