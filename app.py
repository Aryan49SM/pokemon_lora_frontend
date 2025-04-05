import streamlit as st
import requests
import base64
import time
import json
import io
from PIL import Image
import streamlit.components.v1 as components

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
        color: white !important;
        border-radius: 5px;
        border: 1px solid #FF4B4B;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #E43B3B;
        color: white !important;
        border-color: #E43B3B;
    }
    .stButton>button:active {
        background-color: #D22B2B;
        color: white !important;
        border-color: #D22B2B;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'vm_ip' not in st.session_state:
    st.session_state.vm_ip = ""
if 'image_data' not in st.session_state:
    st.session_state.image_data = None
if 'image_binary' not in st.session_state:
    st.session_state.image_binary = None
if 'prompt_used' not in st.session_state:
    st.session_state.prompt_used = ""
if 'task_id' not in st.session_state:
    st.session_state.task_id = None
if 'task_status' not in st.session_state:
    st.session_state.task_status = None
if 'generation_started' not in st.session_state:
    st.session_state.generation_started = None
if 'last_status_check' not in st.session_state:
    st.session_state.last_status_check = 0
if 'end_time' not in st.session_state:
    st.session_state.end_time = None
if 'check_trigger' not in st.session_state:
    st.session_state.check_trigger = False  # Trigger for JavaScript to update

st.markdown("<h1 class='main-header'>Pokémon Image Generator</h1>", unsafe_allow_html=True)

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
def get_api_urls():
    base_url = f"http://{st.session_state.vm_ip}:8000"
    return {
        "health": f"{base_url}/health",
        "direct_generate": f"{base_url}/generate-image",
        "start_generate": f"{base_url}/start-generation",
        "task_status": f"{base_url}/task-status",
        "get_image": f"{base_url}/get-image",
        "cleanup": f"{base_url}/cleanup-task"
    }

st.markdown("""
<div>
    <b>⚠️ Important:</b> Image generation may take <b>7-8 minutes</b> depending on your server hardware. 
    You can safely leave this page and return later to check your results.
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
    urls = get_api_urls()
    with st.spinner("Checking backend status..."):
        try:
            response = requests.get(urls["health"], timeout=10)
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

# Reset task
if st.button("Reset Generation"):
    if st.session_state.task_id:
        try:
            urls = get_api_urls()
            requests.delete(f"{urls['cleanup']}/{st.session_state.task_id}", timeout=5)
        except:
            pass
    st.session_state.task_id = None
    st.session_state.task_status = None
    st.session_state.generation_started = None
    st.session_state.image_data = None
    st.session_state.image_binary = None
    st.session_state.prompt_used = ""
    st.rerun()

# Generation process
if st.button("Generate Image"):
    if not st.session_state.vm_ip:
        st.error("Please enter the backend address first")
        st.stop()
    
    urls = get_api_urls()
    try:
        with st.spinner("Starting image generation..."):
            response = requests.post(
                urls["start_generate"],
                json={"prompt": prompt},
                timeout=20
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.task_id = data["task_id"]
                st.session_state.task_status = "processing"
                st.session_state.generation_started = time.time()
                st.session_state.prompt_used = prompt
                st.info(f"🚀 Image generation started! Task ID: {st.session_state.task_id}")
                st.rerun()
            else:
                st.error(f"Failed to start generation: {response.status_code}")
    except Exception as e:
        st.error(f"Error starting generation: {str(e)}")

# Function to check task status
def check_task_status():
    if st.session_state.task_id and st.session_state.task_status != "completed":
        urls = get_api_urls()
        try:
            status_response = requests.get(
                f"{urls['task_status']}/{st.session_state.task_id}",
                timeout=10
            )
            if status_response.status_code == 200:
                status_data = status_response.json()
                server_status = status_data["status"]
                if server_status == "completed" and st.session_state.task_status != "completed":
                    st.session_state.task_status = "completed"
                    st.rerun()  # Trigger rerun to fetch and display the image
                elif server_status == "failed":
                    st.session_state.task_status = "failed"
        except Exception as e:
            st.warning(f"Error checking status: {str(e)}")

# Polling and status display
if st.session_state.task_id:
    urls = get_api_urls()
    
    # Create placeholders
    status_placeholder = st.empty()
    progress_placeholder = st.empty()
    debug_log = st.empty()  # Debugging log placeholder
    
    # Check if triggered by JavaScript or manual button
    if st.session_state.check_trigger or st.button("Check Status Now"):
        st.session_state.last_status_check = time.time()
        check_task_status()
        debug_log.write(f"Status check triggered at {time.strftime('%H:%M:%S')} (Manual: {not st.session_state.check_trigger})")
        st.session_state.check_trigger = False  # Reset trigger
        st.rerun()
    
    # Display logic
    if st.session_state.task_status == "completed":
        status_placeholder.success("✅ Image generation completed!")
    elif st.session_state.task_status == "failed":
        error = "Unknown error"
        try:
            status_response = requests.get(f"{urls['task_status']}/{st.session_state.task_id}", timeout=10)
            if status_response.status_code == 200:
                error = status_response.json().get("error", "Unknown error")
        except:
            pass
        status_placeholder.error(f"❌ Generation failed: {error}")
    else:
        start_time = st.session_state.generation_started or time.time()
        elapsed = time.time() - start_time
        expected_duration = 7 * 60  # 7 minutes in seconds
        initial_progress = min(95, int((elapsed / expected_duration) * 100))
        initial_remaining = max(0, expected_duration - elapsed)
        initial_minutes = int(initial_remaining / 60)
        initial_seconds = int(initial_remaining % 60)
        
        status_placeholder.info("⏳ Generating image...")
        
        components.html(
            f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .progress-container {{
                        width: 100%;
                        background-color: #e0e0e0;
                        border-radius: 4px;
                        height: 20px;
                        margin-bottom: 10px;
                    }}
                    .progress-bar {{
                        width: {initial_progress}%;
                        height: 100%;
                        background-color: white;
                        border-radius: 4px;
                        transition: width 0.5s ease;
                        border: 1px solid #cccccc;
                    }}
                    .progress-text {{
                        color: #333333;
                        padding-left: 5px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                    .time-remaining {{
                        font-size: 16px;
                        font-weight: bold;
                        color: #0066cc;
                        margin-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="progress-container">
                    <div id="progress-bar" class="progress-bar">
                        <span id="progress-text" class="progress-text">{initial_progress}%</span>
                    </div>
                </div>
                <p class="time-remaining">
                    Estimated time remaining: <span id="minutes">{initial_minutes}</span> min <span id="seconds">{initial_seconds}</span> sec
                </p>
                <script>
                    var startTime = {int(start_time * 1000)};
                    var expectedDuration = {expected_duration * 1000};
                    function updateDisplay() {{
                        var now = new Date().getTime();
                        var elapsed = now - startTime;
                        var remaining = Math.max(0, expectedDuration - elapsed);
                        var minutes = Math.floor(remaining / 60000);
                        var seconds = Math.floor((remaining % 60000) / 1000);
                        document.getElementById("minutes").textContent = minutes;
                        document.getElementById("seconds").textContent = seconds.toString().padStart(2, "0");
                        var progressPct = Math.min(95, Math.floor((elapsed / expectedDuration) * 100));
                        document.getElementById("progress-bar").style.width = progressPct + "%";
                        document.getElementById("progress-text").textContent = progressPct + "%";
                        setTimeout(updateDisplay, 1000);
                    }}
                    updateDisplay();

                    // Periodic status check every 20 seconds
                    setInterval(function() {{
                        document.getElementById("checkButton").click();
                    }}, 20000);
                </script>
                <button id="checkButton" style="display:none;" onclick="window.parent.streamlit.setComponentValue(true)"></button>
            </body>
            </html>
            """,
            height=100,
        )
        st.info("You can safely leave this page and return later. The server will continue processing your image.")

# Display completed image
if st.session_state.task_id and st.session_state.task_status == "completed":
    urls = get_api_urls()
    try:
        if st.session_state.image_data is None:
            with st.spinner("Retrieving your generated image..."):
                image_response = requests.get(
                    f"{urls['get_image']}/{st.session_state.task_id}",
                    timeout=20
                )
                if image_response.status_code == 200:
                    response_data = image_response.json()
                    st.session_state.image_data = response_data["image"]
                    st.session_state.image_binary = base64.b64decode(st.session_state.image_data)
                    st.session_state.prompt_used = response_data["prompt"]
                else:
                    st.error(f"Failed to retrieve image: {image_response.status_code}")
        
        if st.session_state.image_binary:
            st.subheader("Generated Image:")
            image = Image.open(io.BytesIO(st.session_state.image_binary))
            st.image(
                image,
                caption=st.session_state.prompt_used,
                use_container_width=True
            )
            st.download_button(
                label="Download Image",
                data=st.session_state.image_binary,
                file_name="generated_pokemon.png",
                mime="image/png"
            )
    except Exception as e:
        st.error(f"Error retrieving image: {str(e)}")

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
    4. **Wait patiently** - generation takes 7-8 minutes on CPU
    5. You can leave this page and return later - your image will be waiting!
    6. Download your creation!
    
    ### Important Notes
    - **Please be patient**: Image generation takes 7-8 minutes
    - Your generation will continue even if you close this tab
    - The backend server may be offline to save costs - you'll need to start it
    - For better performance, consider using a GPU-enabled VM
    """)

# Footer
st.markdown("""
<div class="footer">
    <p>Made with ❤️ using Stable Diffusion + LoRA</p>
</div>
""", unsafe_allow_html=True)