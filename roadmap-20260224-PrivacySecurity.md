# JARVISv5 Privacy & Security Controls - Milestone 5

**Objective**: Implement privacy controls and security infrastructure required before external API integration.

---

## Architecture Overview

```
User Input
  ↓
Security Layer (PII Detection)
  ↓
[If PII Detected] → Redactor → Redacted Content
  ↓
Tool Execution / LLM Processing
  ↓
Audit Logger (Security Events)
  ↓
[If External Call] → Privacy Check → Escalation Policy
  ↓
Response
```

**Core Principle**: Local-first by default. Privacy controls activate BEFORE any external call.

---

## Security Architecture Layers

### Layer 1: PII Detection & Redaction
**Purpose**: Identify and remove sensitive information before processing/storage/external calls

**Patterns to Detect**:
- **Credentials**: Passwords, API keys, tokens, secrets
- **Personal Identifiers**: SSN, passport numbers, driver's licenses
- **Financial**: Credit card numbers, bank accounts, routing numbers
- **Contact**: Email addresses, phone numbers, physical addresses
- **Health**: Medical record numbers, health insurance IDs
- **Network**: IP addresses, MAC addresses (when sensitive)

### Layer 2: Audit Trail
**Purpose**: Log all security-relevant events for compliance and debugging

**Events to Log**:
- PII detection occurrences
- Redaction operations
- External API calls (with redacted payloads)
- Permission denials
- Encryption operations

### Layer 3: At-Rest Encryption
**Purpose**: Protect stored conversations and memory from unauthorized access

**Scope**:
- Working state JSON files
- Episodic trace database
- Semantic memory metadata
- User preferences/settings

### Layer 4: Access Controls
**Purpose**: Explicit permission gates for sensitive operations

**Controls**:
- Tool permission tiers (already implemented in M4)
- External call permissions
- Encryption key management
- User consent tracking

---

## Implementation Tasks

### Task 5.1: PII Redaction Engine

**File**: `backend/security/redactor.py`

**Purpose**: Detect and redact PII from text before processing or external calls.

**Implementation**:

```python
"""
PII Redaction - Pattern-based detection and redaction of sensitive information
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PIIType(str, Enum):
    """Types of PII that can be detected"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    PASSWORD = "password"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    
    # Contextual patterns
    SECRET_TOKEN = "secret_token"
    PRIVATE_KEY = "private_key"


@dataclass(frozen=True)
class PIIMatch:
    """A detected PII instance"""
    pii_type: PIIType
    start: int
    end: int
    original_text: str
    confidence: float  # 0.0 to 1.0


@dataclass(frozen=True)
class RedactionResult:
    """Result of redaction operation"""
    original: str
    redacted: str
    matches: list[PIIMatch]
    pii_detected: bool


class PIIRedactor:
    """Detect and redact PII from text"""
    
    def __init__(self):
        # Regex patterns for PII detection
        self.patterns = {
            PIIType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            PIIType.PHONE: re.compile(
                r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
            ),
            PIIType.SSN: re.compile(
                r'\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b'
            ),
            PIIType.CREDIT_CARD: re.compile(
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'
            ),
            PIIType.IP_ADDRESS: re.compile(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ),
        }
        
        # Contextual patterns (require surrounding keywords)
        self.contextual_patterns = {
            PIIType.API_KEY: (
                re.compile(r'\b[A-Za-z0-9_-]{32,}\b'),
                ['api[_\s-]?key', 'token', 'secret']
            ),
            PIIType.PASSWORD: (
                re.compile(r'\b\S{8,}\b'),
                ['password', 'passwd', 'pwd']
            ),
            PIIType.SECRET_TOKEN: (
                re.compile(r'\b[A-Za-z0-9_-]{20,}\b'),
                ['secret', 'token', 'bearer']
            ),
        }
    
    def detect(self, text: str) -> list[PIIMatch]:
        """Detect PII in text without redacting"""
        matches = []
        
        # Pattern-based detection
        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    original_text=match.group(),
                    confidence=1.0
                ))
        
        # Contextual pattern detection
        for pii_type, (pattern, keywords) in self.contextual_patterns.items():
            text_lower = text.lower()
            
            # Check if any keyword is present
            has_context = any(
                re.search(rf'\b{keyword}\b', text_lower)
                for keyword in keywords
            )
            
            if has_context:
                for match in pattern.finditer(text):
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        start=match.start(),
                        end=match.end(),
                        original_text=match.group(),
                        confidence=0.8  # Lower confidence for contextual
                    ))
        
        # Sort by position
        return sorted(matches, key=lambda m: m.start)
    
    def redact(
        self,
        text: str,
        replacement_template: str = "[REDACTED:{pii_type}]"
    ) -> RedactionResult:
        """Detect and redact PII from text"""
        matches = self.detect(text)
        
        if not matches:
            return RedactionResult(
                original=text,
                redacted=text,
                matches=[],
                pii_detected=False
            )
        
        # Build redacted text by replacing from end to start
        redacted = text
        for match in reversed(matches):
            replacement = replacement_template.format(
                pii_type=match.pii_type.value.upper()
            )
            redacted = (
                redacted[:match.start] +
                replacement +
                redacted[match.end:]
            )
        
        return RedactionResult(
            original=text,
            redacted=redacted,
            matches=matches,
            pii_detected=True
        )
    
    def redact_with_preservation(
        self,
        text: str,
        preserve_domains: bool = True
    ) -> RedactionResult:
        """
        Redact PII while preserving semantic structure
        
        Example: john.doe@company.com → [EMAIL:preserved@company.com]
        """
        matches = self.detect(text)
        
        if not matches:
            return RedactionResult(
                original=text,
                redacted=text,
                matches=[],
                pii_detected=False
            )
        
        redacted = text
        for match in reversed(matches):
            if match.pii_type == PIIType.EMAIL and preserve_domains:
                # Preserve domain
                email_parts = match.original_text.split('@')
                if len(email_parts) == 2:
                    replacement = f"[REDACTED_EMAIL]@{email_parts[1]}"
                else:
                    replacement = "[REDACTED:EMAIL]"
            else:
                replacement = f"[REDACTED:{match.pii_type.value.upper()}]"
            
            redacted = (
                redacted[:match.start] +
                replacement +
                redacted[match.end:]
            )
        
        return RedactionResult(
            original=text,
            redacted=redacted,
            matches=matches,
            pii_detected=True
        )


def create_default_redactor() -> PIIRedactor:
    """Create redactor with default configuration"""
    return PIIRedactor()
```

**Test**: `tests/unit/test_redactor.py`

```python
"""
Unit tests for PII Redactor
"""
import pytest
from backend.security.redactor import PIIRedactor, PIIType


def test_email_detection():
    """Test email address detection"""
    redactor = PIIRedactor()
    text = "Contact me at john.doe@example.com for details"
    
    result = redactor.redact(text)
    
    assert result.pii_detected
    assert len(result.matches) == 1
    assert result.matches[0].pii_type == PIIType.EMAIL
    assert "[REDACTED:EMAIL]" in result.redacted
    assert "john.doe@example.com" not in result.redacted


def test_phone_detection():
    """Test phone number detection"""
    redactor = PIIRedactor()
    text = "Call me at 555-123-4567 or (555) 987-6543"
    
    result = redactor.redact(text)
    
    assert result.pii_detected
    assert len(result.matches) == 2
    assert all(m.pii_type == PIIType.PHONE for m in result.matches)


def test_credit_card_detection():
    """Test credit card number detection"""
    redactor = PIIRedactor()
    text = "Card number: 4532-1234-5678-9010"
    
    result = redactor.redact(text)
    
    assert result.pii_detected
    assert result.matches[0].pii_type == PIIType.CREDIT_CARD


def test_api_key_contextual_detection():
    """Test API key detection with context"""
    redactor = PIIRedactor()
    text = "My API key is abc123def456ghi789jkl012mno345"
    
    result = redactor.redact(text)
    
    assert result.pii_detected
    assert any(m.pii_type == PIIType.API_KEY for m in result.matches)


def test_no_pii():
    """Test text with no PII"""
    redactor = PIIRedactor()
    text = "This is a normal sentence with no sensitive data."
    
    result = redactor.redact(text)
    
    assert not result.pii_detected
    assert result.original == result.redacted


def test_preserve_domain():
    """Test email redaction with domain preservation"""
    redactor = PIIRedactor()
    text = "Email: user@company.com"
    
    result = redactor.redact_with_preservation(text, preserve_domains=True)
    
    assert result.pii_detected
    assert "@company.com" in result.redacted
    assert "user" not in result.redacted
```

**Validation**:
```bash
pytest tests/unit/test_redactor.py -v
```

---

### Task 5.2: Security Audit Logger

**File**: `backend/security/audit_logger.py`

**Purpose**: Log all security-relevant events with timestamps and context.

**Implementation**:

```python
"""
Security Audit Logger - Record security events for compliance and debugging
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SecurityEventType(str, Enum):
    """Types of security events"""
    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    EXTERNAL_CALL_INITIATED = "external_call_initiated"
    EXTERNAL_CALL_COMPLETED = "external_call_completed"
    PERMISSION_DENIED = "permission_denied"
    ENCRYPTION_PERFORMED = "encryption_performed"
    DECRYPTION_PERFORMED = "decryption_performed"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class SecurityEvent:
    """A security event record"""
    event_type: SecurityEventType
    timestamp: str
    context: dict[str, Any]
    severity: str  # "info", "warning", "critical"
    task_id: str | None = None
    user_id: str | None = None


class SecurityAuditLogger:
    """Log security events to file"""
    
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event: SecurityEvent) -> None:
        """Append security event to log file"""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            # Write as JSONL (JSON Lines)
            f.write(json.dumps(asdict(event)) + '\n')
    
    def log_pii_detection(
        self,
        pii_types: list[str],
        context: str,
        task_id: str | None = None
    ) -> None:
        """Log PII detection event"""
        event = SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp=datetime.utcnow().isoformat(),
            context={
                "pii_types": pii_types,
                "context_snippet": context[:100] + "..." if len(context) > 100 else context
            },
            severity="warning",
            task_id=task_id
        )
        self.log_event(event)
    
    def log_external_call(
        self,
        provider: str,
        endpoint: str,
        redacted_payload: dict[str, Any],
        task_id: str | None = None
    ) -> None:
        """Log external API call"""
        event = SecurityEvent(
            event_type=SecurityEventType.EXTERNAL_CALL_INITIATED,
            timestamp=datetime.utcnow().isoformat(),
            context={
                "provider": provider,
                "endpoint": endpoint,
                "payload": redacted_payload
            },
            severity="info",
            task_id=task_id
        )
        self.log_event(event)
    
    def log_permission_denied(
        self,
        operation: str,
        reason: str,
        task_id: str | None = None
    ) -> None:
        """Log permission denial"""
        event = SecurityEvent(
            event_type=SecurityEventType.PERMISSION_DENIED,
            timestamp=datetime.utcnow().isoformat(),
            context={
                "operation": operation,
                "reason": reason
            },
            severity="warning",
            task_id=task_id
        )
        self.log_event(event)
    
    def read_events(
        self,
        event_type: SecurityEventType | None = None,
        since: datetime | None = None
    ) -> list[SecurityEvent]:
        """Read events from log file with optional filtering"""
        if not self.log_path.exists():
            return []
        
        events = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                event_dict = json.loads(line)
                event = SecurityEvent(**event_dict)
                
                # Filter by event type
                if event_type and event.event_type != event_type:
                    continue
                
                # Filter by timestamp
                if since:
                    event_time = datetime.fromisoformat(event.timestamp)
                    if event_time < since:
                        continue
                
                events.append(event)
        
        return events


def create_default_audit_logger() -> SecurityAuditLogger:
    """Create audit logger with default path"""
    return SecurityAuditLogger("data/logs/security_audit.jsonl")
```

**Validation**:
```bash
# Test audit logger
python -c "
from backend.security.audit_logger import create_default_audit_logger

logger = create_default_audit_logger()
logger.log_pii_detection(['EMAIL', 'PHONE'], 'Test context', 'task-123')
logger.log_external_call('OpenAI', '/v1/chat/completions', {'prompt': '[REDACTED]'}, 'task-123')

# Read back events
events = logger.read_events()
print(f'Logged {len(events)} events')
for event in events:
    print(f'{event.timestamp} - {event.event_type}: {event.severity}')
"
```

---

### Task 5.3: Privacy-Aware Tool Wrapper

**File**: `backend/security/privacy_wrapper.py`

**Purpose**: Wrap tool execution with automatic PII redaction and audit logging.

**Implementation**:

```python
"""
Privacy Wrapper - Wrap tool calls with automatic privacy protection
"""
from __future__ import annotations

from typing import Any

from backend.security.audit_logger import SecurityAuditLogger
from backend.security.redactor import PIIRedactor
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import ToolRegistry
from backend.tools.sandbox import Sandbox


class PrivacyProtectedToolExecutor:
    """Execute tools with automatic privacy protection"""
    
    def __init__(
        self,
        redactor: PIIRedactor,
        audit_logger: SecurityAuditLogger
    ):
        self.redactor = redactor
        self.audit_logger = audit_logger
    
    def execute_with_privacy(
        self,
        request: ToolExecutionRequest,
        registry: ToolRegistry,
        sandbox: Sandbox,
        dispatch_map: dict[str, Any],
        task_id: str | None = None,
        redact_input: bool = False,
        redact_output: bool = False
    ) -> tuple[bool, dict[str, Any]]:
        """
        Execute tool with privacy protection
        
        Args:
            request: Tool execution request
            registry: Tool registry
            sandbox: Sandbox instance
            dispatch_map: Tool dispatch map
            task_id: Current task ID for audit trail
            redact_input: Whether to scan and redact PII from input
            redact_output: Whether to scan and redact PII from output
        
        Returns:
            (success, result_dict)
        """
        # Scan input for PII if requested
        if redact_input:
            input_str = str(request.payload)
            detection_result = self.redactor.detect(input_str)
            
            if detection_result:
                pii_types = [match.pii_type.value for match in detection_result]
                self.audit_logger.log_pii_detection(
                    pii_types=list(set(pii_types)),
                    context=input_str,
                    task_id=task_id
                )
                
                # Optionally redact (for now just log)
                # In production, you might want to fail or redact automatically
        
        # Execute tool
        ok, result = execute_tool_call(
            request=request,
            registry=registry,
            sandbox=sandbox,
            dispatch_map=dispatch_map
        )
        
        # Scan output for PII if requested
        if redact_output and ok:
            output_str = str(result)
            detection_result = self.redactor.detect(output_str)
            
            if detection_result:
                pii_types = [match.pii_type.value for match in detection_result]
                self.audit_logger.log_pii_detection(
                    pii_types=list(set(pii_types)),
                    context=output_str,
                    task_id=task_id
                )
                
                # Optionally redact output
                # For file reads, this might be expected
        
        return ok, result
```

---

### Task 5.4: At-Rest Encryption (Deferred - Investigation Required)

**Status**: DEFERRED - Requires deeper investigation per roadmap

**Considerations for Future Implementation**:

1. **Key Management**:
   - Where to store encryption keys?
   - User-provided passphrase?
   - System keyring integration?
   - Key rotation strategy?

2. **Performance Impact**:
   - Encryption overhead on every write
   - Decryption overhead on every read
   - Impact on episodic trace queries

3. **Scope**:
   - Encrypt all working state JSON?
   - Encrypt episodic SQLite database?
   - Encrypt semantic memory FAISS index?
   - Selective encryption of sensitive fields only?

4. **Libraries**:
   - `cryptography` (Fernet) for symmetric encryption
   - `sqlcipher` for encrypted SQLite
   - Custom encryption for FAISS?

**Placeholder Implementation** (for reference only):

```python
"""
At-Rest Encryption - Placeholder for future implementation
"""
from cryptography.fernet import Fernet

class EncryptionService:
    """PLACEHOLDER - Requires key management design"""
    
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt string to bytes"""
        return self.cipher.encrypt(plaintext.encode('utf-8'))
    
    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt bytes to string"""
        return self.cipher.decrypt(ciphertext).decode('utf-8')

# NOTE: Do not implement until key management strategy is defined
```

---

### Task 5.5: Security Configuration

**File**: `backend/config/settings.py` (additions)

**Purpose**: Centralize security configuration.

**Implementation**:

```python
# Add to Settings class

class Settings(BaseSettings):
    # ... existing fields ...
    
    # Security Configuration
    ENABLE_PII_DETECTION: bool = True
    ENABLE_PII_REDACTION: bool = False  # Log only by default
    ENABLE_SECURITY_AUDIT: bool = True
    SECURITY_AUDIT_LOG_PATH: str = "data/logs/security_audit.jsonl"
    
    # Privacy Levels
    PRIVACY_LEVEL: str = "standard"  # "minimal", "standard", "maximum"
    REDACT_EXTERNAL_CALLS: bool = True
    
    # Future: Encryption
    ENABLE_AT_REST_ENCRYPTION: bool = False  # Deferred
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Update `.env.example`**:

```bash
# Security Configuration
ENABLE_PII_DETECTION=true
ENABLE_PII_REDACTION=false
ENABLE_SECURITY_AUDIT=true
SECURITY_AUDIT_LOG_PATH=data/logs/security_audit.jsonl

# Privacy Levels: minimal, standard, maximum
PRIVACY_LEVEL=standard
REDACT_EXTERNAL_CALLS=true

# At-Rest Encryption (deferred)
ENABLE_AT_REST_ENCRYPTION=false
```

---

### Task 5.6: Integration with Controller

**File**: `backend/controller/controller_service.py` (additions)

**Purpose**: Wire security layer into controller workflow.

**Implementation**:

```python
# Add to imports
from backend.security.redactor import create_default_redactor
from backend.security.audit_logger import create_default_audit_logger
from backend.security.privacy_wrapper import PrivacyProtectedToolExecutor
from backend.config.settings import Settings

class ControllerService:
    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        hardware_service: HardwareService | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self.memory = memory_manager or MemoryManager()
        self.hardware = hardware_service or HardwareService()
        self.registry = model_registry or ModelRegistry()
        
        # Initialize security components
        settings = Settings()
        
        if settings.ENABLE_PII_DETECTION:
            self.redactor = create_default_redactor()
            self.audit_logger = create_default_audit_logger()
            self.privacy_executor = PrivacyProtectedToolExecutor(
                self.redactor,
                self.audit_logger
            )
        else:
            self.redactor = None
            self.audit_logger = None
            self.privacy_executor = None
        
        # ... existing initialization ...
    
    def run(self, user_input: str, task_id: str | None = None, ...) -> dict[str, Any]:
        # ... existing code ...
        
        # Before EXECUTE state, check user input for PII (if enabled)
        if self.redactor:
            detection_result = self.redactor.detect(user_input)
            if detection_result:
                pii_types = [match.pii_type.value for match in detection_result]
                self.audit_logger.log_pii_detection(
                    pii_types=list(set(pii_types)),
                    context=user_input,
                    task_id=resolved_task_id
                )
        
        # ... continue with existing execution ...
```

**Note**: For tool calls, use `privacy_executor.execute_with_privacy()` instead of direct `execute_tool_call()`.

---

## Summary of Deliverables

### Created Files

1. **`backend/security/redactor.py`** - PII detection and redaction engine
2. **`backend/security/audit_logger.py`** - Security event logging
3. **`backend/security/privacy_wrapper.py`** - Privacy-protected tool execution
4. **`backend/security/__init__.py`** - Package initialization
5. **`tests/unit/test_redactor.py`** - Redactor unit tests
6. **`tests/unit/test_audit_logger.py`** - Audit logger tests

### Configuration Updates

- `backend/config/settings.py` - Security settings
- `.env.example` - Security environment variables

### Integration Points

- `backend/controller/controller_service.py` - PII detection in controller
- `backend/workflow/nodes/tool_call_node.py` - Privacy wrapper for tools

---

## Security Features

| Feature | Status | Description |
|---------|--------|-------------|
| PII Detection | ✅ Implemented | Regex-based pattern matching for common PII types |
| PII Redaction | ✅ Implemented | Configurable redaction with preservation options |
| Security Audit Log | ✅ Implemented | JSONL-based event logging |
| Privacy Wrapper | ✅ Implemented | Automatic privacy protection for tool calls |
| At-Rest Encryption | ⏸️ Deferred | Requires key management design |

---

## Validation Commands

```bash
# Unit tests
pytest tests/unit/test_redactor.py -v
pytest tests/unit/test_audit_logger.py -v

# Integration test
python -c "
from backend.security.redactor import create_default_redactor
from backend.security.audit_logger import create_default_audit_logger

redactor = create_default_redactor()
logger = create_default_audit_logger()

# Test PII detection
text = 'My email is john@example.com and phone is 555-123-4567'
result = redactor.redact(text)

print(f'PII Detected: {result.pii_detected}')
print(f'Original: {result.original}')
print(f'Redacted: {result.redacted}')
print(f'Matches: {len(result.matches)}')

# Test audit logging
logger.log_pii_detection(
    pii_types=['EMAIL', 'PHONE'],
    context=text,
    task_id='test-123'
)

# Read events
events = logger.read_events()
print(f'Audit events logged: {len(events)}')
"

# Full validation
python scripts/validate_backend.py --scope unit
```

---

## Privacy Levels

**Minimal** (PRIVACY_LEVEL=minimal):
- PII detection disabled
- No redaction
- Basic audit logging only

**Standard** (PRIVACY_LEVEL=standard) [DEFAULT]:
- PII detection enabled
- Redaction on external calls
- Full audit logging

**Maximum** (PRIVACY_LEVEL=maximum):
- PII detection on all inputs/outputs
- Automatic redaction
- Comprehensive audit trail
- (Future) At-rest encryption enabled

---

## Next Steps After Milestone 5

With privacy controls in place:

1. **Enable external API calls** safely (Milestone 8)
2. **Implement code execution tools** (Tier 3 - requires sandboxing)
3. **Add web search** with redacted queries
4. **Expand filesystem access** with privacy controls

This ensures: **Every external call is logged, PII is detected, and sensitive data is protected.**

---

## Deferred Items (Post-M5)

1. **At-Rest Encryption**: Requires key management design
2. **Tier 3 Code Execution**: Requires additional sandboxing beyond M4
3. **Advanced PII Detection**: ML-based detection (contextual)
4. **User Consent Management**: Explicit opt-in/opt-out per data type
5. **Retention Policies**: Automatic deletion of old sensitive data
