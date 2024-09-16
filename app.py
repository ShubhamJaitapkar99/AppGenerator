import os
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
import requests
from io import BytesIO

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

def read_file(file):
    if file.type == "application/pdf":
        return read_pdf(file)
    elif file.type == "text/plain":
        return file.getvalue().decode("utf-8")
    else:
        raise ValueError("Unsupported file format. Please provide a PDF or text file.")

def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def parse_input(input_text):
    lines = input_text.split('\n')
    app_info = {}
    current_key = None
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            current_key = key.strip()
            app_info[current_key] = value.strip()
        elif current_key and line.strip():
            app_info[current_key] += ' ' + line.strip()
    expected_keys = ['Project name', 'Organization', 'Bundle Name', 'Platforms', 'Description', 'Primary functionality', 'Design Preferences', 'Color Scheme', 'Target Audience']
    for key in expected_keys:
        if key not in app_info:
            app_info[key] = ''
    return app_info

def get_openai_description(app_info):
    prompt = f"""
    Create a detailed description for the {app_info['Project name']} app based on the following information:
    {app_info}
    Include primary features, functionality, and target audience. Organize the description by potential app screens, Also keep this mind that this app is an idea and not in production yet So keep all the information in future tense.
    If design preferences and color scheme are provided, explain how they enhance the user experience.
    If any key information is missing, acknowledge this in your description and provide general suggestions based on common practices for similar apps.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def get_claude_response(prompt):
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text

def refine_with_claude(initial_description):
    prompt = f"""
    As an expert in prompt engineering, refine and improve the following app description. 
    Make it more concise, engaging, and marketable. Organize the description by potential app screens, 
    and include suggestions for UI design based on the app's functionality and target audience. 

    Initial description:
    {initial_description}

    Please provide:
    1. A refined app description
    2. Make the prompts so perfect that it is easier to create the UI design image.
    """
    return get_claude_response(prompt)

def generate_ui_design_description(refined_description):
    prompt = f"""
    Based on this refined app description, provide a detailed description of the UI design for the screens of the app. 
    Focus on the layout, color scheme, and key UI elements and feature functionality. Be specific about positions, sizes, and styling of elements.
    This description will be used to generate an image, so make it as visual and detailed as possible.
    Make the prompts so perfect that it is easier to create the UI design image.

    {refined_description}
    """
    return get_claude_response(prompt)

def summarize_description(refined_description):
    prompt = f"""
    Summarize the following UI design description in about 100 words, focusing on the most important visual elements and overall style:

    {refined_description}
    """
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_ui_image(refined_description):
    summary = summarize_description(refined_description)
    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=f"Create a detailed, professional UI design for a mobile app based on this description: {summary}. The image should show a clear, high-fidelity mockup of the main screen of the app.",
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    return image_url

def generate_flutter_code(ui_design):
    prompt = f"""
    Create a Flutter code structure for all the screens of the app based on this UI design description and feature functionality:

    {ui_design}

    Provide a correct, clean and dynamic well-structured Flutter code that implements the described UI design, elements and layout.
    """
    return get_claude_response(prompt)

def generate_react_native_code(ui_design):
    prompt = f"""
    Create a basic React Native code structure for the screens of the app based on this UI design description:

    {ui_design}

    Provide correct, clean and dynamic well-structured React Native code that implements the described UI design, elements and layout.
    """
    return get_claude_response(prompt)

def main():
    st.set_page_config(page_title="Advanced App Description and UI Generator", page_icon="📱", layout="wide")
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    h1 {
        color: #2C3E50;
        font-weight: 600;
    }
    h2 {
        color: #34495E;
        font-weight: 400;
    }
    .stButton > button {
        background-color: #3498DB;
        color: white;
        font-weight: 600;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #2980B9;
    }
    .css-1v0mbdj.etr89bj1 {
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .description-column {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        height: 100vh;
        overflow-y: auto;
    }
    .output-column {
        padding: 20px;
        height: 100vh;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📱 Advanced App Description and UI Generator")
    
    uploaded_file = st.file_uploader("Upload your app details (PDF or TXT)", type=["pdf", "txt"])

    if uploaded_file is not None:
        try:
            input_text = read_file(uploaded_file)
            app_info = parse_input(input_text)
            
            st.subheader("Application Details")
            for key, value in app_info.items():
                st.text(f"{key}: {value}")
            
            if st.button("Generate Description, UI Design, and Code"):
                with st.spinner("Creating app description, UI design, and code..."):
                    initial_description = get_openai_description(app_info)
                    refined_output = refine_with_claude(initial_description)
                    ui_design_description = generate_ui_design_description(refined_output)
                    ui_image_url = generate_ui_image(ui_design_description)
                    flutter_code = generate_flutter_code(ui_design_description)
                    react_native_code = generate_react_native_code(ui_design_description)
                
            
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown('<div class="description-column">', unsafe_allow_html=True)
                    
                    st.subheader("Refined App Description")
                    st.write(refined_output)
                    
                    st.subheader("UI Design Description")
                    st.write(ui_design_description)
                    
                    st.download_button(
                        label="Download Refined Description",
                        data=refined_output,
                        file_name="refined_app_description.txt",
                        mime="text/plain"
                    )
                    
                    st.download_button(
                        label="Download UI Design Description",
                        data=ui_design_description,
                        file_name="ui_design_description.txt",
                        mime="text/plain"
                    )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown('<div class="output-column">', unsafe_allow_html=True)
                    
                    st.subheader("UI Design")
                    st.image(ui_image_url, use_column_width=True)
                    
                    st.subheader("Flutter Code")
                    with st.expander("View Flutter Code"):
                        st.code(flutter_code, language='dart')
                    
                    st.subheader("React Native Code")
                    with st.expander("View React Native Code"):
                        st.code(react_native_code, language='jsx')
                    
                    st.download_button(
                        label="Download Flutter Code",
                        data=flutter_code,
                        file_name="app_ui.dart",
                        mime="text/plain"
                    )
                    
                    st.download_button(
                        label="Download React Native Code",
                        data=react_native_code,
                        file_name="AppComponent.jsx",
                        mime="text/plain"
                    )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()