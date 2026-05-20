"""WhatsApp Notifications URL routes — /api/v1/whatsapp/*"""

from django.urls import path

from notifications.views import (
    NotificationLogViewSet,
    SendTestMessageView,
    WebhookView,
    WhatsAppTemplatesView,
)

# Manual route registration (ViewSet needs explicit action mapping)
log_list = NotificationLogViewSet.as_view({"get": "list", "head": "list"})
log_detail = NotificationLogViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    # Public webhook endpoint (no auth required — verified by signature)
    path("webhook/", WebhookView.as_view(), name="whatsapp-webhook"),
    # Notification logs (auth required)
    path("logs/", log_list, name="notification-logs-list"),
    path("logs/<uuid:pk>/", log_detail, name="notification-log-detail"),
    # Send test message (admin only)
    path("send-test/", SendTestMessageView.as_view(), name="send-test-message"),
    # List available templates
    path("templates/", WhatsAppTemplatesView.as_view(), name="whatsapp-templates"),
]
