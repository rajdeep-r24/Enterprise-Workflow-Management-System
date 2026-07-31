from django.db import models
from django.core.exceptions import ImproperlyConfigured

class TenantQuerySet(models.QuerySet):
    """
    A custom QuerySet that provides a `for_tenant` method
    to explicitly filter queries by an organization.
    """
    def for_tenant(self, organization):
        if organization is None:
            return self.none()
        
        # We assume the model has an 'organization' attribute
        return self.filter(organization=organization)


class TenantManager(models.Manager):
    """
    A custom Manager that exposes the `for_tenant` method.
    """
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, organization):
        return self.get_queryset().for_tenant(organization)
