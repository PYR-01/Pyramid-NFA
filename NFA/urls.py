from django.urls import path

from .views import *

urlpatterns = [
    path("<str:id>", Sign_View.as_view(), name="home"),
    path("/reject/<str:id>", NFA_Rejection.as_view(), name="rejection"),
]
