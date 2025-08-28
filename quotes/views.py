from typing import List

from django.db import transaction
from django.db.models import F
from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required

from .forms import QuoteForm, SignUpForm, CommentForm
from .models import Quote, Vote, Source, Comment, CommentVote


def home_random_quote(request: HttpRequest) -> HttpResponse:
    quotes = list(Quote.objects.only("id", "weight").values_list("id", "weight"))
    if not quotes:
        return render(request, "quotes/home.html", {"quote": None})
    ids: List[int] = [q[0] for q in quotes]
    weights: List[int] = [max(int(q[1]), 1) for q in quotes]

    import random

    chosen_id = random.choices(ids, weights=weights, k=1)[0]
    quote = Quote.objects.select_related("source").get(id=chosen_id)
    Quote.objects.filter(id=quote.id).update(views=F("views") + 1)
    # voted state for disabling buttons
    session_key = _ensure_session(request)
    ip = _client_ip(request)
    voted = (
        Vote.objects.filter(quote_id=quote.id)
        .filter(models.Q(session_key=session_key) | models.Q(ip_address=ip))
        .exists()
    )
    comments = Comment.objects.filter(quote=quote).select_related("user")[:20]
    comments = (
        Comment.objects.filter(quote=quote, parent__isnull=True)
        .select_related("user")
        .prefetch_related("replies", "replies__user")
    )
    return render(
        request,
        "quotes/home.html",
        {
            "quote": quote,
            "voted": voted,
            "comments": comments,
            "comment_form": CommentForm(),
        },
    )


def quote_detail(request: HttpRequest, quote_id: int) -> HttpResponse:
    quote = get_object_or_404(Quote.objects.select_related("source"), id=quote_id)
    Quote.objects.filter(id=quote.id).update(views=F("views") + 1)
    session_key = _ensure_session(request)
    ip = _client_ip(request)
    voted = (
        Vote.objects.filter(quote_id=quote.id)
        .filter(models.Q(session_key=session_key) | models.Q(ip_address=ip))
        .exists()
    )
    comments = Comment.objects.filter(quote=quote).select_related("user")[:20]
    comments = (
        Comment.objects.filter(quote=quote, parent__isnull=True)
        .select_related("user")
        .prefetch_related("replies", "replies__user")
    )
    return render(
        request,
        "quotes/home.html",
        {
            "quote": quote,
            "voted": voted,
            "comments": comments,
            "comment_form": CommentForm(),
        },
    )


def _ensure_session(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _client_ip(request: HttpRequest) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@transaction.atomic
def like_quote(request: HttpRequest, quote_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    session_key = _ensure_session(request)
    ip = _client_ip(request)
    already = (
        Vote.objects.filter(quote_id=quote_id)
        .filter(models.Q(session_key=session_key) | models.Q(ip_address=ip))
        .exists()
    )
    if not already:
        Vote.objects.create(
            quote_id=quote_id,
            vote_type=Vote.LIKE,
            session_key=session_key,
            ip_address=ip,
        )
        Quote.objects.filter(id=quote_id).update(likes=F("likes") + 1)
    if request.headers.get("HX-Request"):
        quote = Quote.objects.get(id=quote_id)
        return render(
            request, "quotes/_like_block.html", {"quote": quote, "voted": True}
        )
    return redirect("home")


@transaction.atomic
def dislike_quote(request: HttpRequest, quote_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    session_key = _ensure_session(request)
    ip = _client_ip(request)
    already = (
        Vote.objects.filter(quote_id=quote_id)
        .filter(models.Q(session_key=session_key) | models.Q(ip_address=ip))
        .exists()
    )
    if not already:
        Vote.objects.create(
            quote_id=quote_id,
            vote_type=Vote.DISLIKE,
            session_key=session_key,
            ip_address=ip,
        )
        Quote.objects.filter(id=quote_id).update(dislikes=F("dislikes") + 1)
    if request.headers.get("HX-Request"):
        quote = Quote.objects.get(id=quote_id)
        return render(
            request, "quotes/_like_block.html", {"quote": quote, "voted": True}
        )
    return redirect("home")


def add_quote(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return render(request, "quotes/login_required.html")

    if request.method == "POST":
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.created_by = request.user
            quote.save()
            return redirect("home")
    else:
        form = QuoteForm()
    return render(request, "quotes/add_quote.html", {"form": form})


@login_required
def add_comment(request: HttpRequest, quote_id: int) -> HttpResponse:
    quote = get_object_or_404(Quote, id=quote_id)
    if request.method != "POST":
        return HttpResponse(status=405)
    form = CommentForm(request.POST)
    if form.is_valid():
        parent = None
        parent_id = form.cleaned_data.get("parent_id")
        if parent_id:
            parent = Comment.objects.filter(id=parent_id, quote=quote).first()
        Comment.objects.create(
            quote=quote,
            user=request.user,
            text=form.cleaned_data["text"],
            parent=parent,
        )
    if request.headers.get("HX-Request"):
        comments = Comment.objects.filter(quote=quote).select_related("user")[:20]
        comments = (
            Comment.objects.filter(quote=quote, parent__isnull=True)
            .select_related("user")
            .prefetch_related("replies", "replies__user")
        )
        return render(
            request, "quotes/_comments.html", {"comments": comments, "quote": quote}
        )
    return redirect("quote_detail", quote_id=quote.id)


@login_required
def comment_like(request: HttpRequest, comment_id: int) -> HttpResponse:
    comment = get_object_or_404(Comment, id=comment_id)
    vote, created = CommentVote.objects.get_or_create(
        comment=comment, user=request.user, defaults={"value": CommentVote.LIKE}
    )
    if not created:
        if vote.value == CommentVote.LIKE:
            vote.delete()
            Comment.objects.filter(id=comment.id).update(likes=F("likes") - 1)
        else:
            vote.value = CommentVote.LIKE
            vote.save(update_fields=["value"])
            Comment.objects.filter(id=comment.id).update(
                likes=F("likes") + 1, dislikes=F("dislikes") - 1
            )
    else:
        Comment.objects.filter(id=comment.id).update(likes=F("likes") + 1)
    if request.headers.get("HX-Request"):
        comment.refresh_from_db()
        return render(
            request,
            "quotes/_comment_item.html",
            {"comment": comment, "request": request},
        )
    return redirect("quote_detail", quote_id=comment.quote_id)


@login_required
def comment_dislike(request: HttpRequest, comment_id: int) -> HttpResponse:
    comment = get_object_or_404(Comment, id=comment_id)
    vote, created = CommentVote.objects.get_or_create(
        comment=comment, user=request.user, defaults={"value": CommentVote.DISLIKE}
    )
    if not created:
        if vote.value == CommentVote.DISLIKE:
            vote.delete()
            Comment.objects.filter(id=comment.id).update(dislikes=F("dislikes") - 1)
        else:
            vote.value = CommentVote.DISLIKE
            vote.save(update_fields=["value"])
            Comment.objects.filter(id=comment.id).update(
                dislikes=F("dislikes") + 1, likes=F("likes") - 1
            )
    else:
        Comment.objects.filter(id=comment.id).update(dislikes=F("dislikes") + 1)
    if request.headers.get("HX-Request"):
        comment.refresh_from_db()
        return render(
            request,
            "quotes/_comment_item.html",
            {"comment": comment, "request": request},
        )
    return redirect("quote_detail", quote_id=comment.quote_id)


@login_required
def comment_delete(request: HttpRequest, comment_id: int) -> HttpResponse:
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    quote_id = comment.quote_id
    if request.method != "POST":
        return HttpResponse(status=405)
    comment.delete()
    if request.headers.get("HX-Request"):
        comments = Comment.objects.filter(quote_id=quote_id).select_related("user")[:20]
        return render(
            request,
            "quotes/_comments.html",
            {"comments": comments, "quote": get_object_or_404(Quote, id=quote_id)},
        )
    return redirect("quote_detail", quote_id=quote_id)


@login_required
def quote_delete(request: HttpRequest, quote_id: int) -> HttpResponse:
    quote = get_object_or_404(Quote, id=quote_id, created_by=request.user)
    if request.method != "POST":
        return HttpResponse(status=405)
    quote.delete()
    return redirect("home")


def popular_quotes(request: HttpRequest) -> HttpResponse:
    qs = Quote.objects.select_related("source")
    source_name = request.GET.get("source") or ""
    type_ = request.GET.get("type") or ""
    sort = request.GET.get("sort") or "likes"
    if source_name:
        qs = qs.filter(source__name__icontains=source_name)
    if type_:
        qs = qs.filter(source__type=type_)
    if sort == "views":
        qs = qs.order_by("-views", "-likes")
    elif sort == "created":
        qs = qs.order_by("-created_at")
    else:
        qs = qs.order_by("-likes", "-views")

    from django.core.paginator import Paginator

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "quotes/popular.html", {"page_obj": page_obj})


def dashboard(request: HttpRequest) -> HttpResponse:
    from django.db.models import Sum

    totals = Quote.objects.aggregate(
        quotes=models.Count("id"),
        views=Sum("views"),
        likes=Sum("likes"),
        dislikes=Sum("dislikes"),
    )
    totals["sources"] = Source.objects.count()

    top_sources = (
        Quote.objects.values("source__name")
        .annotate(total_likes=Sum("likes"))
        .order_by("-total_likes")[:10]
    )
    return render(
        request, "quotes/dashboard.html", {"totals": totals, "top_sources": top_sources}
    )


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "quotes/signup.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("home")


# Create your views here.
