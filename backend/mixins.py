from rest_framework.exceptions import MethodNotAllowed


class CreateReadOnlyMixin:
    """
    Block the generic update/partial_update/destroy routes on a ModelViewSet.

    Used for records that their owner may create and read but must not edit or
    delete afterwards (bookings, withdrawals, itinerary purchases). Money and
    status fields on these records change only through dedicated actions such
    as payment upload or admin/supplier review. Custom @action routes are not
    affected.
    """

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)
