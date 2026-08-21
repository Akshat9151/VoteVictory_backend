import enum
from typing import Dict, List


class RoleCode(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    VOLUNTEER = "VOLUNTEER"
    CUSTOM = "CUSTOM"


class PermissionCode(str, enum.Enum):
    # System & Org Level
    SYSTEM_MANAGE = "system.manage"
    AUDIT_VIEW = "audit.view"
    SECURITY_VIEW = "security.view"

    ORGANIZATION_CREATE = "organization.create"
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_UPDATE = "organization.update"
    ORGANIZATION_SUSPEND = "organization.suspend"

    # User & Access
    USER_CREATE = "user.create"
    USER_VIEW = "user.view"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_SUSPEND = "user.suspend"
    ROLE_MANAGE = "role.manage"
    PERMISSION_MANAGE = "permission.manage"

    # Election & Config
    ELECTION_CREATE = "election.create"
    ELECTION_VIEW = "election.view"
    ELECTION_UPDATE = "election.update"
    ELECTION_PUBLISH = "election.publish"
    ELECTION_CLOSE = "election.close"
    ELECTION_CANCEL = "election.cancel"
    POSITION_MANAGE = "position.manage"
    CONSTITUENCY_MANAGE = "constituency.manage"
    BOOTH_MANAGE = "booth.manage"
    AREA_MANAGE = "area.manage"

    # Candidates
    CANDIDATE_CREATE = "candidate.create"
    CANDIDATE_VIEW = "candidate.view"
    CANDIDATE_UPDATE = "candidate.update"
    CANDIDATE_APPROVE = "candidate.approve"
    CANDIDATE_REJECT = "candidate.reject"

    # Voters
    VOTER_CREATE = "voter.create"
    VOTER_VIEW = "voter.view"
    VOTER_UPDATE = "voter.update"
    VOTER_IMPORT = "voter.import"
    VOTER_VERIFY = "voter.verify"
    VOTER_CHECKIN = "voter.checkin"
    VOTER_BLOCK = "voter.block"

    # Polling & Volunteers
    STATION_MANAGE = "station.manage"
    STATION_VIEW = "station.view"
    VOLUNTEER_MANAGE = "volunteer.manage"
    VOLUNTEER_ASSIGN = "volunteer.assign"
    VOLUNTEER_VIEW = "volunteer.view"

    # Field Data Collection & Review
    DATA_SUBMIT = "data.submit"
    DATA_VIEW = "data.view"
    DATA_REVIEW = "data.review"
    DATA_EXPORT = "data.export"

    # Content & Creatives
    TEMPLATE_MANAGE = "template.manage"
    BANNER_MANAGE = "banner.manage"

    # Voting Engine & Ballots
    VOTE_SESSION_ISSUE = "vote.session_issue"
    VOTE_CAST = "vote.cast"

    # Results
    RESULT_VIEW = "result.view"
    RESULT_COUNT = "result.count"
    RESULT_APPROVE = "result.approve"
    RESULT_PUBLISH = "result.publish"

    # Notifications & Campaigns
    NOTIFICATION_SEND = "notification.send"
    NOTIFICATION_MANAGE = "notification.manage"
    NOTIFICATION_VIEW = "notification.view"

    # Reports, Alerts & Dashboards
    DASHBOARD_VIEW = "dashboard.view"
    REPORT_GENERATE = "report.generate"
    ALERT_MANAGE = "alert.manage"


# Default Role Permission Mappings
DEFAULT_ROLE_PERMISSIONS: Dict[RoleCode, List[PermissionCode]] = {
    RoleCode.SUPER_ADMIN: [
        PermissionCode.SYSTEM_MANAGE,
        PermissionCode.AUDIT_VIEW,
        PermissionCode.SECURITY_VIEW,
        PermissionCode.ORGANIZATION_CREATE,
        PermissionCode.ORGANIZATION_VIEW,
        PermissionCode.ORGANIZATION_UPDATE,
        PermissionCode.ORGANIZATION_SUSPEND,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_VIEW,
        PermissionCode.USER_UPDATE,
        PermissionCode.USER_SUSPEND,
        PermissionCode.ROLE_MANAGE,
        PermissionCode.PERMISSION_MANAGE,
        PermissionCode.ELECTION_CREATE,
        PermissionCode.ELECTION_VIEW,
        PermissionCode.ELECTION_UPDATE,
        PermissionCode.ELECTION_PUBLISH,
        PermissionCode.ELECTION_CLOSE,
        PermissionCode.ELECTION_CANCEL,
        PermissionCode.POSITION_MANAGE,
        PermissionCode.CONSTITUENCY_MANAGE,
        PermissionCode.BOOTH_MANAGE,
        PermissionCode.AREA_MANAGE,
        PermissionCode.CANDIDATE_CREATE,
        PermissionCode.CANDIDATE_VIEW,
        PermissionCode.CANDIDATE_UPDATE,
        PermissionCode.CANDIDATE_APPROVE,
        PermissionCode.CANDIDATE_REJECT,
        PermissionCode.VOTER_CREATE,
        PermissionCode.VOTER_VIEW,
        PermissionCode.VOTER_UPDATE,
        PermissionCode.VOTER_IMPORT,
        PermissionCode.VOTER_VERIFY,
        PermissionCode.VOTER_CHECKIN,
        PermissionCode.VOTER_BLOCK,
        PermissionCode.STATION_MANAGE,
        PermissionCode.STATION_VIEW,
        PermissionCode.VOLUNTEER_MANAGE,
        PermissionCode.VOLUNTEER_ASSIGN,
        PermissionCode.VOLUNTEER_VIEW,
        PermissionCode.DATA_SUBMIT,
        PermissionCode.DATA_VIEW,
        PermissionCode.DATA_REVIEW,
        PermissionCode.DATA_EXPORT,
        PermissionCode.TEMPLATE_MANAGE,
        PermissionCode.BANNER_MANAGE,
        PermissionCode.VOTE_SESSION_ISSUE,
        PermissionCode.VOTE_CAST,
        PermissionCode.RESULT_VIEW,
        PermissionCode.RESULT_COUNT,
        PermissionCode.RESULT_APPROVE,
        PermissionCode.RESULT_PUBLISH,
        PermissionCode.NOTIFICATION_SEND,
        PermissionCode.NOTIFICATION_MANAGE,
        PermissionCode.NOTIFICATION_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.REPORT_GENERATE,
        PermissionCode.ALERT_MANAGE,
    ],
    RoleCode.ADMIN: [
        PermissionCode.ORGANIZATION_VIEW,
        PermissionCode.ORGANIZATION_UPDATE,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_VIEW,
        PermissionCode.USER_UPDATE,
        PermissionCode.USER_SUSPEND,
        PermissionCode.ELECTION_CREATE,
        PermissionCode.ELECTION_VIEW,
        PermissionCode.ELECTION_UPDATE,
        PermissionCode.ELECTION_PUBLISH,
        PermissionCode.ELECTION_CLOSE,
        PermissionCode.POSITION_MANAGE,
        PermissionCode.CONSTITUENCY_MANAGE,
        PermissionCode.BOOTH_MANAGE,
        PermissionCode.AREA_MANAGE,
        PermissionCode.CANDIDATE_CREATE,
        PermissionCode.CANDIDATE_VIEW,
        PermissionCode.CANDIDATE_UPDATE,
        PermissionCode.CANDIDATE_APPROVE,
        PermissionCode.CANDIDATE_REJECT,
        PermissionCode.VOTER_CREATE,
        PermissionCode.VOTER_VIEW,
        PermissionCode.VOTER_UPDATE,
        PermissionCode.VOTER_IMPORT,
        PermissionCode.VOTER_VERIFY,
        PermissionCode.VOTER_CHECKIN,
        PermissionCode.VOTER_BLOCK,
        PermissionCode.STATION_MANAGE,
        PermissionCode.STATION_VIEW,
        PermissionCode.VOLUNTEER_MANAGE,
        PermissionCode.VOLUNTEER_ASSIGN,
        PermissionCode.VOLUNTEER_VIEW,
        PermissionCode.DATA_SUBMIT,
        PermissionCode.DATA_VIEW,
        PermissionCode.DATA_REVIEW,
        PermissionCode.DATA_EXPORT,
        PermissionCode.TEMPLATE_MANAGE,
        PermissionCode.BANNER_MANAGE,
        PermissionCode.RESULT_VIEW,
        PermissionCode.RESULT_COUNT,
        PermissionCode.RESULT_APPROVE,
        PermissionCode.RESULT_PUBLISH,
        PermissionCode.NOTIFICATION_SEND,
        PermissionCode.NOTIFICATION_MANAGE,
        PermissionCode.NOTIFICATION_VIEW,
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.REPORT_GENERATE,
        PermissionCode.ALERT_MANAGE,
        PermissionCode.AUDIT_VIEW,
    ],
    RoleCode.VOLUNTEER: [
        PermissionCode.ELECTION_VIEW,
        PermissionCode.STATION_VIEW,
        PermissionCode.USER_VIEW,
        PermissionCode.VOTER_VIEW,
        PermissionCode.VOTER_CREATE,
        PermissionCode.VOTER_VERIFY,
        PermissionCode.VOTER_CHECKIN,
        PermissionCode.VOLUNTEER_VIEW,
        PermissionCode.TEMPLATE_MANAGE,
        PermissionCode.NOTIFICATION_VIEW,
        PermissionCode.DATA_SUBMIT,
        PermissionCode.DASHBOARD_VIEW,
    ],
}
