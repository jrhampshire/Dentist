# Generated manually for xml_content field

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoicing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="xml_content",
            field=models.TextField(
                blank=True,
                default="",
                help_text="XML timbrado firmado por el SAT (decodificado de base64 Finkok)",
            ),
        ),
    ]
