[app]
title = VideMon
package.name = videmon
package.domain = org.videmon
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0.0
orientation = portrait  # Set to 'portrait' or 'landscape' or 'all'
fullscreen = 0
presplash = 
icon.filename = icon.png

# Main entrypoint
entrypoint = main.py

# (list) Application requirements
requirements = python3,kivy,yt-dlp,pyperclip

# (bool) Indicate if the application should use AndroidX libraries.
android.enable_androidx = True

# Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.arch = armeabi-v7a,arm64-v8a
