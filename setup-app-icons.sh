#!/bin/bash

# Setup App Icons Script for MyRecoveryPal
# This script prepares app icons for iOS and Android from existing favicon files

echo "🎨 Setting up app icons for MyRecoveryPal native apps..."

# Check if required tools are installed
if ! command -v convert &> /dev/null; then
    echo "⚠️  ImageMagick is not installed. Please install it first:"
    echo "   Ubuntu/Debian: sudo apt-get install imagemagick"
    echo "   macOS: brew install imagemagick"
    exit 1
fi

# Source icon (use the 512x512 favicon)
SOURCE_ICON="static/images/favicon_512.png"

if [ ! -f "$SOURCE_ICON" ]; then
    echo "❌ Source icon not found: $SOURCE_ICON"
    exit 1
fi

echo "📱 Generating Android icons..."

# Android icon sizes and directories
declare -A ANDROID_SIZES=(
    ["mdpi"]="48"
    ["hdpi"]="72"
    ["xhdpi"]="96"
    ["xxhdpi"]="144"
    ["xxxhdpi"]="192"
)

# Create Android icons
for density in "${!ANDROID_SIZES[@]}"; do
    size=${ANDROID_SIZES[$density]}
    dir="android/app/src/main/res/mipmap-${density}"

    if [ -d "$dir" ]; then
        echo "  Creating ${size}x${size} icon for ${density}..."
        convert "$SOURCE_ICON" -resize "${size}x${size}" "$dir/ic_launcher.png"
        convert "$SOURCE_ICON" -resize "${size}x${size}" "$dir/ic_launcher_round.png"

        # Create foreground for adaptive icon
        convert "$SOURCE_ICON" -resize "${size}x${size}" -background none -gravity center -extent "$((size*2))x$((size*2))" "$dir/ic_launcher_foreground.png"
    else
        echo "  ⚠️  Directory not found: $dir"
    fi
done

echo "🍎 iOS icons need to be generated using Xcode or manually..."
echo "   iOS requires specific icon sets in Assets.xcassets"
echo "   You can use a tool like https://appicon.co/ to generate iOS icons"

echo ""
echo "✅ Android icons generated successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. For iOS: Generate an AppIcon.appiconset using Xcode or online tools"
echo "   2. Update splash screens in both platforms"
echo "   3. Run: npx cap sync"
echo ""
