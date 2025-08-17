"""
Model-Specific Compatibility System for DeepAgents

This module provides model-specific compatibility configurations and automatic
detection of models that require tool compatibility fixes.

Key Features:
- Registry of known problematic models
- Automatic model detection and compatibility fix application
- Configuration for model-specific behaviors
- Easy addition of new models and fixes
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

compatibility_logger = logging.getLogger("deepagents.compatibility")


class CompatibilityLevel(Enum):
    """Levels of compatibility fixes needed."""
    NONE = "none"           # Model works perfectly
    MINIMAL = "minimal"     # Minor fixes needed
    MODERATE = "moderate"   # Several fixes needed
    EXTENSIVE = "extensive" # Many fixes required


@dataclass
class ModelCompatibilityProfile:
    """Configuration profile for a specific model."""
    name: str
    patterns: List[str]                    # Regex patterns to match model names
    compatibility_level: CompatibilityLevel
    known_issues: List[str]               # Description of known issues
    fixes_needed: Set[str]                # Set of fix names to apply
    notes: str = ""                       # Additional notes about the model
    
    def matches_model(self, model_name: str) -> bool:
        """Check if this profile matches the given model name."""
        if not model_name:
            return False
        
        model_name_lower = model_name.lower()
        
        # Check exact name match first
        if self.name.lower() == model_name_lower:
            return True
        
        # Check regex patterns
        for pattern in self.patterns:
            if re.search(pattern.lower(), model_name_lower):
                return True
        
        return False


class ModelCompatibilityRegistry:
    """Registry of model compatibility profiles."""
    
    def __init__(self):
        self.profiles: List[ModelCompatibilityProfile] = []
        self._setup_default_profiles()
    
    def _setup_default_profiles(self):
        """Setup default compatibility profiles for known models."""
        
        # Models known to have JSON string serialization issues
        problematic_models = [
            ModelCompatibilityProfile(
                name="gpt-3.5-turbo",
                patterns=[r"gpt-3\.5", r"gpt35"],
                compatibility_level=CompatibilityLevel.MODERATE,
                known_issues=[
                    "Serializes list parameters as JSON strings",
                    "Inconsistent tool call formatting"
                ],
                fixes_needed={"write_todos_json_fix"},
                notes="Earlier GPT models often serialize complex parameters as JSON strings"
            ),
            
            ModelCompatibilityProfile(
                name="gpt-4-turbo",
                patterns=[r"gpt-4.*turbo", r"gpt4.*turbo"],
                compatibility_level=CompatibilityLevel.MINIMAL,
                known_issues=[
                    "Occasional JSON string serialization for complex lists"
                ],
                fixes_needed={"write_todos_json_fix"},
                notes="Generally good but occasionally sends JSON strings for complex parameters"
            ),
            
            ModelCompatibilityProfile(
                name="claude-3-haiku",
                patterns=[r"claude.*3.*haiku", r"claude-3-haiku"],
                compatibility_level=CompatibilityLevel.MINIMAL,
                known_issues=[
                    "Sometimes sends JSON strings for list parameters"
                ],
                fixes_needed={"write_todos_json_fix"},
                notes="Haiku model occasionally has tool parameter serialization issues"
            ),
            
            ModelCompatibilityProfile(
                name="claude-3-sonnet",
                patterns=[r"claude.*3.*sonnet", r"claude-3-sonnet"],
                compatibility_level=CompatibilityLevel.NONE,
                known_issues=[],
                fixes_needed=set(),
                notes="Generally excellent tool calling, no known issues"
            ),
            
            ModelCompatibilityProfile(
                name="claude-3-opus",
                patterns=[r"claude.*3.*opus", r"claude-3-opus"],
                compatibility_level=CompatibilityLevel.NONE,
                known_issues=[],
                fixes_needed=set(),
                notes="Excellent tool calling, no known issues"
            ),
            
            ModelCompatibilityProfile(
                name="claude-3.5-sonnet",
                patterns=[r"claude.*3\.5.*sonnet", r"claude-3\.5-sonnet"],
                compatibility_level=CompatibilityLevel.NONE,
                known_issues=[],
                fixes_needed=set(),
                notes="Latest Claude model with excellent tool calling"
            ),
            
            # Placeholder for other models that might have issues
            ModelCompatibilityProfile(
                name="llama-based-models",
                patterns=[r"llama", r"alpaca", r"vicuna"],
                compatibility_level=CompatibilityLevel.EXTENSIVE,
                known_issues=[
                    "Tool calling support varies",
                    "May require function calling format adaptation"
                ],
                fixes_needed={"write_todos_json_fix", "function_calling_format"},
                notes="Open source models may need extensive compatibility fixes"
            ),
            
            ModelCompatibilityProfile(
                name="unknown-models",
                patterns=[r".*"],  # Catch-all pattern
                compatibility_level=CompatibilityLevel.MINIMAL,
                known_issues=[
                    "Unknown model behavior"
                ],
                fixes_needed={"write_todos_json_fix"},
                notes="Default profile for unknown models - applies basic fixes"
            )
        ]
        
        self.profiles.extend(problematic_models)
    
    def get_profile_for_model(self, model_name: str) -> Optional[ModelCompatibilityProfile]:
        """
        Get the compatibility profile for a given model.
        
        Args:
            model_name: Name of the model to look up
            
        Returns:
            ModelCompatibilityProfile if found, None otherwise
        """
        if not model_name:
            return None
        
        # Find the most specific match (not the catch-all)
        for profile in self.profiles:
            if profile.name != "unknown-models" and profile.matches_model(model_name):
                return profile
        
        # Fall back to unknown-models profile
        for profile in self.profiles:
            if profile.name == "unknown-models":
                return profile
        
        return None
    
    def register_model(self, profile: ModelCompatibilityProfile):
        """Register a new model compatibility profile."""
        # Remove existing profile with same name
        self.profiles = [p for p in self.profiles if p.name != profile.name]
        # Insert before the catch-all pattern
        insert_index = len(self.profiles) - 1 if self.profiles else 0
        self.profiles.insert(insert_index, profile)
        
        compatibility_logger.info(f"Registered new model profile: {profile.name}")
    
    def list_known_models(self) -> List[str]:
        """List all known model names."""
        return [profile.name for profile in self.profiles if profile.name != "unknown-models"]


def detect_model_from_environment() -> Optional[str]:
    """
    Detect the current model from environment variables.
    
    Returns:
        Model name if detected, None otherwise
    """
    # Check common environment variables
    model_env_vars = [
        "DEEPAGENTS_MODEL",
        "ANTHROPIC_MODEL", 
        "OPENAI_MODEL",
        "MODEL_NAME",
        "LLM_MODEL"
    ]
    
    for env_var in model_env_vars:
        model = os.getenv(env_var)
        if model:
            compatibility_logger.debug(f"Detected model from {env_var}: {model}")
            return model
    
    return None


def should_apply_compatibility_fixes(model_name: str, registry: ModelCompatibilityRegistry = None) -> bool:
    """
    Determine if compatibility fixes should be applied for a given model.
    
    Args:
        model_name: Name of the model
        registry: Optional custom registry, uses default if None
        
    Returns:
        True if fixes should be applied
    """
    if not registry:
        registry = ModelCompatibilityRegistry()
    
    profile = registry.get_profile_for_model(model_name)
    if not profile:
        # Unknown model, apply fixes as precaution
        return True
    
    return profile.compatibility_level != CompatibilityLevel.NONE


def get_required_fixes(model_name: str, registry: ModelCompatibilityRegistry = None) -> Set[str]:
    """
    Get the set of fixes required for a given model.
    
    Args:
        model_name: Name of the model
        registry: Optional custom registry, uses default if None
        
    Returns:
        Set of fix names to apply
    """
    if not registry:
        registry = ModelCompatibilityRegistry()
    
    profile = registry.get_profile_for_model(model_name)
    if not profile:
        # Unknown model, apply basic fixes
        return {"write_todos_json_fix"}
    
    return profile.fixes_needed


def print_model_compatibility_report(model_name: str, registry: ModelCompatibilityRegistry = None):
    """
    Print a compatibility report for a given model.
    
    Args:
        model_name: Name of the model to report on
        registry: Optional custom registry, uses default if None
    """
    if not registry:
        registry = ModelCompatibilityRegistry()
    
    profile = registry.get_profile_for_model(model_name)
    
    print(f"\n🤖 Model Compatibility Report: {model_name}")
    print("=" * 50)
    
    if not profile:
        print("❓ Unknown model - no specific profile found")
        print("🔧 Will apply default compatibility fixes as precaution")
        return
    
    print(f"📋 Profile: {profile.name}")
    print(f"🎯 Compatibility Level: {profile.compatibility_level.value}")
    
    if profile.known_issues:
        print(f"⚠️  Known Issues:")
        for issue in profile.known_issues:
            print(f"   • {issue}")
    else:
        print("✅ No known issues")
    
    if profile.fixes_needed:
        print(f"🔧 Fixes Applied:")
        for fix in profile.fixes_needed:
            print(f"   • {fix}")
    else:
        print("✨ No fixes needed")
    
    if profile.notes:
        print(f"📝 Notes: {profile.notes}")
    
    print()


# Global registry instance
default_registry = ModelCompatibilityRegistry()


# Example usage and testing
if __name__ == "__main__":
    # Test model detection
    registry = ModelCompatibilityRegistry()
    
    test_models = [
        "gpt-3.5-turbo",
        "claude-3-sonnet-20240229",
        "gpt-4-turbo-preview",
        "claude-3.5-sonnet-20241022",
        "unknown-model-name"
    ]
    
    for model in test_models:
        print_model_compatibility_report(model, registry)
    
    # Test environment detection
    detected_model = detect_model_from_environment()
    if detected_model:
        print(f"🔍 Detected model from environment: {detected_model}")
        print_model_compatibility_report(detected_model, registry)