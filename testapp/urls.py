from django.urls import path
from .views import *

urlpatterns = [
    # Vendor URLs
    path('api/vendors/', VendorListCreateView.as_view(), name='vendor-list-create'),
    path('api/vendors/<int:vendor_id>/', VendorDetailView.as_view(), name='vendor-detail'),
    path('api/vendors/<int:vendor_id>/performance/', VendorPerformanceView.as_view(), name='vendor-performance'),

    # Purchase Order URLs
    path('api/purchase_orders/', PurchaseOrderListCreateView.as_view(), name='purchase-order-list-create'),
    path('api/purchase_orders/<int:po_id>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('api/purchase_orders/<int:po_id>/acknowledge/', AcknowledgePurchaseOrderView.as_view(), name='purchase-order-acknowledge'),
]