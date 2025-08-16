from langchain_anthropic import ChatAnthropic
from langchain_litellm import ChatLiteLLM
import os


def get_default_model():
    """Mantiene compatibilità con il modello default Claude"""
    return ChatAnthropic(model_name="claude-sonnet-4-20250514", max_tokens=64000)


def get_model(model_spec=None):
    """
    Crea un modello basato sulla specifica fornita.
    
    Supporta:
    - None: usa il modello default (Claude)
    - Istanza di modello: ritorna direttamente
    - String con prefisso provider: usa LiteLLM
      - "openrouter/z-ai/glm-4.5"
      - "anthropic/claude-3.5-sonnet"
      - "azure/gpt-4"
      - etc.
    
    Args:
        model_spec: Specifica del modello (None, string, o istanza)
        
    Returns:
        Istanza del modello configurato
    """
    if model_spec is None:
        return get_default_model()
    
    # Se già un'istanza di modello
    if hasattr(model_spec, "invoke"):
        return model_spec
    
    # Usa LiteLLM per tutti i modelli string-based
    if isinstance(model_spec, str):
        # LiteLLM gestisce automaticamente il routing basato sul prefisso
        return ChatLiteLLM(
            model=model_spec,
            temperature=0.7,
            max_tokens=64000
        )
    
    return get_default_model()
