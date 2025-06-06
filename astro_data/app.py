# Make streamlit optional
try:
    import streamlit as st
    import os
    from dotenv import load_dotenv
    from page import Show_Factoryastro
    
    # Set page configuration
    st.set_page_config(
        page_title='Factory Astro',
        page_icon='🏭',
        layout='wide',
        initial_sidebar_state="collapsed"
    )
    
    # Load environment variables
    load_dotenv()
    if "OPENAI_API_KEY" not in st.session_state:
        st.session_state.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if st.session_state.OPENAI_API_KEY:
            print("OpenAI API key loaded successfully.")
        else:
            st.error("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")
except ImportError:
    # In API mode, we don't need the Streamlit UI
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Create dummy objects for API mode
    class DummyStreamlit:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
        
        @property
        def session_state(self):
            return {}
    
    st = DummyStreamlit()

# Display the Factory Astro page
Show_Factoryastro()
