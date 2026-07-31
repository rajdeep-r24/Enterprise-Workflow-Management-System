from accounts.models import User

class SystemIdentityService:
    
    INBOUND_EMAIL_PROCESSOR_EMAIL = "inbound_email_processor@system.local"

    @classmethod
    def get_inbound_email_processor(cls):
        """
        Retrieves the Inbound Email Processor system identity.
        This account must be pre-provisioned via data migration or management command.
        Raises an exception if missing, to avoid silent escalation or provisioning bugs.
        """
        try:
            return User.objects.get(
                email=cls.INBOUND_EMAIL_PROCESSOR_EMAIL,
                user_type="SYSTEM",
                is_active=True
            )
        except User.DoesNotExist:
            raise RuntimeError(
                f"System identity '{cls.INBOUND_EMAIL_PROCESSOR_EMAIL}' not found. "
                "Ensure the data migration provisioning this account has been run."
            )
