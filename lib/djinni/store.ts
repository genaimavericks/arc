import { create } from "zustand"
import { persist } from "zustand/middleware"

export type DjinniModelType = "factory_astro" | "churn_astro";

export interface DjinniState {
  // Selected model configuration
  activeModel: DjinniModelType;
  setActiveModel: (model: DjinniModelType) => void;
  
  // Session management
  isNewSession: boolean;
  startNewSession: (model?: DjinniModelType) => void;
  
  // Chat history
  chatHistory: {
    model: DjinniModelType;
    messages: Array<{
      role: "user" | "assistant";
      content: string;
      timestamp: number;
    }>;
  }[];
  
  // Current session messages (not persisted between sessions)
  sessionMessages: {
    model: DjinniModelType;
    messages: Array<{
      role: "user" | "assistant";
      content: string;
      timestamp: number;
    }>;
  }[];
  
  addMessage: (model: DjinniModelType, role: "user" | "assistant", content: string) => void;
  clearChatHistory: (model?: DjinniModelType) => void;
  clearSessionMessages: (model?: DjinniModelType) => void;
}

export const useDjinniStore = create<DjinniState>()(
  persist(
    (set, get) => ({
      // Default to factory_astro as the active model
      activeModel: "factory_astro",
      setActiveModel: (model) => {
        // Only update if the model has actually changed
        if (model !== get().activeModel) {
          console.log(`Djinni store: Setting active model to ${model}`);
          set({ activeModel: model });
        }
      },
      
      // Session management
      isNewSession: true,
      startNewSession: (model) => {
        console.log(`Starting new session${model ? ` for ${model}` : ''}`);
        set((state) => ({
          isNewSession: true,
          // Clear session messages for the specified model or all models
          sessionMessages: model
            ? state.sessionMessages.filter(chat => chat.model !== model)
            : []
        }));
      },
      
      // Initialize empty chat history
      chatHistory: [],
      
      // Initialize empty session messages
      sessionMessages: [],
      
      // Add a message to both chat history and current session
      addMessage: (model, role, content) => 
        set((state) => {
          // Create the new message
          const newMessage = {
            role,
            content,
            timestamp: Date.now()
          };
          
          // Update persistent chat history
          const existingModelChat = state.chatHistory.find(chat => chat.model === model);
          const updatedChatHistory = existingModelChat
            ? state.chatHistory.map(chat => 
                chat.model === model 
                  ? { ...chat, messages: [...chat.messages, newMessage] }
                  : chat
              )
            : [
                ...state.chatHistory,
                {
                  model,
                  messages: [newMessage]
                }
              ];
          
          // Update current session messages
          const existingSessionChat = state.sessionMessages.find(chat => chat.model === model);
          const updatedSessionMessages = existingSessionChat
            ? state.sessionMessages.map(chat => 
                chat.model === model 
                  ? { ...chat, messages: [...chat.messages, newMessage] }
                  : chat
              )
            : [
                ...state.sessionMessages,
                {
                  model,
                  messages: [newMessage]
                }
              ];
          
          // Set isNewSession to false once we add a message
          return {
            isNewSession: false,
            chatHistory: updatedChatHistory,
            sessionMessages: updatedSessionMessages
          };
        }),
      
      // Clear chat history for a specific model or all models
      clearChatHistory: (model) => 
        set((state) => ({
          chatHistory: model 
            ? state.chatHistory.filter(chat => chat.model !== model)
            : []
        })),
        
      // Clear session messages for a specific model or all models
      clearSessionMessages: (model) => 
        set((state) => ({
          sessionMessages: model 
            ? state.sessionMessages.filter(chat => chat.model !== model)
            : []
        }))
    }),
    {
      name: "djinni-storage",
      // Only persist these fields
      partialize: (state) => ({
        activeModel: state.activeModel,
        chatHistory: state.chatHistory
        // Intentionally not persisting sessionMessages and isNewSession
      })
    }
  )
);
