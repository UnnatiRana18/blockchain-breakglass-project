// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EmergencyAccessControl {
    enum UrgencyLevel { MODERATE, URGENT, CRITICAL_RESUSCITATION }
    enum AccessState { NONE, ACTIVE, EXPIRED, REVOKED }

    struct Doctor {
        address walletAddress;
        string doctorId;
        string fullName;
        string licenseNumber;
        string hospitalAffiliation;
        bool isCertified;
        uint256 registeredAt;
    }

    struct AccessGrant {
        bytes32 grantId;
        string patientId;
        address doctorAddress;
        string doctorId;
        UrgencyLevel urgency;
        string reason;
        bytes32 reasonHash;
        uint256 grantedAt;
        uint256 durationSeconds;
        uint256 expiresAt;
        bool isManuallyRevoked;
        bytes32 dataScopeHash;
    }

    struct AuditEntry {
        bytes32 logId;
        bytes32 grantId;
        string patientId;
        address doctorAddress;
        string doctorId;
        uint256 timestamp;
        string action;
        string dataCategory;
        bytes32 payloadHash;
        bytes32 previousLogHash;
    }

    address public immutable admin;
    uint256 public constant MAX_EMERGENCY_WINDOW = 3600;
    uint256 public constant DEFAULT_EMERGENCY_WINDOW = 1800;

    bytes32 public lastGlobalLogHash;
    uint256 public totalAuditLogsCount;

    mapping(address => Doctor) public certifiedDoctors;
    mapping(bytes32 => AccessGrant) public accessGrants;
    mapping(string => bytes32[]) private patientGrantsHistory;
    mapping(string => bytes32[]) private patientAuditLogs;
    AuditEntry[] public globalAuditTrail;

    event DoctorCertified(address indexed doctorAddress, string doctorId, string licenseNumber);
    event EmergencyAccessRequested(bytes32 indexed grantId, string indexed patientId, address indexed doctorAddress, UrgencyLevel urgency, uint256 durationSeconds);
    event EmergencyAccessGranted(bytes32 indexed grantId, string indexed patientId, address indexed doctorAddress, uint256 grantedAt, uint256 expiresAt);
    event EmergencyAccessRevoked(bytes32 indexed grantId, string indexed patientId, address indexed doctorAddress, string reason, uint256 revokedAt);
    event AccessAttemptDeniedExpired(bytes32 indexed grantId, string indexed patientId, address indexed doctorAddress, uint256 attemptedAt);
    event RecordAccessLogged(bytes32 indexed logId, bytes32 indexed grantId, string indexed patientId, address doctorAddress, string action, string dataCategory, uint256 timestamp, bytes32 logHash);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Caller is not authorized admin");
        _;
    }

    modifier onlyCertifiedDoctor() {
        require(certifiedDoctors[msg.sender].isCertified, "Doctor is not certified in permissioned registry");
        _;
    }

    constructor() {
        admin = msg.sender;
        lastGlobalLogHash = keccak256(abi.encodePacked("GENESIS_BREAK_GLASS_AUDIT_LOG", block.timestamp));
    }

    function certifyDoctor(
        address _doctorAddress,
        string calldata _doctorId,
        string calldata _fullName,
        string calldata _licenseNumber,
        string calldata _hospitalAffiliation
    ) external onlyAdmin {
        require(_doctorAddress != address(0), "Invalid doctor address");
        certifiedDoctors[_doctorAddress] = Doctor({
            walletAddress: _doctorAddress,
            doctorId: _doctorId,
            fullName: _fullName,
            licenseNumber: _licenseNumber,
            hospitalAffiliation: _hospitalAffiliation,
            isCertified: true,
            registeredAt: block.timestamp
        });
        emit DoctorCertified(_doctorAddress, _doctorId, _licenseNumber);
    }

    function requestEmergencyAccess(
        string calldata _patientId,
        string calldata _reason,
        UrgencyLevel _urgency,
        uint256 _requestedDuration
    ) external onlyCertifiedDoctor returns (bytes32 grantId) {
        require(bytes(_patientId).length > 0, "Patient ID is required");
        require(bytes(_reason).length >= 8, "Clinical justification required (min 8 chars)");

        uint256 duration = _requestedDuration;
        if (duration == 0 || duration > MAX_EMERGENCY_WINDOW) {
            duration = DEFAULT_EMERGENCY_WINDOW;
        }

        uint256 currentTime = block.timestamp;
        uint256 expiryTime = currentTime + duration;
        bytes32 reasonHash = keccak256(abi.encodePacked(_reason));
        grantId = keccak256(abi.encodePacked(msg.sender, _patientId, currentTime, reasonHash, totalAuditLogsCount));
        bytes32 emergencyScopeHash = keccak256(abi.encodePacked("EMERGENCY_SCOPE_ALLERGIES_BLOOD_MEDS_VITALS"));

        accessGrants[grantId] = AccessGrant({
            grantId: grantId,
            patientId: _patientId,
            doctorAddress: msg.sender,
            doctorId: certifiedDoctors[msg.sender].doctorId,
            urgency: _urgency,
            reason: _reason,
            reasonHash: reasonHash,
            grantedAt: currentTime,
            durationSeconds: duration,
            expiresAt: expiryTime,
            isManuallyRevoked: false,
            dataScopeHash: emergencyScopeHash
        });

        patientGrantsHistory[_patientId].push(grantId);
        emit EmergencyAccessRequested(grantId, _patientId, msg.sender, _urgency, duration);
        emit EmergencyAccessGranted(grantId, _patientId, msg.sender, currentTime, expiryTime);

        _appendAuditLog(grantId, _patientId, msg.sender, certifiedDoctors[msg.sender].doctorId, "BREAK_GLASS_TRIGGERED", "GRANT_CREATED", reasonHash);
        return grantId;
    }

    function verifyAndValidateAccess(bytes32 _grantId) external returns (bool isValid, AccessState state, uint256 remainingSeconds) {
        AccessGrant storage grant = accessGrants[_grantId];
        require(grant.grantedAt > 0, "Grant ID does not exist");
        if (grant.isManuallyRevoked) return (false, AccessState.REVOKED, 0);
        if (block.timestamp > grant.expiresAt) {
            emit AccessAttemptDeniedExpired(_grantId, grant.patientId, grant.doctorAddress, block.timestamp);
            return (false, AccessState.EXPIRED, 0);
        }
        return (true, AccessState.ACTIVE, grant.expiresAt - block.timestamp);
    }

    function _appendAuditLog(
        bytes32 _grantId,
        string memory _patientId,
        address _doctorAddress,
        string memory _doctorId,
        string memory _action,
        string memory _dataCategory,
        bytes32 _payloadHash
    ) internal returns (bytes32 logId) {
        uint256 currentTime = block.timestamp;
        logId = keccak256(abi.encodePacked(lastGlobalLogHash, _grantId, _patientId, _doctorAddress, currentTime, _action, _payloadHash));
        AuditEntry memory entry = AuditEntry({
            logId: logId,
            grantId: _grantId,
            patientId: _patientId,
            doctorAddress: _doctorAddress,
            doctorId: _doctorId,
            timestamp: currentTime,
            action: _action,
            dataCategory: _dataCategory,
            payloadHash: _payloadHash,
            previousLogHash: lastGlobalLogHash
        });
        globalAuditTrail.push(entry);
        patientAuditLogs[_patientId].push(logId);
        lastGlobalLogHash = logId;
        totalAuditLogsCount++;
        emit RecordAccessLogged(logId, _grantId, _patientId, _doctorAddress, _action, _dataCategory, currentTime, logId);
        return logId;
    }
}
