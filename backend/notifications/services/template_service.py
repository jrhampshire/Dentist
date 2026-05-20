"""
WhatsApp message template service.

Handles:
- Template rendering with variable substitution
- Pre-approved template storage
- Variable validation ({nombre}, {fecha}, {hora}, {doctor})
"""

import logging
import re
from typing import Any

logger = logging.getLogger("notifications.services")

# ---------------------------------------------------------------------------
# Pre-approved WhatsApp templates
# These must match templates approved in Twilio WhatsApp Business API
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict[str, Any]] = {
    "appointment_reminder": {
        "name": "appointment_reminder",
        "body": "Hola {nombre}, te recordamos que tienes una cita el {fecha} a las {hora} con el/la Dr(a). {doctor}. Responde CONFIRMAR o CANCELAR.",
        "variables": ["nombre", "fecha", "hora", "doctor"],
        "language": "es",
        "category": "utility",
    },
    "appointment_confirmation": {
        "name": "appointment_confirmation",
        "body": "Hola {nombre}, tu cita ha sido confirmada para el {fecha} a las {hora} con el/la Dr(a). {doctor}. ¡Te esperamos!",
        "variables": ["nombre", "fecha", "hora", "doctor"],
        "language": "es",
        "category": "utility",
    },
    "appointment_cancelled": {
        "name": "appointment_cancelled",
        "body": "Hola {nombre}, tu cita del {fecha} a las {hora} con el/la Dr(a). {doctor} ha sido cancelada. Contacta a la clínica para reagendar.",
        "variables": ["nombre", "fecha", "hora", "doctor"],
        "language": "es",
        "category": "utility",
    },
    "appointment_rescheduled": {
        "name": "appointment_rescheduled",
        "body": "Hola {nombre}, tu cita ha sido reagendada para el {fecha} a las {hora} con el/la Dr(a). {doctor}.",
        "variables": ["nombre", "fecha", "hora", "doctor"],
        "language": "es",
        "category": "utility",
    },
    "test_message": {
        "name": "test_message",
        "body": "Este es un mensaje de prueba de ClínicaSaaS Dental MX. {mensaje}",
        "variables": ["mensaje"],
        "language": "es",
        "category": "utility",
    },
}


class TemplateError(Exception):
    """Raised when template rendering fails."""

    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template does not exist."""

    pass


class TemplateVariableError(TemplateError):
    """Raised when required template variables are missing."""

    pass


def get_template(template_name: str) -> dict[str, Any]:
    """
    Get a template by name.

    Args:
        template_name: Template identifier (e.g., 'appointment_reminder')

    Returns:
        Template dict with name, body, variables, language, category

    Raises:
        TemplateNotFoundError: If template doesn't exist
    """
    if template_name not in TEMPLATES:
        raise TemplateNotFoundError(
            f"Template '{template_name}' not found. "
            f"Available: {', '.join(TEMPLATES.keys())}"
        )
    return TEMPLATES[template_name]


def list_templates() -> list[dict[str, Any]]:
    """Return a list of all available templates with metadata."""
    return [
        {
            "name": tpl["name"],
            "body": tpl["body"],
            "variables": tpl["variables"],
            "language": tpl["language"],
            "category": tpl["category"],
        }
        for tpl in TEMPLATES.values()
    ]


def render_template(template_name: str, variables: dict[str, str]) -> str:
    """
    Render a template with variable substitution.

    Variables in the template body are denoted by {variable_name}.
    All required variables must be provided.

    Args:
        template_name: Template identifier
        variables: Dict of variable name → value

    Returns:
        Rendered message string

    Raises:
        TemplateNotFoundError: If template doesn't exist
        TemplateVariableError: If required variables are missing
    """
    template = get_template(template_name)
    body = template["body"]

    # Find all variables in the template body
    required_vars = set(re.findall(r"\{(\w+)\}", body))

    # Check for missing variables
    missing = required_vars - set(variables.keys())
    if missing:
        raise TemplateVariableError(
            f"Missing required variables for template '{template_name}': "
            f"{', '.join(sorted(missing))}"
        )

    # Substitute variables
    try:
        rendered = body.format(**variables)
    except KeyError as exc:
        raise TemplateVariableError(
            f"Variable {exc} not found in template '{template_name}'"
        ) from exc

    logger.debug(
        "Template '%s' rendered with variables: %s",
        template_name,
        list(variables.keys()),
    )
    return rendered
