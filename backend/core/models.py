from django.db import models
from django.conf import settings

class BaseAuditModel(models.Model):
    """
    An abstract base class that provides self-updating 
    'created_at' and 'updated_at' fields, plus tracking for WHO made the changes.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name="%(class)s_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name="%(class)s_updated"
    )

    class Meta:
        abstract = True 