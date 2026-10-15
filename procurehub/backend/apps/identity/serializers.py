from rest_framework import serializers

from apps.identity.models import User


class UserMeSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "company", "roles"]

    def get_company(self, user):
        if not user.company:
            return None
        return {
            "id": str(user.company_id),
            "legal_name": user.company.legal_name,
            "company_type": user.company.company_type,
            "category": user.company.category,
            "status": user.company.status,
        }

    def get_roles(self, user):
        return list(user.roles.values_list("role_code", flat=True))
