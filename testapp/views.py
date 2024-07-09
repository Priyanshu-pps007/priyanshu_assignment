from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from django.utils import timezone
from django.db.models import Avg, F, ExpressionWrapper, fields

class VendorListCreateView(APIView):
    def get(self, request):
        vendors = Vendor.objects.all()
        serializer = VendorSerializer(vendors, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VendorDetailView(APIView):
    def get_object(self, vendor_id):
        return get_object_or_404(Vendor, id=vendor_id)

    def get(self, request, vendor_id):
        vendor = self.get_object(vendor_id)
        serializer = VendorSerializer(vendor)
        return Response(serializer.data)

    def put(self, request, vendor_id):
        vendor = self.get_object(vendor_id)
        serializer = VendorSerializer(vendor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, vendor_id):
        vendor = self.get_object(vendor_id)
        vendor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PurchaseOrderListCreateView(APIView):
    def get(self, request):
        purchase_orders = PurchaseOrder.objects.all()
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            purchase_orders = purchase_orders.filter(vendor_id=vendor_id)
        serializer = PurchaseOrderSerializer(purchase_orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PurchaseOrderDetailView(APIView):
    def get_object(self, po_id):
        return get_object_or_404(PurchaseOrder, id=po_id)

    def get(self, request, po_id):
        po = self.get_object(po_id)
        serializer = PurchaseOrderSerializer(po)
        return Response(serializer.data)

    def put(self, request, po_id):
        po = self.get_object(po_id)
        serializer = PurchaseOrderSerializer(po, data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.update_vendor_metrics(po.vendor)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, po_id):
        po = self.get_object(po_id)
        po.delete()
        self.update_vendor_metrics(po.vendor)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update_vendor_metrics(self, vendor):
        completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed')
        
        # On-Time Delivery Rate
        on_time_deliveries = completed_pos.filter(delivery_date__lte=F('order_date')).count()
        total_completed = completed_pos.count()
        on_time_delivery_rate = (on_time_deliveries / total_completed * 100) if total_completed > 0 else 0

        # Quality Rating Average
        quality_rating_avg = completed_pos.exclude(quality_rating__isnull=True).aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0

        # Average Response Time
        response_times = completed_pos.exclude(acknowledgment_date__isnull=True).annotate(
            response_time=ExpressionWrapper(
                F('acknowledgment_date') - F('issue_date'),
                output_field=fields.DurationField()
            )
        )
        avg_response_time = response_times.aggregate(Avg('response_time'))['response_time__avg']
        avg_response_time = avg_response_time.total_seconds() / 3600 if avg_response_time else 0  # Convert to hours

        # Fulfilment Rate
        fulfilled_pos = completed_pos.count()
        total_pos = PurchaseOrder.objects.filter(vendor=vendor).count()
        fulfillment_rate = (fulfilled_pos / total_pos * 100) if total_pos > 0 else 0

        # Update Vendor metrics
        vendor.on_time_delivery_rate = on_time_delivery_rate
        vendor.quality_rating_avg = quality_rating_avg
        vendor.average_response_time = avg_response_time
        vendor.fulfillment_rate = fulfillment_rate
        vendor.save()

        # Create Historical Performance record
        HistoricalPerformance.objects.create(
            vendor=vendor,
            date=timezone.now(),
            on_time_delivery_rate=on_time_delivery_rate,
            quality_rating_avg=quality_rating_avg,
            average_response_time=avg_response_time,
            fulfillment_rate=fulfillment_rate
        )

class VendorPerformanceView(APIView):
    def get(self, request, vendor_id):
        vendor = get_object_or_404(Vendor, id=vendor_id)
        serializer = VendorPerformanceSerializer(vendor)
        return Response(serializer.data)

class AcknowledgePurchaseOrderView(APIView):
    def post(self, request, po_id):
        po = get_object_or_404(PurchaseOrder, id=po_id)
        po.acknowledgment_date = timezone.now()
        po.save()
        self.update_vendor_metrics(po.vendor)
        return Response({'message': 'Purchase Order acknowledged successfully'})

    def update_vendor_metrics(self, vendor):
        # Recalculate average_response_time
        response_times = PurchaseOrder.objects.filter(vendor=vendor).exclude(acknowledgment_date__isnull=True).annotate(
            response_time=ExpressionWrapper(
                F('acknowledgment_date') - F('issue_date'),
                output_field=fields.DurationField()
            )
        )
        avg_response_time = response_times.aggregate(Avg('response_time'))['response_time__avg']
        vendor.average_response_time = avg_response_time.total_seconds() / 3600 if avg_response_time else 0  # Convert to hours
        vendor.save()