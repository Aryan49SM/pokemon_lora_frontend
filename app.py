import streamlit as st
import requests
import base64
import time
import json

st.set_page_config(
    page_title="Pokémon Image Generator",
    page_icon="🐉",
    layout="centered"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF4B4B;
        text-align: center;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #FF4B4B;
    }
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>Pokémon Image Generator</h1>", unsafe_allow_html=True)

# VM IP Configuration
if 'vm_ip' not in st.session_state:
    st.session_state.vm_ip = ""

# VM IP input
with st.expander("Configure Backend"):
    vm_ip = st.text_input(
        "Enter Backend IP or Domain",
        value=st.session_state.vm_ip,
        help="Enter the public IP address or domain name of your Azure VM"
    )
    if vm_ip != st.session_state.vm_ip:
        st.session_state.vm_ip = vm_ip
        st.success("Backend address updated!")

# Define API URLs
API_URL = f"http://{st.session_state.vm_ip}:8000/generate-image" if st.session_state.vm_ip else ""
HEALTH_URL = f"http://{st.session_state.vm_ip}:8000/health" if st.session_state.vm_ip else ""

st.markdown("""
<div>
    <b>⚠️ Important:</b> Image generation may take <b>few minutes</b> depending on your server hardware. 
    Do not close this tab or refresh the page during generation.
</div>
""", unsafe_allow_html=True)

st.write("")
st.write("")
st.write("")

prompt = st.text_input(
    "Enter a prompt for the Pokémon image",
    value="A cartoon drawing of a blue Pokemon with wings and a fiery tail",
    help="Describe the Pokémon you want to generate"
)

# Backend status indicator
backend_status = st.empty()

# Check backend status if VM IP is provided
if st.session_state.vm_ip:
    with st.spinner("Checking backend status..."):
        try:
            response = requests.get(HEALTH_URL, timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("model") == "loaded":
                    backend_status.success("✅ Backend is online and model is loaded")
                else:
                    backend_status.warning("⚠️ Backend is online but model is not loaded yet")
            else:
                backend_status.error("⚠️ Backend is online but not responding correctly")
        except requests.exceptions.RequestException:
            backend_status.error("⚠️ Backend is offline. Please start your Azure VM.")
else:
    backend_status.warning("⚠️ Please configure the backend address in the settings above")

# Generation process
if 'generation_id' not in st.session_state:
    st.session_state.generation_id = None

# Generation process with long-running support
if st.button("Generate Image"):
    if not st.session_state.vm_ip:
        st.error("Please enter the backend address first")
        st.stop()
        
    with st.spinner("Generating image (this will take 6-10 minutes)..."):
        try:
            # Direct API call without threading - simplest approach
            start_time = time.time()
            
            # Make the request with a very generous timeout
            response = requests.post(
                API_URL,
                json={"prompt": prompt},
                timeout=1200  # 20 minutes timeout
            )
            
            # Process the response
            if response.status_code == 200:
                try:
                    # Parse the JSON response
                    response_data = response.json()
                    image_data = response_data["image"]
                    
                    # Calculate generation time
                    generation_time = int(time.time() - start_time)
                    
                    # Show success message
                    st.success(f"✨ Image generated in {generation_time} seconds")
                    
                    # Display the image
                    st.image(
                        f"data:image/png;base64,{image_data}",
                        caption=prompt,
                        use_container_width=True
                    )
                    
                    # Add download button
                    image_binary = base64.b64decode(image_data)
                    st.download_button(
                        label="Download Image",
                        data=image_binary,
                        file_name="generated_pokemon.png",
                        mime="image/png"
                    )
                except Exception as e:
                    st.error(f"Error processing image data: {str(e)}")
            else:
                st.error(f"Server returned status code {response.status_code}")
                
        except requests.exceptions.Timeout:
            st.error("Request timed out. The server might be taking too long to generate the image.")
        except requests.exceptions.ConnectionError:
            st.error("Connection error. Please check if the server is running.")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            
# Information section
with st.expander("About This App"):
    st.markdown("""
    ### How It Works
    
    This app generates custom Pokémon images based on your text descriptions using:
    
    - **Stable Diffusion**: A powerful text-to-image model
    - **LoRA fine-tuning**: Special training to create Pokémon-style images
    
    ### Using The App
    
    1. Enter the backend IP address (you'll need to start your Azure VM)
    2. Type a description of the Pokémon you want to create
    3. Click "Generate Image"
    4. **Wait patiently** - generation takes 10-15 minutes on CPU
    5. Download your creation!
    
    ### Important Notes
    
    - **Please be patient**: Image generation takes 10-15 minutes
    - **Do not refresh**: Refreshing the page will cancel your generation
    - The backend server may be offline to save costs - you'll need to start it
    - For better performance, consider using a GPU-enabled VM
    """)

# Footer
st.markdown("""
<div class="footer">
    <p>Made with ❤️ using Stable Diffusion + LoRA</p>
</div>
""", unsafe_allow_html=True)
