"""
Django Admin Site Configuration
Customizes the admin site header, title, and index title.
"""
from django.contrib import admin

# Customize admin site header and title
admin.site.site_header = "DC Network Administration"
admin.site.site_title = "DC Network Admin"
admin.site.index_title = "Welcome to DC Network Administration"

