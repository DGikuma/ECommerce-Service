from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth import get_user_model
from core.models import Customer

User = get_user_model()

class MyOIDCBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user = super().create_user(claims)
        # Create/attach a Customer profile
        Customer.objects.get_or_create(
            user=user,
            defaults={
                "name": claims.get("name", user.username),
                "email": claims.get("email", ""),
                "phone_number": "",
                "address": "",
            }
        )
        return user

    def update_user(self, user, claims):
        user = super().update_user(user, claims)
        Customer.objects.update_or_create(
            user=user,
            defaults={
                "name": claims.get("name", user.username),
                "email": claims.get("email", getattr(user, "email", "")),
            }
        )
        return user
