from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("itinerary", "0006_itinerarytransaction_promo_code_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="itineraryboard",
            name="supplier_display_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Optional supplier name shown for this board. "
                    "Use when entering on behalf of a partner without an account. "
                    "If blank, the owning supplier company name is used."
                ),
                max_length=255,
            ),
        ),
    ]
