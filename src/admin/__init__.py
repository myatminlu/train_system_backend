"""
Admin System Module

This module provides comprehensive administrative functionality for the Bangkok Train Transport System.
It includes:

- Role-based authentication and authorization
- 2FA (Two-Factor Authentication) support
- System monitoring and health checks
- Performance metrics collection
- Audit logging
- User management
- Station management
- Analytics and reporting
- System configuration
- Backup and maintenance

The admin system is designed with security and scalability in mind, providing
granular permissions and comprehensive logging of all administrative actions.
"""

from . import router, schemas, auth_service, admin_service, monitoring_service

__all__ = [
    "router",
    "schemas", 
    "auth_service",
    "admin_service",
    "monitoring_service"
]