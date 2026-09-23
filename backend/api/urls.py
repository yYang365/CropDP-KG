from django.urls import path
from .views import (
    GraphStatsView,
    GraphMetaView,
    GraphSearchView,
    GraphSubgraphView,
    GraphDiagnoseView,
)

urlpatterns = [
    path('graph/stats/', GraphStatsView.as_view(), name='graph-stats'),
    path('graph/meta/', GraphMetaView.as_view(), name='graph-meta'),
    path('graph/search/', GraphSearchView.as_view(), name='graph-search'),
    path('graph/subgraph/', GraphSubgraphView.as_view(), name='graph-subgraph'),
    path('graph/diagnose/', GraphDiagnoseView.as_view(), name='graph-diagnose'),
]
