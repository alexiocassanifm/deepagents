"""
Esempio di utilizzo di deepagents con z-ai/glm-4.5 tramite OpenRouter e LiteLLM.

Questo esempio mostra come:
1. Configurare l'API key di OpenRouter
2. Creare un agent con il modello z-ai/glm-4.5
3. Utilizzare l'agent per semplici conversazioni

Prerequisiti:
- Installare deepagents: pip install -e .
- Ottenere una API key da OpenRouter: https://openrouter.ai/
- Impostare la variabile d'ambiente OPENROUTER_API_KEY
"""

import os
from deepagents import create_deep_agent

def main():
    # Verifica che l'API key sia configurata
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ Errore: OPENROUTER_API_KEY non configurata")
        print("   Imposta la variabile d'ambiente o crea un file .env")
        return
    
    print("🤖 Creazione agent con z-ai/glm-4.5...")
    
    # Creare agent con z-ai/glm-4.5 tramite OpenRouter
    agent = create_deep_agent(
        tools=[],  # Nessun tool custom per questo esempio
        instructions="""You are a helpful assistant powered by GLM-4.5.
        
You should:
- Be helpful and informative
- Respond in the same language as the user's question
- Use your reasoning capabilities when needed
        """,
        model="openrouter/z-ai/glm-4.5"  # LiteLLM gestisce automaticamente OpenRouter
    )
    
    print("✅ Agent creato con successo!")
    print("💬 Prova alcune domande (digita 'quit' per uscire):\n")
    
    while True:
        user_input = input("Tu: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Arrivederci!")
            break
        
        try:
            print("🤔 GLM-4.5 sta pensando...")
            
            # Utilizzare l'agent
            result = agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })
            
            # Estrarre la risposta dal risultato
            if "messages" in result and len(result["messages"]) > 0:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    response = last_message.content
                else:
                    response = str(last_message)
            else:
                response = str(result)
            
            print(f"🤖 GLM-4.5: {response}\n")
            
        except Exception as e:
            print(f"❌ Errore: {e}\n")

if __name__ == "__main__":
    main()