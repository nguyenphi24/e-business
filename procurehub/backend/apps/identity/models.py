import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from common.models import BaseModel


class Company(BaseModel):
    class CompanyType(models.TextChoices):
        BUYER = "BUYER"
        SUPPLIER = "SUPPLIER"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"

    legal_name = models.CharField(max_length=255)
    tax_code = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    company_type = models.CharField(max_length=10, choices=CompanyType.choices)  # D-01
    category = models.CharField(max_length=100, blank=True)  # D-01, FR-SUP-03

    class Meta:
        db_table = "companies"

    def __str__(self):
        return self.legal_name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.PROTECT, related_name="users")
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    objects = UserManager()

    class Meta:
        db_table = "users"

    def has_role(self, code):
        return self.roles.filter(role_code=code).exists()


class UserRole(models.Model):
    class Role(models.TextChoices):
        BUYER = "BUYER"
        MANAGER = "MANAGER"
        FINANCE = "FINANCE"  # hóa đơn, công nợ, thanh toán
        SUPPLIER = "SUPPLIER"
        COMPANY_ADMIN = "COMPANY_ADMIN"
        SYSTEM_ADMIN = "SYSTEM_ADMIN"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role_code = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        db_table = "user_roles"
        constraints = [models.UniqueConstraint(fields=["user", "role_code"], name="uniq_user_role")]
