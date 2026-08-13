from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("travel", "0015_tourpackage_supplier_display_name"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="tourdate",
            unique_together={
                (
                    "package",
                    "departure_date",
                    "has_shopping_stop",
                    "departure_city",
                    "airline",
                )
            },
        ),
    ]
