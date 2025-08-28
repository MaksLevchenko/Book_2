from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.contrib.auth import get_user_model


class Source(models.Model):
    TYPE_CHOICES = [
        ("movie", "Фильм"),
        ("book", "Книга"),
        ("series", "Сериал"),
        ("other", "Другое"),
    ]

    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")

    def __str__(self) -> str:
        return f"{self.name}"


class Quote(models.Model):
    text = models.TextField(unique=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="quotes")
    weight = models.PositiveIntegerField(default=1)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
    )

    class Meta:
        indexes = [
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["likes"]),
        ]

    def clean(self):
        super().clean()
        if self.weight < 1:
            raise ValidationError({"weight": "Weight must be at least 1."})
        if self.source_id:
            existing_count = (
                Quote.objects.filter(source_id=self.source_id)
                .exclude(pk=self.pk)
                .count()
            )
            if existing_count >= 3:
                raise ValidationError("A source cannot have more than 3 quotes.")

    def __str__(self) -> str:
        return self.text[:60]


class Vote(models.Model):
    LIKE = "like"
    DISLIKE = "dislike"
    VOTE_CHOICES = [
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    ]

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="votes")
    vote_type = models.CharField(max_length=7, choices=VOTE_CHOICES)
    session_key = models.CharField(max_length=40, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["quote", "session_key"]),
            models.Index(fields=["quote", "ip_address"]),
        ]


class Comment(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="comments"
    )
    text = models.TextField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["quote", "created_at"])]

    def __str__(self) -> str:
        return self.text[:60]


class CommentVote(models.Model):
    LIKE = 1
    DISLIKE = -1
    VALUE_CHOICES = [
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    ]

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="comment_votes"
    )
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "user")
        indexes = [
            models.Index(fields=["comment", "user"]),
        ]


# Create your models here.
