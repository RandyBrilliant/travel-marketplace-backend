"""
Django Admin Site Configuration
Customizes the admin site header, title, and index title.
"""
from django.contrib import admin

# Customize admin site header and title
admin.site.site_header = "Travel Marketplace Administration"
admin.site.site_title = "Travel Marketplace Admin"
admin.site.index_title = "Welcome to Travel Marketplace Administration"

