from django.urls import path

from . import views_html

urlpatterns = [
    path(
        "simple/",
        views_html.SimpleRuleListView.as_view(),
        name="simplerule-list-html",
    ),
    path(
        "simple/new/",
        views_html.SimpleRuleCreateView.as_view(),
        name="simplerule-create-html",
    ),
    path(
        "simple/<int:pk>/edit/",
        views_html.SimpleRuleUpdateView.as_view(),
        name="simplerule-update-html",
    ),
    path(
        "simple/<int:pk>/delete/",
        views_html.simple_rule_delete,
        name="simplerule-delete-html",
    ),
    path(
        "custom/",
        views_html.CustomRuleListView.as_view(),
        name="customrule-list-html",
    ),
    path(
        "custom/new/",
        views_html.CustomRuleCreateView.as_view(),
        name="customrule-create-html",
    ),
    path(
        "custom/<int:pk>/edit/",
        views_html.CustomRuleUpdateView.as_view(),
        name="customrule-update-html",
    ),
    path(
        "custom/<int:pk>/delete/",
        views_html.custom_rule_delete,
        name="customrule-delete-html",
    ),
    path(
        "custom/<int:pk>/validate/",
        views_html.custom_rule_validate,
        name="customrule-validate-html",
    ),
]
