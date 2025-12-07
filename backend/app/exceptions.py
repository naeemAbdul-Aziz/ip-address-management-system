from fastapi import HTTPException, status

class IPAMError(Exception):
    """Base exception for IPAM application"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=self.message
        )

class ResourceNotFoundError(IPAMError):
    def __init__(self, resource_type: str, resource_id: any):
        super().__init__(f"{resource_type} not found: {resource_id}")
        self.resource_type = resource_type
        self.resource_id = resource_id

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=self.message
        )

class DuplicateResourceError(IPAMError):
    def __init__(self, resource_type: str, identifier: any):
        super().__init__(f"{resource_type} already exists: {identifier}")
        
    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=self.message
        )

class ValidationError(IPAMError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=self.message
        )

class InvalidCIDRError(ValidationError):
    def __init__(self, cidr: str, details: dict = None):
        super().__init__(f"Invalid CIDR format: {cidr}", details)

class CIDROverlapError(ValidationError):
    def __init__(self, cidr: str, existing_cidrs: list):
        super().__init__(
            f"CIDR {cidr} overlaps with existing subnets.",
            {"conflicting_cidrs": existing_cidrs}
        )
    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=self.message
        )

class SubnetFullError(IPAMError):
    def __init__(self, subnet_id: int, cidr: str):
        super().__init__(f"No available IPs in subnet {cidr} (ID: {subnet_id})")

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=self.message
        )

class DatabaseError(IPAMError):
    def __init__(self, operation: str, error: str):
        super().__init__(f"Database error during {operation}: {error}")
