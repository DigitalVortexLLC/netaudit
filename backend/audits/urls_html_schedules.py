from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.ScheduleListView.as_view(), name="schedule-list-html"),
    path("new/", views_html.ScheduleCreateView.as_view(), name="schedule-create-html"),
    path("<int:pk>/edit/", views_html.ScheduleUpdateView.as_view(), name="schedule-update-html"),
    path("<int:pk>/delete/", views_html.schedule_delete, name="schedule-delete-html"),
]
