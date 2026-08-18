from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, PermissionCode, RoleCode


def test_rbac_default_role_permissions_matrix():
    super_perms = DEFAULT_ROLE_PERMISSIONS[RoleCode.SUPER_ADMIN]
    admin_perms = DEFAULT_ROLE_PERMISSIONS[RoleCode.ADMIN]
    volunteer_perms = DEFAULT_ROLE_PERMISSIONS[RoleCode.VOLUNTEER]

    # Super admin must have system.manage
    assert PermissionCode.SYSTEM_MANAGE in super_perms

    # Admin must not have system.manage
    assert PermissionCode.SYSTEM_MANAGE not in admin_perms
    assert PermissionCode.ELECTION_CREATE in admin_perms

    # Volunteer must have limited operational permissions
    assert PermissionCode.ELECTION_CREATE not in volunteer_perms
    assert PermissionCode.CANDIDATE_CREATE not in volunteer_perms
    assert PermissionCode.VOTER_CHECKIN in volunteer_perms
    assert PermissionCode.VOTER_VIEW in volunteer_perms
