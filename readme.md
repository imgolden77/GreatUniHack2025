# Defend Your Posture Collision

## Problem definition/user need
As people age, physical activity significantly decreases, accelerating muscle loss and often leading to bodily imbalances. Among these, the first and most crucial function to be impacted is walking. An unbalanced walking posture can lead to the weakening of muscles on one side, resulting in joint inflammation and further reducing overall activity.

The question is: What if seniors could practice correct walking form for just 5 to 10 minutes a day in the comfort of their homes?

While many AI-powered training apps exist for younger people, there is a lack of accessible, personalized solutions for seniors.

## Solution concept description
The Defend Your Posture Collision (DPC) AI Agent is designed as a personalized, in-home gait training coach for seniors who may have difficulty leaving home or affording expensive personal training.

### Core Technology & Analysis:
1. Pose Detection: Uses OpenCV and MediaPipe to capture and track key joints like the shoulders, neck, and pelvis in real-time.

2. Imbalance Measurement: The system continuously measures left-right asymmetry based on the captured joint coordinates.

3. AI Coaching Trigger: If the measured data shows a state of imbalance (asymmetry) for more than 33% of the monitored time, a prompt containing the specific imbalance data is sent to OpenAI's GPT model.

4. Personalized Feedback: GPT acts as the "Posture Coach," generating personalized, natural language advice on what specific exercises to perform, which muscle groups to strengthen, and simple posture adjustments tailored to the detected imbalance.

## User journey or scenario
### A 30-Second Gait Correction Session
1. Launch & Calibration: The senior user opens the application (e.g., on a laptop or tablet). The AI prompts them to stand in front of the camera for initial calibration.

2. Guided Practice: The user is instructed to walk in place (or take short steps) for 30 seconds (10 seconds for a demo) while the AI tracks their posture.

3. Real-Time Feedback: During the session, the user sees visual cues (e.g., a green light for balanced walking, a red light for imbalance) overlaid on their video feed.

4. AI Intervention: If the imbalance threshold (33%) is exceeded, the session ends, and the AI Coach (GPT) is triggered.

5. Personalized Advice: A message appears on the screen (or is read out loud) from the GPT agent.

6. Next Steps: The user can save the advice or immediately attempt a new, corrected session.

## Future Enhencement
1. Gamification: Add a simple scoring system or "Postural Streak" counter to encourage daily engagement.

2. Accessibility: Integrate Text-to-Speech (TTS) functionality for verbal coaching, making the agent fully accessible to users who may struggle to read the screen.

3. Progression Tracking: Store the daily imbalance scores in a simple database (e.g., Snowflake, if scaling up) to visualize the user's postural improvement over time.

## Features
- Real-time webcam video feed served by FastAPI
- Two analysis modes: `frontal` and `side`
- 10-second batch collection then automated analysis
- Asynchronous AI coaching feedback generation (OpenAI)
- Frontend polling + manual "Show AI Feedback" button
- Simple UI controls: Start, Stop, Mode selector, AI feedback bubble

## Requirements
- macOS (development tested)
- Python 3.9+
- See `requirements.txt` for exact packages (FastAPI, uvicorn, mediapipe, opencv-python, openai, etc.)

## Quick setup
1. Create and activate a virtual environment:
   - python3 -m venv venv
   - source venv/bin/activate
2. Install dependencies:
   - pip install -r requirements.txt
3. Set environment variables (if using OpenAI):
   - export OPENAI_API_KEY="sk-..."

## Run (development)
Start the FastAPI app:
- uvicorn main_ai:app --reload --host 0.0.0.0 --port 8000

Open browser:
- http://localhost:8000/

## Usage (UI)
- Start: begin webcam stream and posture analysis
- Stop: stop analysis and stream
- Mode (frontal/side): choose analysis view (disabled while analyzing)
- Show AI Feedback: manually fetch AI-generated feedback and display it in the posture bubble

## Notes & Troubleshooting
- If AI feedback appears only after page refresh: ensure frontend keeps polling /feedback after analysis end, and backend sets ai_message when ready. Use the AI button to force retrieval.
- If the camera doesn't open: check system permissions and that OpenCV can access the device (logs/console).
- If styles appear overridden (e.g., aiButton background), inspect with browser dev tools and ensure `static/index.css` is loaded last or use specific selectors.

## Project layout
- main_ai.py — FastAPI app and analysis logic
- templates/ — HTML templates including index_ai.html
- static/ — JS, CSS, client assets
- src/ — detectors, ai_coach, utilities
- requirements.txt — Python dependencies

## License
Add a license file or header as needed.