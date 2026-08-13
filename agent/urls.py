from django.urls import path

from .views import (
    AgentBoardColumnCreateView,
    AgentBoardDetailView,
    AgentBoardListCreateView,
    AgentBoardPackageImageView,
    AgentBoardPublishView,
    AgentCardCoverView,
    AgentCardCreateView,
    AgentCardDetailView,
    AgentSupplierLookupView,
    AgentTourDateCreateView,
    AgentTourDetailView,
    AgentTourImageCreateView,
    AgentTourListCreateView,
    AgentTourPublishView,
)

urlpatterns = [
    path("suppliers/", AgentSupplierLookupView.as_view(), name="agent-suppliers"),
    path("tours/", AgentTourListCreateView.as_view(), name="agent-tours"),
    path("tours/<int:pk>/", AgentTourDetailView.as_view(), name="agent-tour-detail"),
    path("tours/<int:pk>/images/", AgentTourImageCreateView.as_view(), name="agent-tour-images"),
    path("tours/<int:pk>/dates/", AgentTourDateCreateView.as_view(), name="agent-tour-dates"),
    path("tours/<int:pk>/publish/", AgentTourPublishView.as_view(), name="agent-tour-publish"),
    path("boards/", AgentBoardListCreateView.as_view(), name="agent-boards"),
    path("boards/<int:pk>/", AgentBoardDetailView.as_view(), name="agent-board-detail"),
    path(
        "boards/<int:pk>/package-image/",
        AgentBoardPackageImageView.as_view(),
        name="agent-board-package-image",
    ),
    path(
        "boards/<int:pk>/columns/",
        AgentBoardColumnCreateView.as_view(),
        name="agent-board-columns",
    ),
    path("boards/<int:pk>/publish/", AgentBoardPublishView.as_view(), name="agent-board-publish"),
    path("columns/<int:pk>/cards/", AgentCardCreateView.as_view(), name="agent-column-cards"),
    path("cards/<int:pk>/", AgentCardDetailView.as_view(), name="agent-card-detail"),
    path("cards/<int:pk>/cover/", AgentCardCoverView.as_view(), name="agent-card-cover"),
]
