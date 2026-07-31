import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from employees.models import EmployeeInvitation

class InvitationService:

    @classmethod
    @transaction.atomic
    def create_invitation(cls, employee, invited_by):
        # Revoke any existing PENDING invitations for this employee
        now = timezone.now()
        existing_invitations = EmployeeInvitation.objects.filter(
            employee=employee,
            status="PENDING",
        )
        existing_invitations.update(
            status="REVOKED",
            revoked_at=now,
        )

        # Generate a new secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Create the new invitation
        expires_at = now + timedelta(hours=48)
        
        invitation = EmployeeInvitation.objects.create(
            employee=employee,
            organization=employee.organization,
            email=employee.user.email,
            token_hash=token_hash,
            status="PENDING",
            expires_at=expires_at,
            invited_by=invited_by,
        )

        return invitation, raw_token

    @classmethod
    def validate_token(cls, raw_token):
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        
        invitation = EmployeeInvitation.objects.filter(token_hash=token_hash).first()
        
        if not invitation:
            raise ValidationError("Invalid or expired invitation token.")
            
        if invitation.status != "PENDING":
            raise ValidationError("Invalid or expired invitation token.")
            
        if invitation.expires_at <= timezone.now():
            raise ValidationError("Invalid or expired invitation token.")
            
        return invitation

    @classmethod
    @transaction.atomic
    def accept_invitation(cls, raw_token, password):
        invitation = cls.validate_token(raw_token)
        
        user = invitation.employee.user
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])
        
        invitation.status = "ACCEPTED"
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at"])
        
        return user

