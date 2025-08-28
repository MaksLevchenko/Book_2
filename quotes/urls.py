from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.home_random_quote, name="home"),
    path("q/<int:quote_id>/", views.quote_detail, name="quote_detail"),
    path("add/", views.add_quote, name="add_quote"),
    path("comment/<int:quote_id>/", views.add_comment, name="add_comment"),
    path("popular/", views.popular_quotes, name="popular_quotes"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("like/<int:quote_id>/", views.like_quote, name="like_quote"),
    path("dislike/<int:quote_id>/", views.dislike_quote, name="dislike_quote"),
    path("comment-like/<int:comment_id>/", views.comment_like, name="comment_like"),
    path(
        "comment-dislike/<int:comment_id>/",
        views.comment_dislike,
        name="comment_dislike",
    ),
    path(
        "comment-delete/<int:comment_id>/", views.comment_delete, name="comment_delete"
    ),
    path("q/<int:quote_id>/delete/", views.quote_delete, name="quote_delete"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="quotes/login.html"),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
]
