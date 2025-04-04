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
        
    with st.spinner("Connecting to image generator..."):
        try:
            # Check if backend is available with a timeout
            response = requests.get(HEALTH_URL, timeout=10)
            backend_available = response.status_code == 200
        except requests.exceptions.RequestException:
            backend_available = False
            
        if not backend_available:
            st.error("⚠️ Image generator is currently offline. Please start your Azure VM.")
            st.stop()
        
        try:
            # Progress elements for long-running tasks
            progress_placeholder = st.empty()
            progress_bar = progress_placeholder.progress(0)
            status_text = st.empty()
            
            # Start timing
            start_time = time.time()
            
            # Make one API call - this is the ONLY place we call the API
            import threading
            
            # Container to store API response and status
            result_container = {"response": None, "error": None, "completed": False}
            
            def make_api_call():
                try:
                    result_container["response"] = requests.post(
                        API_URL,
                        json={"prompt": prompt},
                        timeout=1800  # 30 minutes in seconds
                    )
                except Exception as e:
                    result_container["error"] = e
                finally:
                    result_container["completed"] = True
            
            # Start the API call in background
            api_thread = threading.Thread(target=make_api_call)
            api_thread.start()
            
            # Status messages
            status_messages = [
                "Initializing generation process...",
                "Starting to create your Pokémon...",
                "Building the basic shape...",
                "Adding colors and patterns...",
                "Working on the details...",
                "Generating image features...",
                "Refining your Pokémon image...",
                "Almost done! Finalizing image...",
                "Waiting for the server to respond...",
                "Still waiting - image generation can take 15-20 minutes...",
                "Please continue to wait - complex images take time...",
                "Image is being processed by the server..."
            ]
            
            # MUCH slower progress bar - configured for very long wait times
            max_wait_seconds = 1500  # 25 minutes
            
            # Calculate timing parameters
            total_steps = 100
            time_per_step = max_wait_seconds / total_steps
            
            # Determines how slowly the progress bar moves - higher = slower
            slowness_factor = 3
            
            # Run a loop that progresses very slowly
            for step in range(1, total_steps + 1):
                # Stop if we've got a response
                if result_container["completed"]:
                    # Immediately jump to 100%
                    progress_bar.progress(100)
                    break
                
                # Calculate progress - be conservative so we don't hit 100% too soon
                progress = min(95, step * (95 / total_steps))
                progress_bar.progress(int(progress))
                
                # Show status messages - cycle through them based on progress
                message_index = int((step / total_steps) * len(status_messages))
                if message_index >= len(status_messages):
                    message_index = len(status_messages) - 1
                status_text.info(status_messages[message_index])
                
                # Sleep for longer periods to make the progress bar move very slowly
                # This means we'll wait for the API response for up to max_wait_seconds
                time.sleep(time_per_step * slowness_factor)
                
                # Check if we've waited too long
                if time.time() - start_time > max_wait_seconds:
                    # Don't give up! Just stop advancing the progress bar but keep waiting
                    status_text.warning("Taking longer than expected, but still waiting...")
                    # Wait for completion with periodic checks
                    while not result_container["completed"]:
                        time.sleep(5)
                    break
            
            # Process the response (after the thread finishes)
            if result_container["error"]:
                raise result_container["error"]
                
            response = result_container["response"]
            
            if response and response.status_code == 200:
                image_data = response.json()["image"]
                
                # Clear progress indicators
                progress_placeholder.empty()
                status_text.empty()
                
                # Calculate and display generation time
                generation_time = int(time.time() - start_time)
                st.success(f"✨ Image generated successfully in {generation_time} seconds!")
                
                # Display the image
                st.image(
                    f"data:image/png;base64,{image_data}",
                    caption=prompt,
                    use_container_width=True
                )

                # Convert base64 string back to binary data for download
                image_binary = base64.b64decode(image_data)
                
                # Download button with binary data
                st.download_button(
                    label="Download Image",
                    data=image_binary,
                    file_name="generated_pokemon.png",
                    mime="image/png"
                )
            elif response:
                st.error(f"Error: Server returned status code {response.status_code}")
            else:
                st.error("No response received from the server")
                
        except requests.exceptions.Timeout:
            st.error("⚠️ The request timed out after 25 minutes. The server may be overloaded.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error communicating with the image generator: {str(e)}")
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
