# addiction/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),  # Include your app's URLs
    path('api/auth/', include('dj_rest_auth.urls')),  # dj_rest_auth login/logout
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    # dj_rest_auth registration
    path('accounts/', include('allauth.urls')),  # allauth's own signup/login/logout

]
