from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.models import Company
from apps.identity.permissions import has_any_role
from apps.suppliers.models import SupplierRelationship
from apps.suppliers.services import rating_summary
from common.exceptions import DomainError


class SupplierRelationshipListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not has_any_role(request.user, "BUYER", "COMPANY_ADMIN", "SYSTEM_ADMIN"):
            raise DomainError("permission_denied", "Only buying-side users can view suppliers.", status_code=403)

        if has_any_role(request.user, "SYSTEM_ADMIN") or request.user.is_superuser:
            relationships = SupplierRelationship.objects.filter(
                status=SupplierRelationship.Status.ACTIVE,
                supplier_company__company_type=Company.CompanyType.SUPPLIER,
            ).select_related("supplier_company")
        elif request.user.company_id:
            relationships = SupplierRelationship.objects.filter(
                buyer_company_id=request.user.company_id,
                status=SupplierRelationship.Status.ACTIVE,
                supplier_company__company_type=Company.CompanyType.SUPPLIER,
            ).select_related("supplier_company")
        else:
            relationships = SupplierRelationship.objects.none()

        relationships = list(relationships.order_by("supplier_company__legal_name"))
        ratings = {}
        if request.user.company_id:
            ratings = rating_summary(request.user.company_id, [item.supplier_company_id for item in relationships])
        return Response({
            "results": [
                {
                    "id": str(relationship.id),
                    "status": relationship.status,
                    "supplier_company": {
                        "id": str(relationship.supplier_company_id),
                        "legal_name": relationship.supplier_company.legal_name,
                        "category": relationship.supplier_company.category,
                        "status": relationship.supplier_company.status,
                    },
                    "rating_average": ratings.get(relationship.supplier_company_id, {}).get("average"),
                    "rating_count": ratings.get(relationship.supplier_company_id, {}).get("count", 0),
                }
                for relationship in relationships
            ],
        })
