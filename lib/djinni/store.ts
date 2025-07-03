import { create } from "zustand"
import { persist } from "zustand/middleware"

export type DjinniModelType = "factory_astro" | "churn_astro" | "kg_insights" | "kginsights";

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
      predictionData?: any; // To store structured data for visualizations
    }>;
  }[];
  
  // Current session messages (not persisted between sessions)
  sessionMessages: {
    model: DjinniModelType;
    messages: Array<{
      role: "user" | "assistant";
      content: string;
      timestamp: number;
      predictionData?: any; // To store structured data for visualizations
    }>;
  }[];
  
    addMessage: (model: DjinniModelType, role: "user" | "assistant", content: string, predictionData?: any) => void;
  clearChatHistory: (model?: DjinniModelType) => void;
  clearSessionMessages: (model?: DjinniModelType) => void;
}

export const useDjinniStore = create<DjinniState>()(
  persist(
    (set, get) => ({
      activeModel: "factory_astro",
      setActiveModel: (model: DjinniModelType) => {
        if (model !== get().activeModel) {
          console.log(`Djinni store: Setting active model to ${model}`);
          set({ activeModel: model });
        }
      },
      
      isNewSession: true,
      startNewSession: (model?: DjinniModelType) => {
        console.log(`Starting new session${model ? ` for ${model}` : ''}`);
        set((state: DjinniState) => ({
          isNewSession: true,
          sessionMessages: model
            ? state.sessionMessages.filter(chat => chat.model !== model)
            : [],
        }));
      },
      
      chatHistory: [],
      sessionMessages: [],
      
      addMessage: (model: DjinniModelType, role: "user" | "assistant", content: string, predictionData?: any) =>
        set((state: DjinniState) => {
          const newMessage = {
            role,
            content,
            timestamp: Date.now(),
            predictionData,
          };

          const findAndUpdate = (
            chatList: typeof state.chatHistory, // Can use chatHistory type for both
            modelToUpdate: DjinniModelType
          ) => {
            const existingChat = chatList.find(chat => chat.model === modelToUpdate);
            if (existingChat) {
              return chatList.map(chat =>
                chat.model === modelToUpdate
                  ? { ...chat, messages: [...chat.messages, newMessage] }
                  : chat
              );
            } else {
              return [
                ...chatList,
                {
                  model: modelToUpdate,
                  messages: [newMessage],
                },
              ];
            }
          };

          return {
            isNewSession: false,
            chatHistory: findAndUpdate(state.chatHistory, model),
            sessionMessages: findAndUpdate(state.sessionMessages, model),
          };
        }),
      
      clearChatHistory: (model?: DjinniModelType) => 
        set((state: DjinniState) => ({
          chatHistory: model 
            ? state.chatHistory.filter(chat => chat.model !== model)
            : [],
        })),
        
      clearSessionMessages: (model?: DjinniModelType) => 
        set((state: DjinniState) => ({
          sessionMessages: model 
            ? state.sessionMessages.filter(chat => chat.model !== model)
            : [],
        })),
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
