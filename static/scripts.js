const videoFeed = document.getElementById('videoFeed');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const feedbackDiv = document.getElementById('feedback');
const postureBubble = document.getElementById('posture-bubble');
const frontalButton = document.getElementById('frontalButton');
const sideButton = document.getElementById('sideButton');
const aiButton = document.getElementById('aiButton');

let analysisActive = false;
let feedbackInterval;

const updateFeedback = async () => {
    try {
        const response = await fetch(`/feedback?t=${Date.now()}`, { cache: 'no-store' });
        if (!response.ok) throw new Error('Server not responding');
        const data = await response.json();

        if (feedbackDiv) feedbackDiv.textContent = data.message;
        if (data.mode === 'frontal') {
            frontalButton.classList.add('active');
            sideButton.classList.remove('active');
        } else if (data.mode === 'side') {
            sideButton.classList.add('active');
            frontalButton.classList.remove('active');
        }

        if (postureBubble) {
            const aiMsg = data.ai_message || '';
            postureBubble.textContent = aiMsg;
            postureBubble.style.display = aiMsg ? '' : 'none';
        }

        if (analysisActive && data.active === false) {
            analysisActive = false;
            startButton.disabled = false;
            stopButton.disabled = true;
            frontalButton.disabled = false;
            sideButton.disabled = false;

            clearInterval(feedbackInterval);
        }
    } catch (e) {
        if (feedbackDiv) feedbackDiv.textContent = '❌ Server connection error.';
        console.error("Feedback fetch error:", e);
        if (feedbackInterval) clearInterval(feedbackInterval);
    }
};

const setMode = async (mode) => {
    if (analysisActive) return;

    try {
        await fetch(`/control/set_view/${mode}`, { method: 'POST' });
        await updateFeedback();
    } catch (e) {
        console.error("Set mode error:", e);
        feedbackDiv.textContent = '❌ Could not set mode.';
    }
};

frontalButton.onclick = () => setMode('frontal');
sideButton.onclick = () => setMode('side');

if (aiButton) {
    aiButton.onclick = async () => {
        try {
            aiButton.disabled = true;
            aiButton.textContent = 'Fetching AI...';

            const response = await fetch(`/feedback?t=${Date.now()}`, { cache: 'no-store' });
            if (!response.ok) throw new Error('Server not responding');
            const data = await response.json();

            const aiMsg = data.ai_message || '';
            if (postureBubble) {
                postureBubble.textContent = aiMsg;
                postureBubble.style.display = aiMsg ? '' : 'none';
            }
            feedbackDiv.textContent = aiMsg ? 'AI feedback shown.' : 'No AI feedback available yet.';
        } catch (e) {
            console.error('AI fetch error:', e);
            if (feedbackDiv) feedbackDiv.textContent = '❌ Could not fetch AI feedback.';
        } finally {
            aiButton.disabled = false;
            aiButton.textContent = 'Show AI Feedback';
        }
    };
}

startButton.onclick = async () => {
    if (analysisActive) return;
    analysisActive = true;

    startButton.disabled = true;
    stopButton.disabled = false;
    frontalButton.disabled = true;
    sideButton.disabled = true;

    try {
        await fetch('/control/start', { method: 'POST' });
        videoFeed.src = `/video_feed?t=${new Date().getTime()}`;
        if (feedbackInterval) clearInterval(feedbackInterval);
        feedbackInterval = setInterval(updateFeedback, 500);
        if (feedbackDiv) feedbackDiv.textContent = 'Analysis starting...';

    } catch (e) {
        if (feedbackDiv) feedbackDiv.textContent = '❌ Failed to start analysis. Check server.';
        analysisActive = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        frontalButton.disabled = false;
        sideButton.disabled = false;
    }
};

stopButton.onclick = async () => {
    if (!analysisActive) return;
    analysisActive = false;

    startButton.disabled = false;
    stopButton.disabled = true;
    frontalButton.disabled = false;
    sideButton.disabled = false;

    clearInterval(feedbackInterval);

    await fetch('/control/stop', { method: 'POST' });

    videoFeed.src = '';

    await updateFeedback();
};

document.addEventListener('DOMContentLoaded', updateFeedback);