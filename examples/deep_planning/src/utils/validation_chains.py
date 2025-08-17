"""
Validation Chains - Complete error handling and validation system

This module provides comprehensive validation chains for ensuring
data integrity and proper error handling throughout the deep planning system.

Key Features:
1. Chain-of-responsibility pattern for validation
2. Complete error handling with recovery strategies
3. Context validation at multiple levels
4. Integration with logging and monitoring
5. Graceful degradation on validation failures
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    CRITICAL = "critical"  # Must pass or operation fails
    WARNING = "warning"    # Should pass but can continue
    INFO = "info"         # Informational only


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, 
                 valid: bool,
                 level: ValidationLevel = ValidationLevel.INFO,
                 message: str = "",
                 errors: List[str] = None,
                 warnings: List[str] = None,
                 data: Dict[str, Any] = None):
        self.valid = valid
        self.level = level
        self.message = message
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "valid": self.valid,
            "level": self.level.value,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data
        }


class Validator(ABC):
    """Abstract base class for validators."""
    
    def __init__(self, name: str, level: ValidationLevel = ValidationLevel.WARNING):
        self.name = name
        self.level = level
        self.next_validator: Optional[Validator] = None
    
    def set_next(self, validator: 'Validator') -> 'Validator':
        """Set the next validator in the chain."""
        self.next_validator = validator
        return validator
    
    @abstractmethod
    def validate(self, data: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Perform validation."""
        pass
    
    def handle(self, data: Any, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """Handle validation and pass to next in chain."""
        results = []
        
        try:
            result = self.validate(data, context)
            results.append(result)
            
            # Log validation result
            if not result.valid:
                if result.level == ValidationLevel.CRITICAL:
                    logger.error(f"Validation failed [{self.name}]: {result.message}")
                elif result.level == ValidationLevel.WARNING:
                    logger.warning(f"Validation warning [{self.name}]: {result.message}")
                else:
                    logger.info(f"Validation info [{self.name}]: {result.message}")
            
            # Continue chain if not critical failure
            if self.next_validator and (result.valid or result.level != ValidationLevel.CRITICAL):
                next_results = self.next_validator.handle(data, context)
                results.extend(next_results)
                
        except Exception as e:
            # Complete error handling - log and create result
            logger.error(f"Validation error in {self.name}: {e}", exc_info=True)
            results.append(ValidationResult(
                valid=False,
                level=self.level,
                message=f"Validation failed with exception: {str(e)}",
                errors=[str(e)]
            ))
            
            # Continue chain if not critical
            if self.next_validator and self.level != ValidationLevel.CRITICAL:
                try:
                    next_results = self.next_validator.handle(data, context)
                    results.extend(next_results)
                except Exception as chain_error:
                    logger.error(f"Chain continuation failed: {chain_error}")
        
        return results


class ContextValidator(Validator):
    """Validates context size and utilization."""
    
    def __init__(self, max_tokens: int = 50000, warning_threshold: float = 0.8):
        super().__init__("context_validator", ValidationLevel.WARNING)
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
    
    def validate(self, data: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate context size and utilization."""
        if not isinstance(data, dict) or 'messages' not in data:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message="No messages to validate"
            )
        
        messages = data.get('messages', [])
        
        # Estimate token count
        total_tokens = sum(len(str(m)) // 4 for m in messages)
        utilization = total_tokens / self.max_tokens
        
        if utilization > 1.0:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Context exceeds maximum ({total_tokens}/{self.max_tokens} tokens)",
                errors=[f"Token overflow: {total_tokens - self.max_tokens} tokens over limit"],
                data={"tokens": total_tokens, "utilization": utilization}
            )
        elif utilization > self.warning_threshold:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.WARNING,
                message=f"High context utilization: {utilization:.1%}",
                warnings=[f"Approaching token limit ({total_tokens}/{self.max_tokens})"],
                data={"tokens": total_tokens, "utilization": utilization}
            )
        else:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message=f"Context within limits: {utilization:.1%}",
                data={"tokens": total_tokens, "utilization": utilization}
            )


class MessageStructureValidator(Validator):
    """Validates message structure and format."""
    
    def __init__(self):
        super().__init__("message_structure_validator", ValidationLevel.WARNING)
    
    def validate(self, data: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate message structure."""
        if not isinstance(data, dict) or 'messages' not in data:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message="Invalid data structure: missing messages",
                errors=["Expected dict with 'messages' key"]
            )
        
        messages = data.get('messages', [])
        errors = []
        warnings = []
        
        for i, msg in enumerate(messages):
            # Check required fields
            if not isinstance(msg, dict):
                errors.append(f"Message {i} is not a dictionary")
                continue
            
            if 'role' not in msg:
                errors.append(f"Message {i} missing 'role' field")
            elif msg['role'] not in ['user', 'assistant', 'system', 'tool']:
                warnings.append(f"Message {i} has unusual role: {msg['role']}")
            
            if 'content' not in msg and 'tool_calls' not in msg:
                errors.append(f"Message {i} missing content or tool_calls")
        
        if errors:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message="Message structure validation failed",
                errors=errors,
                warnings=warnings
            )
        elif warnings:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message="Message structure valid with warnings",
                warnings=warnings
            )
        else:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message="Message structure valid"
            )


class PhaseTransitionValidator(Validator):
    """Validates phase transitions in the deep planning system."""
    
    def __init__(self):
        super().__init__("phase_transition_validator", ValidationLevel.CRITICAL)
    
    def validate(self, data: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate phase transition requirements."""
        if not context or 'phase_transition' not in context:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message="No phase transition to validate"
            )
        
        transition = context['phase_transition']
        from_phase = transition.get('from')
        to_phase = transition.get('to')
        
        # Define valid transitions
        valid_transitions = {
            'investigation': ['discussion'],
            'discussion': ['planning'],
            'planning': ['execution'],
            'execution': ['complete']
        }
        
        if from_phase not in valid_transitions:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Invalid source phase: {from_phase}",
                errors=[f"Unknown phase: {from_phase}"]
            )
        
        if to_phase not in valid_transitions[from_phase]:
            return ValidationResult(
                valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Invalid transition: {from_phase} -> {to_phase}",
                errors=[f"Cannot transition from {from_phase} to {to_phase}"]
            )
        
        # Check phase completion criteria
        if 'completion_criteria' in transition:
            criteria = transition['completion_criteria']
            missing = [c for c in criteria if not criteria[c]]
            
            if missing:
                return ValidationResult(
                    valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Incomplete phase criteria",
                    warnings=[f"Missing: {', '.join(missing)}"]
                )
        
        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message=f"Valid transition: {from_phase} -> {to_phase}"
        )


class CompressionValidator(Validator):
    """Validates compression operations and results."""
    
    def __init__(self):
        super().__init__("compression_validator", ValidationLevel.WARNING)
    
    def validate(self, data: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate compression result."""
        if not context or 'compression_result' not in context:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.INFO,
                message="No compression result to validate"
            )
        
        result = context['compression_result']
        
        # Check compression success
        if not result.get('success', False):
            return ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message="Compression failed",
                errors=[result.get('error', 'Unknown error')]
            )
        
        # Check reduction percentage
        reduction = result.get('reduction_percentage', 0)
        if reduction < 10:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.WARNING,
                message=f"Low compression ratio: {reduction:.1f}%",
                warnings=["Compression may not be effective"]
            )
        elif reduction > 90:
            return ValidationResult(
                valid=True,
                level=ValidationLevel.WARNING,
                message=f"Very high compression ratio: {reduction:.1f}%",
                warnings=["Possible information loss"]
            )
        
        return ValidationResult(
            valid=True,
            level=ValidationLevel.INFO,
            message=f"Compression successful: {reduction:.1f}% reduction",
            data={"reduction_percentage": reduction}
        )


class ValidationChain:
    """Manages a chain of validators."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.validators: List[Validator] = []
        self.head: Optional[Validator] = None
    
    def add_validator(self, validator: Validator) -> 'ValidationChain':
        """Add a validator to the chain."""
        if not self.head:
            self.head = validator
        elif self.validators:
            self.validators[-1].set_next(validator)
        
        self.validators.append(validator)
        return self
    
    def validate(self, data: Any, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the validation chain."""
        if not self.head:
            return {
                "valid": True,
                "message": "No validators configured",
                "results": []
            }
        
        try:
            results = self.head.handle(data, context)
            
            # Aggregate results
            all_valid = all(r.valid or r.level != ValidationLevel.CRITICAL for r in results)
            all_errors = []
            all_warnings = []
            
            for result in results:
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
            
            return {
                "valid": all_valid,
                "message": "Validation complete" if all_valid else "Validation failed",
                "errors": all_errors,
                "warnings": all_warnings,
                "results": [r.to_dict() for r in results],
                "chain": self.name
            }
            
        except Exception as e:
            logger.error(f"Validation chain failed: {e}", exc_info=True)
            return {
                "valid": False,
                "message": f"Validation chain error: {str(e)}",
                "errors": [str(e)],
                "warnings": [],
                "results": [],
                "chain": self.name
            }


def create_default_validation_chain() -> ValidationChain:
    """Create the default validation chain for the system."""
    chain = ValidationChain("default")
    
    # Add validators in order of execution
    chain.add_validator(MessageStructureValidator())
    chain.add_validator(ContextValidator())
    chain.add_validator(PhaseTransitionValidator())
    chain.add_validator(CompressionValidator())
    
    return chain


def create_strict_validation_chain() -> ValidationChain:
    """Create a strict validation chain with all checks as critical."""
    chain = ValidationChain("strict")
    
    # Create validators with critical level
    structure_validator = MessageStructureValidator()
    structure_validator.level = ValidationLevel.CRITICAL
    
    context_validator = ContextValidator(max_tokens=40000, warning_threshold=0.7)
    context_validator.level = ValidationLevel.CRITICAL
    
    chain.add_validator(structure_validator)
    chain.add_validator(context_validator)
    chain.add_validator(PhaseTransitionValidator())
    
    return chain


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create validation chain
    chain = create_default_validation_chain()
    
    # Test data
    test_data = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
    }
    
    # Test context
    test_context = {
        "phase_transition": {
            "from": "investigation",
            "to": "discussion",
            "completion_criteria": {
                "findings_documented": True,
                "tools_explored": True
            }
        }
    }
    
    # Run validation
    result = chain.validate(test_data, test_context)
    
    print("Validation Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Message: {result['message']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    if result['warnings']:
        print(f"  Warnings: {result['warnings']}")
    
    # Test with invalid data
    invalid_data = {
        "messages": [
            {"content": "Missing role field"},
            "Not a dictionary"
        ]
    }
    
    result = chain.validate(invalid_data)
    print("\nInvalid Data Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Errors: {result['errors']}")