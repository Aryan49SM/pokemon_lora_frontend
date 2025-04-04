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
        
    # Check if backend is available
    try:
        response = requests.get(HEALTH_URL, timeout=10)
        if response.status_code != 200:
            st.error("⚠️ Backend is not responding correctly")
            st.stop()
    except requests.exceptions.RequestException:
        st.error("⚠️ Backend is offline. Please start your Azure VM.")
        st.stop()
        
    # Create progress bar
    progress_bar = st.progress(0)
    
    # Use threading to make API call in background
    import threading
    
    # Container to store API response
    result = {"response": None, "error": None, "done": False}
    
    # Function to call API
    def call_api():
        try:
            result["response"] = requests.post(
                API_URL,
                json={"prompt": prompt},
                timeout=900  # 15 minutes timeout (more than needed)
            )
        except Exception as e:
            result["error"] = e
        finally:
            result["done"] = True
    
    # Start API call in background
    api_thread = threading.Thread(target=call_api)
    api_thread.start()
    
    # Record start time
    start_time = time.time()
    
    # Simple progress bar for 10 minutes (600 seconds)
    max_wait = 600  # 10 minutes
    
    # Update progress bar every 3 seconds
    while not result["done"] and time.time() - start_time < max_wait:
        # Calculate progress as percentage of time passed
        elapsed = time.time() - start_time
        progress = min(99, int((elapsed / max_wait) * 100))
        progress_bar.progress(progress)
        time.sleep(3)  # Update every 3 seconds
    
    # Continue waiting if needed
    if not result["done"]:
        progress_bar.progress(99)  # Stay at 99%
        api_thread.join()  # Wait for thread to complete
    
    # Check for errors
    if result["error"]:
        st.error(f"Error: {str(result['error'])}")
        st.stop()
    
    # Get response
    response = result["response"]
    if not response:
        st.error("No response received from server")
        st.stop()
        
    if response.status_code != 200:
        st.error(f"Error: Server returned status code {response.status_code}")
        st.stop()
    
    # Process successful response
    try:
        image_data = response.json()["image"]
        
        # Complete progress bar
        progress_bar.progress(100)
        
        # Calculate generation time
        generation_time = int(time.time() - start_time)
        st.success(f"✨ Image generated in {generation_time} seconds")
        
        # Display image
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
        st.error(f"Error processing the image: {str(e)}")

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
